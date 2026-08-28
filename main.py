import fastapi_jsonrpc as jsonrpc
from fastapi import Body
from pydantic import BaseModel


# so the json rpc is built on top of the fast api
app = jsonrpc.API()
# so all the json rpc calls come to this end point
rpc = jsonrpc.Entrypoint("/rpc")


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


# JSON-RPC method
@rpc.method()
def add_items(
    a: int = Body(...),
    b: int = Body(...),
) -> int:
    return a + b


# JSON-RPC method
@rpc.method()
def subtract_items(
    a: int = Body(...),
    b: int = Body(...),
) -> int:
    return a - b

# Connect the /rpc entrypoint to the application
app.bind_entrypoint(rpc)