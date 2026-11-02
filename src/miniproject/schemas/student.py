from pydantic import BaseModel, Field
from typing import Optional
from datetime import date


class Student(BaseModel):
    """Student schema"""
    id: Optional[int] = Field(None, description="Student id")
    name: str = Field(..., description="Student name")
    phone: str = Field(..., description="Student phone")
    library_id: int = Field(..., description="Library id to which the student belongs")
    Owner_id: Optional[int] = Field(None, description="Owner id (extracted automatically from auth token)")
    email: Optional[str] = Field(None, description="Student email")
    address: Optional[str] = Field(None, description="Student address")
    status: Optional[str] = "active"
    alumini: Optional[bool] = Field(False, description="Whether the student is an alumnus")
    payment_start_month: Optional[date] = None
    last_payment_date: Optional[date] = None
    
