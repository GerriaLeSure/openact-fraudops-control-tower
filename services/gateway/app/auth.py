from datetime import datetime, timedelta, timezone
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import jwt
from pydantic import BaseModel
from .config import settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
ALGO = "HS256"

class TokenData(BaseModel):
    sub: str
    role: str

def create_token(sub: str, role: str = "analyst") -> str:
    exp = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRE_MIN)
    return jwt.encode({"sub": sub, "role": role, "exp": exp}, settings.JWT_SECRET, algorithm=ALGO)

def require_role(roles: list[str]):
    async def dep(token: str = Depends(oauth2_scheme)) -> TokenData:
        try:
            data = jwt.decode(token, settings.JWT_SECRET, algorithms=[ALGO])
            td = TokenData(sub=data["sub"], role=data["role"])
            if td.role not in roles:
                raise HTTPException(403, "insufficient_role")
            return td
        except Exception:
            raise HTTPException(401, "invalid_token")
    return dep
