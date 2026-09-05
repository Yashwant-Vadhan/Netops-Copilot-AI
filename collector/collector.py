#!/usr/bin/env python3
"""
Real Telemetry Collector Module (TV-001)
========================================
Collects real network interface telemetry (throughput, bytes sent/recv) via psutil
and measures round-trip latency / packet loss to a target host via ping3 (with system
subprocess ping fallback). Posts validated telemetry records to the FastAPI backend.

Environment Variables:
- TARGET_HOST: Host to ping (default: 8.8.8.8)
- POLL_INTERVAL_SECONDS: Time between collection cycles (default: 5)
- BACKEND_URL: Backend base URL (default: http://localhost:8000)
- COLLECTOR_SECRET: Shared secret matching backend header (default: dev-collector-secret)
- INTERFACE_NAME: Specific network interface name (empty for auto-detect)
- SOURCE_ID: Unique identifier for this collector instance (default: hostname)
"""

import os
import sys
import time
import socket
import logging
import argparse
import platform
import subprocess
from datetime import datetime, timezone
from typing import Optional, Tuple, Dict, Any

import psutil
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('TelemetryCollector')

TARGET_HOST = os.getenv('TARGET_HOST', '8.8.8.8')
POLL_INTERVAL_SECONDS = float(os.getenv('POLL_INTERVAL_SECONDS', '5.0'))
BACKEND_URL = os.getenv('BACKEND_URL', 'http://localhost:8000').rstrip('/')
COLLECTOR_SECRET = os.getenv('COLLECTOR_SECRET', 'netops-collector-secret-key-2026')
INTERFACE_NAME = os.getenv('INTERFACE_NAME', '')
SOURCE_ID = os.getenv('SOURCE_ID', socket.gethostname())


def autodetect_interface() -> str:
    """
    Detects the primary active network interface by checking active stats and IP bindings.
    """
    stats = psutil.net_if_stats()
    addrs = psutil.net_if_addrs()

    io_counters = psutil.net_io_counters(pernic=True)
    best_nic = None
    max_bytes = -1

    for nic, nic_stats in stats.items():
        if nic_stats.isup and nic in addrs:
            has_ipv4 = any(addr.family == socket.AF_INET and not addr.address.startswith('127.') for addr in addrs[nic])
            if has_ipv4:
                io = io_counters.get(nic)
                total_bytes = (io.bytes_sent + io.bytes_recv) if io else 0
                if total_bytes > max_bytes:
                    max_bytes = total_bytes
                    best_nic = nic

    if best_nic:
        return best_nic

    if io_counters:
        return list(io_counters.keys())[0]

    return 'eth0'


def ping_probe(target_host: str, count: int = 3, timeout: float = 2.0) -> Tuple[Optional[float], float, bool]:
    """
    Pings target_host to measure average latency_ms and packet_loss_pct.
    Uses ping3 if available and functional; falls back to system subprocess ping.
    Returns: (latency_ms, packet_loss_pct, probe_failed)
    """
    latencies = []
    failed_pings = 0

    try:
        import ping3
        for _ in range(count):
            try:
                delay = ping3.ping(target_host, timeout=timeout, unit='ms')
                if delay is not None and delay is not False:
                    latencies.append(float(delay))
                else:
                    failed_pings += 1
            except Exception:
                failed_pings += 1
            time.sleep(0.05)
    except Exception as e:
        logger.debug(f'ping3 not usable ({e}), falling back to system ping')
        latencies = []
        failed_pings = 0

    if not latencies and failed_pings == count:
        is_win = platform.system().lower() == 'windows'
        ping_cmd = ['ping', '-n', str(count), '-w', str(int(timeout * 1000)), target_host] if is_win else ['ping', '-c', str(count), '-W', str(int(timeout)), target_host]
        try:
            res = subprocess.run(ping_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=count * timeout + 2)
            output = res.stdout
            
            if is_win:
                for line in output.splitlines():
                    line_lower = line.lower()
                    if 'time=' in line_lower or 'time<' in line_lower:
                        parts = line_lower.split('time')
                        if len(parts) > 1:
                            val_part = parts[1].split()[0].lstrip('=<').rstrip('ms')
                            try:
                                latencies.append(float(val_part))
                            except ValueError:
                                pass
                if '100% loss' in output or not latencies:
                    failed_pings = count - len(latencies)
            else:
                for line in output.splitlines():
                    if 'time=' in line:
                        part = line.split('time=')[1].split()[0]
                        try:
                            latencies.append(float(part))
                        except ValueError:
                            pass
                failed_pings = count - len(latencies)
        except Exception as proc_err:
            logger.warning(f'Subprocess ping error: {proc_err}')
            failed_pings = count

    if not latencies:
        return None, 100.0, True

    avg_latency = sum(latencies) / len(latencies)
    packet_loss = (failed_pings / count) * 100.0
    return round(avg_latency, 2), round(packet_loss, 2), False


class Collector:
    def __init__(self, interface: Optional[str] = None, target_host: str = TARGET_HOST, source_id: str = SOURCE_ID, backend_url: str = BACKEND_URL, collector_secret: str = COLLECTOR_SECRET):
        self.interface = interface or autodetect_interface()
        self.target_host = target_host
        self.source_id = source_id
        self.backend_url = backend_url
        self.collector_secret = collector_secret
        self.last_sample_time = None
        self.last_bytes_sent = 0
        self.last_bytes_recv = 0
        self._init_counters()

    def _init_counters(self):
        """Take initial counter snapshot for delta calculation."""
        try:
            counters = psutil.net_io_counters(pernic=True)
            if self.interface not in counters:
                self.interface = autodetect_interface()
                counters = psutil.net_io_counters(pernic=True)

            nic_io = counters.get(self.interface)
            if nic_io:
                self.last_bytes_sent = nic_io.bytes_sent
                self.last_bytes_recv = nic_io.bytes_recv
                self.last_sample_time = time.time()
        except Exception as e:
            logger.error(f'Error initializing network counters: {e}')

    def collect_metrics(self) -> Dict[str, Any]:
        """Reads network metrics, computes throughput delta, and performs ping probe."""
        now = time.time()
        counters = psutil.net_io_counters(pernic=True)

        if self.interface not in counters:
            logger.warning(f'Interface {self.interface} not found, redetecting...')
            self.interface = autodetect_interface()
            counters = psutil.net_io_counters(pernic=True)

        nic_io = counters.get(self.interface)
        bytes_sent = nic_io.bytes_sent if nic_io else 0
        bytes_recv = nic_io.bytes_recv if nic_io else 0

        throughput_mbps = 0.0
        if self.last_sample_time and now > self.last_sample_time:
            elapsed = now - self.last_sample_time
            delta_bytes = (bytes_sent - self.last_bytes_sent) + (bytes_recv - self.last_bytes_recv)
            if delta_bytes >= 0 and elapsed > 0:
                throughput_mbps = round((delta_bytes * 8.0) / (elapsed * 1_000_000.0), 3)

        self.last_bytes_sent = bytes_sent
        self.last_bytes_recv = bytes_recv
        self.last_sample_time = now

        latency_ms, packet_loss_pct, probe_failed = ping_probe(self.target_host)

        payload = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'source_id': self.source_id,
            'interface': self.interface,
            'latency_ms': latency_ms,
            'packet_loss_pct': packet_loss_pct,
            'throughput_mbps': throughput_mbps,
            'bytes_sent': bytes_sent,
            'bytes_recv': bytes_recv,
            'probe_failed': probe_failed
        }
        return payload

    def send_telemetry(self, payload: Dict[str, Any]) -> bool:
        """POSTs telemetry payload to the backend ingest endpoint."""
        endpoint = f'{self.backend_url}/api/telemetry/ingest'
        headers = {
            'Content-Type': 'application/json',
            'X-Collector-Secret': self.collector_secret
        }
        try:
            resp = requests.post(endpoint, json=payload, headers=headers, timeout=5)
            if resp.status_code == 201:
                logger.info(f"Telemetry pushed [{self.interface}] -> Latency: {payload['latency_ms']}ms | Loss: {payload['packet_loss_pct']}% | Throughput: {payload['throughput_mbps']}Mbps")
                return True
            else:
                logger.warning(f'Backend rejected telemetry (HTTP {resp.status_code}): {resp.text}')
                return False
        except requests.exceptions.RequestException as req_err:
            logger.error(f'Failed to reach backend at {endpoint}: {req_err}')
            return False

    def run_cycle(self) -> Dict[str, Any]:
        """Runs a single collection cycle and sends telemetry."""
        payload = self.collect_metrics()
        self.send_telemetry(payload)
        return payload


def main():
    parser = argparse.ArgumentParser(description='NetOps Copilot AI - Real Telemetry Collector')
    parser.add_argument('--interface', type=str, default=INTERFACE_NAME, help='Interface name to monitor')
    parser.add_argument('--target-host', type=str, default=TARGET_HOST, help='Ping target host (default: 8.8.8.8)')
    parser.add_argument('--backend-url', type=str, default=BACKEND_URL, help='Backend URL (default: http://localhost:8000)')
    parser.add_argument('--secret', type=str, default=COLLECTOR_SECRET, help='Collector secret key')
    parser.add_argument('--source-id', type=str, default=SOURCE_ID, help='Source identifier')
    parser.add_argument('--interval', type=float, default=POLL_INTERVAL_SECONDS, help='Poll interval in seconds')
    parser.add_argument('--once', action='store_true', help='Run once and exit (for testing/CI)')
    args = parser.parse_args()

    collector = Collector(
        interface=args.interface if args.interface else None,
        target_host=args.target_host,
        source_id=args.source_id,
        backend_url=args.backend_url,
        collector_secret=args.secret
    )

    logger.info(f'Starting Telemetry Collector (Interface: {collector.interface}, Target: {collector.target_host}, Interval: {args.interval}s, Source: {collector.source_id})')

    if args.once:
        data = collector.run_cycle()
        logger.info(f'Single-shot collection completed: {data}')
        return

    while True:
        try:
            collector.run_cycle()
            time.sleep(args.interval)
        except KeyboardInterrupt:
            logger.info('Collector stopped by user.')
            break
        except Exception as e:
            logger.error(f'Unexpected error in collector cycle: {e}')
            time.sleep(2.0)


if __name__ == '__main__':
    main()