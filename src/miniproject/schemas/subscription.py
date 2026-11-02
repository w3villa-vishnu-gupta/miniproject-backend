from pydantic import BaseModel, Field
from typing import Optional


#this is subscription for library
class subscription(BaseModel):
    id: Optional[int] = Field(None, description="Subscription id")
    subscription_type: str = Field(..., description="Subscription type")
    owner_id: int = Field(..., description="Owner id")
    start_date: str = Field(..., description="Subscription start date")
    end_date: str = Field(..., description="Subscription end date")