from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from typing import Any, Dict, Optional

class APIException(HTTPException):
    def __init__(self, status_code: int, code: str, message: str, headers: Optional[Dict[str, str]] = None):
        super().__init__(status_code=status_code, detail=message, headers=headers)
        self.code = code
        self.message = message

def success_response(data: Any, status_code: int = 200) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "data": data,
            "error": None
        }
    )

def error_response(code: str, message: str, status_code: int = 400) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "data": None,
            "error": {
                "code": code,
                "message": message
            }
        }
    )

async def api_exception_handler(request: Request, exc: APIException) -> JSONResponse:
    return error_response(code=exc.code, message=exc.message, status_code=exc.status_code)

async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    code_map = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        422: "VALIDATION_ERROR",
        500: "INTERNAL_SERVER_ERROR"
    }
    code = code_map.get(exc.status_code, "ERROR")
    message = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
    return error_response(code=code, message=message, status_code=exc.status_code)

async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    errors = exc.errors()
    msg = errors[0].get("msg", "Validation error") if errors else "Validation error"
    return error_response(code="VALIDATION_ERROR", message=f"Payload validation failed: {msg}", status_code=422)

async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return error_response(code="INTERNAL_SERVER_ERROR", message=f"An unexpected error occurred: {str(exc)}", status_code=500)
