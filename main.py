from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class Item(BaseModel):
    name: str
    price: float
    is_offer: bool = None


class Items(BaseModel):
    name: str
    description: str | None = None
    price: float
    tax: float | None = None


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/hello/{name}")
async def say_hello(name: str):
    data = Item(name=name, price=100, is_offer=True)
    return {"message": f"Hello {data.name} your total is {data.price} "}


@app.post("/items/")
async def create_item(item: Items):
    response = item | {"id": 1}
    return response

@app.get("/home/{item_id}")
def read_item(item_id: int):
    return f"Welcome to the home page {item_id}"