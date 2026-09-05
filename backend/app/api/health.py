from fastapi import APIRouter
from app.core.errors import success_response

router = APIRouter()

@router.get("/health")
def health_check():
    return {"status": "ok", "data": {"status": "ok"}, "error": None}
