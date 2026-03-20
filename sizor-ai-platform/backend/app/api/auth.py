from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jose import JWTError, jwt
from passlib.context import CryptContext
from ..database import get_db
from ..models import Clinician
from ..config import settings

router = APIRouter(prefix="/auth", tags=["auth"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def create_token(clinician_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    return jwt.encode(
        {"sub": clinician_id, "exp": expire},
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )


async def get_current_clinician(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
):
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        clinician_id = payload.get("sub")
        if not clinician_id:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    result = await db.execute(
        select(Clinician).where(Clinician.clinician_id == clinician_id)
    )
    clinician = result.scalar_one_or_none()
    if not clinician:
        raise HTTPException(status_code=401, detail="Clinician not found")
    return clinician


@router.post("/login")
async def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Clinician).where(Clinician.email == form.username)
    )
    clinician = result.scalar_one_or_none()
    if not clinician or not pwd_context.verify(form.password, clinician.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    clinician.last_login = datetime.now(timezone.utc)
    await db.commit()
    return {
        "access_token": create_token(str(clinician.clinician_id)),
        "token_type": "bearer",
    }


@router.get("/me")
async def me(clinician=Depends(get_current_clinician)):
    return {
        "clinician_id": str(clinician.clinician_id),
        "full_name": clinician.full_name,
        "role": clinician.role,
        "email": clinician.email,
        "ward_id": str(clinician.ward_id) if clinician.ward_id else None,
        "hospital_id": str(clinician.hospital_id),
    }
