from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class Book(BaseModel):
    """Book schema"""
    id: Optional[int] = Field(None, description="Book id")
    library_id: int = Field(..., description="Library id to which the book belongs")
    owner_id: Optional[int] = Field(None, description="Owner id")
    title: str = Field(..., description="Book title")
    author: str = Field(..., description="Book author")
    category: str = Field(..., description="Book category/genre")
    copies: int = Field(1, description="Number of copies", ge=1)
    issued_copies: int = Field(0, description="Number of copies currently issued", ge=0)
    status: Optional[str] = Field("Available", description="Availability status (e.g. Available, Issued, Reserved)")
    description: Optional[str] = Field(None, description="Book description/synopsis")
    created_at: Optional[datetime] = None


class BookUpdate(BaseModel):
    """Book update schema"""
    title: Optional[str] = None
    author: Optional[str] = None
    category: Optional[str] = None
    copies: Optional[int] = Field(None, ge=1)
    issued_copies: Optional[int] = Field(None, ge=0)
    status: Optional[str] = None
    description: Optional[str] = None
