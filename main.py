import fastapi_jsonrpc as jsonrpc
from fastapi import Body
from pydantic import BaseModel
from agent.simple import graph
from uuid import uuid4
from langgraph.types import Command


# so the json rpc is built on top of the fast api
app = jsonrpc.API()
# so all the json rpc calls come to this end point
rpc = jsonrpc.Entrypoint("/rpc")


class ProtocolRequest(BaseModel):
    protocol_id: str
    old_version: str
    new_version: str

class ReviewRequest(BaseModel):
    thread_id: str
    action: str
    comment: str | None = None

class Item(BaseModel):
    name: str
    price: float
    is_offer: bool = None


class Items(BaseModel):
    name: str
    description: str | None = None
    price: float
    tax: float | None = None

sample_items= Items(name="apple", description="red", price=100, tax=10)


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/hello/{name}")
async def say_hello(name: str):
    data = Item(name=name, price=100, is_offer=True)
    return {"message": f"Hello {data.name} your total is {data.price} "}


@app.post("/items/")
async def create_item(item: Items):
    response = item or sample_items
    return response

@app.get("/home/{item_id}")
def read_item(item_id: int):
    return f"Welcome to the home page {item_id}"




@app.post("/api/v1/protocol/compare")
def compare_protocol(request: ProtocolRequest):

    thread_id = str(uuid4())

    config = {
        "configurable": {
            "thread_id": thread_id
        }
    }

    response = graph.invoke(
        {
            "protocol_id": request.protocol_id,
            "old_version": request.old_version,
            "new_version": request.new_version
        },
        config=config
    )

    return {
        "thread_id": thread_id,
        "result": response
    }




@app.post("/api/v1/protocol/review")
def review_protocol(request: ReviewRequest):

    config = {
        "configurable": {
            "thread_id": request.thread_id
        }
    }

    response = graph.invoke(
        Command(
            resume={
                "action": request.action,
                "comment": request.comment
            }
        ),
        config=config
    )

    return response

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