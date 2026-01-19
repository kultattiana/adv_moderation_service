from fastapi import APIRouter

router = APIRouter(tags=["Health"])

@router.get("/")
async def root():
    return {'message': 'Hello World'}