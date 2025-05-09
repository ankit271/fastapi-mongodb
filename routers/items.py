from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def get_items() -> list:
    return [{"username": "Alice"}, {"username": "Bob"}]