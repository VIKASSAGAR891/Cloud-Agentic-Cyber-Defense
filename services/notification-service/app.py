from fastapi import FastAPI
from pydantic import BaseModel
from datetime import datetime

app = FastAPI(title="Notification Service")


class NotificationRequest(BaseModel):
    user_id: str
    message: str
    notification_type: str = "general"


@app.get("/")
def health_check():
    return {
        "service": "notification-service",
        "status": "running"
    }


@app.post("/notify")
def send_notification(notification: NotificationRequest):
    return {
        "notification_id": "NOTIF-" + datetime.now().strftime("%Y%m%d%H%M%S"),
        "user_id": notification.user_id,
        "message": notification.message,
        "notification_type": notification.notification_type,
        "status": "sent"
    }