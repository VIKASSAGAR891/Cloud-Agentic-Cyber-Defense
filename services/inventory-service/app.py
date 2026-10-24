from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Inventory Service")


class InventoryItem(BaseModel):
    product_name: str
    quantity: int
    price: float


inventory = {
    "laptop": {
        "product_name": "Laptop",
        "quantity": 25,
        "price": 75000.0
    },
    "phone": {
        "product_name": "Smartphone",
        "quantity": 50,
        "price": 30000.0
    },
    "keyboard": {
        "product_name": "Keyboard",
        "quantity": 100,
        "price": 1500.0
    }
}


@app.get("/")
def health_check():
    return {
        "service": "inventory-service",
        "status": "running"
    }


@app.get("/inventory")
def get_inventory():
    return {
        "items": inventory
    }


@app.get("/inventory/{product_id}")
def get_product(product_id: str):

    if product_id not in inventory:
        return {
            "error": "Product not found"
        }

    return inventory[product_id]


@app.post("/inventory")
def add_product(item: InventoryItem):

    product_id = item.product_name.lower().replace(" ", "-")

    inventory[product_id] = {
        "product_name": item.product_name,
        "quantity": item.quantity,
        "price": item.price
    }

    return {
        "product_id": product_id,
        "product": inventory[product_id],
        "status": "added"
    }