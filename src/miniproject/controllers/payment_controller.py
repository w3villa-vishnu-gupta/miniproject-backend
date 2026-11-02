import hmac
import os
from decimal import Decimal
from urllib.parse import quote

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text

from miniproject.auth.auth import get_current_owner
from miniproject.connections.db import engine
from miniproject.schemas.order import OrderCreateRequest

router = APIRouter(tags=["payments"])

plans = {
    1: {
        "name": "Silver",
        "price": 499,
        "duration_days": 30,
    },
    2: {
        "name": "Gold",
        "price": 999,
        "duration_days": 30,
    },
    3: {
        "name": "Platinum",
        "price": 1499,
        "duration_days": 30,
    },
}


class VerifyPaymentRequest(BaseModel):
    razorpay_order_id: str = Field(..., min_length=1)
    razorpay_payment_id: str = Field(..., min_length=1)
    razorpay_signature: str = Field(..., min_length=1)
    user_id: int = Field(..., gt=0)


@router.post("/payment/createorder")
def create_razorpay_order(order_request: OrderCreateRequest):
    plan = plans.get(order_request.plan_id)
    if plan is None:
        raise HTTPException(status_code=400, detail="Invalid plan_id")

    if (
        order_request.plan_name != plan["name"]
        or order_request.amount_inr != Decimal(str(plan["price"]))
    ):
        raise HTTPException(
            status_code=400,
            detail="The submitted plan name or price does not match the selected plan",
        )

    key_id = os.getenv("RAZORPAY_KEY_ID") or os.getenv("key_id")
    key_secret = os.getenv("RAZORPAY_KEY_SECRET") or os.getenv("key_secret")
    if not key_id or not key_secret:
        raise HTTPException(
            status_code=503,
            detail="Razorpay is not configured on the server",
        )

    amount_paise = plan["price"] * 100
    with engine.begin() as connection:
        # Serialize order creation for this user and plan to prevent duplicate pending orders.
        connection.execute(
            text("SELECT pg_advisory_xact_lock(:user_id, :plan_id)"),
            {"user_id": order_request.user_id, "plan_id": order_request.plan_id},
        )

        user_exists = connection.execute(
            text("SELECT 1 FROM users WHERE id = :user_id UNION SELECT 1 FROM owners WHERE id = :user_id"),
            {"user_id": order_request.user_id},
        ).first()
        if user_exists is None:
            raise HTTPException(status_code=404, detail="User not found")

        check_if_any_order_is_already_done = connection.execute(
            text("""
                SELECT *
                FROM orders
                WHERE user_id = :user_id
                  AND status = 'paid'
            """),
            {"user_id": order_request.user_id},
        ).first()

        if check_if_any_order_is_already_done is not None:
            raise HTTPException(status_code=403, detail="You have already subscribed to a plan")

        existing_order = connection.execute(
            text("""
                SELECT id, razorpay_order_id, amount_paise, currency, plan_name, status
                FROM orders
                WHERE user_id = :user_id
                  AND plan_id = :plan_id
                  AND status = 'created'
                ORDER BY created_at DESC, id DESC
                LIMIT 1
            """),
            {"user_id": order_request.user_id, "plan_id": order_request.plan_id},
        ).mappings().first()

        if existing_order is not None:
            return {
                "id": existing_order["id"],
                "order_id": existing_order["razorpay_order_id"],
                "amount": existing_order["amount_paise"],
                "currency": existing_order["currency"],
                "plan_name": existing_order["plan_name"],
                "status": existing_order["status"],
                "reused": True,
            }

        try:
            response = httpx.post(
                "https://api.razorpay.com/v1/orders",
                auth=(key_id, key_secret),
                json={"amount": amount_paise, "currency": "INR"},
                timeout=15.0,
            )
            response.raise_for_status()
            razorpay_order = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise HTTPException(
                status_code=502,
                detail="Could not create an order with Razorpay",
            ) from exc

        razorpay_order_id = (
            razorpay_order.get("id") if isinstance(razorpay_order, dict) else None
        )
        if not razorpay_order_id:
            raise HTTPException(
                status_code=502,
                detail="Razorpay returned an invalid order response",
            )

        new_order_id = connection.execute(
            text("""
                INSERT INTO orders (
                    user_id, plan_id, plan_name, amount_paise, currency,
                    razorpay_order_id, status
                )
                VALUES (
                    :user_id, :plan_id, :plan_name, :amount_paise, 'INR',
                    :razorpay_order_id, 'created'
                )
                RETURNING id
            """),
            {
                "user_id": order_request.user_id,
                "plan_id": order_request.plan_id,
                "plan_name": plan["name"],
                "amount_paise": amount_paise,
                "razorpay_order_id": razorpay_order_id,
            },
        ).scalar_one()

    return {
        "id": new_order_id,
        "order_id": razorpay_order_id,
        "amount": amount_paise,
        "currency": "INR",
        "plan_name": plan["name"],
        "status": "created",
        "reused": False,
    }


@router.post("/payment/verify-payment")
def verify_payment(data: VerifyPaymentRequest):
    key_id = os.getenv("RAZORPAY_KEY_ID")
    key_secret = os.getenv("RAZORPAY_KEY_SECRET")
    print("called")
    if not key_id or not key_secret:
        raise HTTPException(
            status_code=503,
            detail="Razorpay is not configured",
        )

    signature_payload = f"{data.razorpay_order_id}|{data.razorpay_payment_id}"
    expected_signature = hmac.new(
        key_secret.encode("utf-8"),
        signature_payload.encode("utf-8"),
        digestmod="sha256",
    ).hexdigest()
    if not hmac.compare_digest(expected_signature, data.razorpay_signature):
        raise HTTPException(
            status_code=400,
            detail="Invalid payment signature",
        )

    try:
        response = httpx.get(
            "https://api.razorpay.com/v1/payments/"
            f"{quote(data.razorpay_payment_id, safe='')}",
            auth=(key_id, key_secret),
            timeout=15.0,
        )
        response.raise_for_status()
        payment = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(
            status_code=502,
            detail="Could not verify payment with Razorpay",
        ) from exc

    if not isinstance(payment, dict):
        raise HTTPException(
            status_code=502,
            detail="Razorpay returned an invalid payment response",
        )

    if payment.get("order_id") != data.razorpay_order_id:
        raise HTTPException(
            status_code=400,
            detail="Payment does not belong to this order",
        )

    if payment.get("status") != "captured":
        raise HTTPException(
            status_code=409,
            detail="Payment is not captured yet",
        )

    if payment.get("currency") != "INR":
        raise HTTPException(
            status_code=400,
            detail="Invalid payment currency",
        )

    with engine.begin() as connection:
        order = connection.execute(
            text("""
                SELECT
                    id,
                    status,
                    user_id,
                    plan_id,
                    amount_paise,
                    razorpay_order_id
                FROM orders
                WHERE razorpay_order_id = :order_id
                  AND user_id = :user_id
                FOR UPDATE
            """),
            {
                "order_id": data.razorpay_order_id,
                "user_id": data.user_id,
            },
        ).mappings().first()

        if order is None:
            raise HTTPException(
                status_code=404,
                detail="Order not found",
            )

        if payment.get("amount") != order["amount_paise"]:
            raise HTTPException(
                status_code=400,
                detail="Payment amount does not match order",
            )

        if order["status"] == "paid":
            return {
                "message": "Payment already verified",
                "order_id": data.razorpay_order_id,
                "status": "paid",
            }

        if order["status"] != "created":
            raise HTTPException(
                status_code=409,
                detail=f"Order status is {order['status']}",
            )

        plan = plans.get(order["plan_id"])
        if plan is None:
            raise HTTPException(
                status_code=404,
                detail="Plan not found",
            )

        connection.execute(
            text("""
                UPDATE orders
                SET status = 'paid',
                    razorpay_payment_id = :payment_id
                WHERE id = :order_id
            """),
            {
                "payment_id": data.razorpay_payment_id,
                "order_id": order["id"],
            },
        )

        connection.execute(
            text("""
                INSERT INTO subscriptions (
                    subscription_type,
                    owner_id,
                    start_date,
                    end_date
                )
                VALUES (
                    :subscription_type,
                    :owner_id,
                    CURRENT_DATE,
                    CURRENT_DATE + :duration_days
                )
            """),
            {
                "subscription_type": plan["name"],
                "owner_id": order["user_id"],
                "duration_days": plan["duration_days"],
            },
        )

    return {
        "message": "Payment verified and subscription created",
        "order_id": data.razorpay_order_id,
        "status": "paid",
        "subscription_type": plan["name"],
    }


@router.get("/subscription")
@router.get("/getsubscription")
def get_current_subscription(
    owner_id: int | None = None,
    current_owner: dict = Depends(get_current_owner),
):
    oid = current_owner["owner_id"] if current_owner else owner_id

    with engine.connect() as connection:
        sub = connection.execute(
            text("""
                SELECT id, subscription_type, owner_id, start_date, end_date
                FROM subscriptions
                WHERE owner_id = :owner_id AND end_date >= CURRENT_DATE
                ORDER BY id DESC
                LIMIT 1
            """),
            {"owner_id": oid},
        ).mappings().first()

        if not sub:
            plan_name = "free"
            subscription = None
        else:
            plan_name = sub["subscription_type"].lower()
            subscription = dict(sub)

    with engine.connect() as connection:
        feature = connection.execute(
            text("""
                SELECT feature_name, is_enabled
                FROM plan_features
                WHERE plan_name = :plan_name
            """),
            {"plan_name": plan_name},
        ).mappings().all()

        print(feature)

        if not sub:
            return {
                "subscription": None,
                "subscription_type": "Free",
                "active": False,
                "feature": {f["feature_name"]: f["is_enabled"] for f in feature},
            }

        return {
            "subscription": dict(sub),
            "subscription_type": sub["subscription_type"],
            "active": True,
            "start_date": str(sub["start_date"]),
            "end_date": str(sub["end_date"]),
            "feature": {f["feature_name"]: f["is_enabled"] for f in feature},
        }
