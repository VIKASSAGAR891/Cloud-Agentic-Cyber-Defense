from fastapi import FastAPI
from pydantic import BaseModel
import uuid

app = FastAPI(title="Payment Service")


class PaymentRequest(BaseModel):
    username: str
    amount: float


payments = {}


@app.get("/")
def health_check():
    return {
        "service": "payment-service",
        "status": "running"
    }


@app.post("/pay")
def make_payment(payment: PaymentRequest):

    payment_id = str(uuid.uuid4())

    payment_record = {
        "payment_id": payment_id,
        "username": payment.username,
        "amount": payment.amount,
        "status": "successful"
    }

    payments[payment_id] = payment_record

    return payment_record


@app.get("/payments/{payment_id}")
def get_payment(payment_id: str):

    if payment_id not in payments:
        return {
            "error": "Payment not found"
        }

    return payments[payment_id]