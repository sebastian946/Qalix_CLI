from fastapi import APIRouter

router = APIRouter()


@router.post("/register_user", tags=["Users"])
async def register_user() -> dict:
    return {"message": "Not yet implemented"}
