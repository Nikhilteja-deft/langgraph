from langgraph.graph import StateGraph, START, END
from pydantic import BaseModel


class ProtocolState(BaseModel):
    protocol_id: str
    old_version: str
    new_version: str


def compare_protocols(state: ProtocolState):
    print(state.protocol_id)

    return {
        "old_version": state.old_version,
        "new_version": state.new_version,
    }


graph = StateGraph(ProtocolState)

graph.add_node(compare_protocols)

graph.add_edge(START, "compare_protocols")
graph.add_edge("compare_protocols", END)

graph = graph.compile()


response = graph.invoke({
    "protocol_id": "PROTOCOL-001",
    "old_version": "v1",
    "new_version": "v2"
})

print(response)