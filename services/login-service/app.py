from fastapi import FastAPI

app = FastAPI(title="Login Service")


@app.get("/")
def home():
    return {
        "service": "login-service",
        "status": "running"
    }


@app.get("/login")
def login(username: str = "testuser"):
    return {
        "username": username,
        "message": "Login successful"
    }