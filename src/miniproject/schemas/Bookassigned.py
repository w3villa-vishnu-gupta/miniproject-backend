from pydantic import BaseModel
from typing import Optional

class Bookassigned(BaseModel):
    book_id: int
    student_id: int
    assigned_date: str
    return_date: str
    status: Optional[str] = "issued"