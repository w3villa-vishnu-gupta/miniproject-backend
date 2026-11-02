from datetime import datetime, timezone
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field


class OrderCreateRequest(BaseModel):
    user_id: int = Field(..., gt=0)
    plan_id: int = Field(..., gt=0)
    plan_name: str = Field(..., min_length=1)
    amount_inr: Decimal = Field(..., gt=0)


class Order(BaseModel):
    id: int | None = Field(None, description="Internal order ID")
    user_id: int = Field(..., description="ID of the user who created the order")
    plan_id: int = Field(..., description="Database ID of the selected plan")
    plan_name: str = Field(..., description="Plan name at the time of the order")
    amount_paise: int = Field(..., gt=0, description="Order amount in paise")
    currency: Literal["INR"] = Field("INR", description="Order currency")
    razorpay_order_id: str = Field(..., description="Order ID returned by Razorpay")
    status: Literal["created", "paid", "failed"] = Field(
        "created", description="Payment status"
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Time the order was created",
    )