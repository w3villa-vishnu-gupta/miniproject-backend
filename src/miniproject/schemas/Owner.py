from pydantic import BaseModel, Field
from typing import Optional

class Owner(BaseModel):
    id: Optional[int] = Field(None, description="The unique identifier of the owner")
    name: str = Field(..., description="The name of the owner")
    email: str = Field(..., description="The email of the owner")
    phone: str = Field(..., description="The phone number of the owner")
    password: str = Field(..., description="The password of the owner")
    
