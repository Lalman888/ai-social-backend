from pydantic import BaseModel
from typing import Optional

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    # Subject (usually user ID or email) stored within the JWT
    sub: Optional[str] = None
    # You can add other custom claims here if needed
    # e.g., roles: List[str] = []
