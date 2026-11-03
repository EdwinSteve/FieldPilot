"""The public passport of a lot: what the QR opens, no token (§4.14, D083)."""

from fastapi import APIRouter

from app.api.deps import ContainerDep
from app.api.schemas import PassportOut

router = APIRouter(tags=["trace"])


@router.get("/trace/{code}")
def passport(code: str, container: ContainerDep) -> PassportOut:
    return PassportOut.of(container.passports.public(code))
