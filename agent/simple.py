from langgraph.graph import StateGraph, START, END
from pydantic import BaseModel


class ProtocolState(BaseModel):
    protocol_id: str
    old_version: str
    new_version: str
    protocol_exists: bool = False


def retrive_protocol(state: ProtocolState):
    protocol_ids = [
        "PROTOCOL-001",
        "PROTOCOL-002",
        "PROTOCOL-003"
    ]

    return {
        "protocol_exists": state.protocol_id in protocol_ids
    }


def route_protocol(state: ProtocolState):
    if state.protocol_exists:
        return "compare_protocols"

    return END


def compare_protocols(state: ProtocolState):
    print(
        f"Comparing {state.old_version} "
        f"and {state.new_version}"
    )

    return {}


graph = StateGraph(ProtocolState)

graph.add_node(retrive_protocol)
graph.add_node(compare_protocols)

graph.add_edge(START, "retrive_protocol")

graph.add_conditional_edges(
    "retrive_protocol",
    route_protocol
)

graph.add_edge("compare_protocols", END)

graph = graph.compile()


response = graph.invoke({
    "protocol_id": "PROTOCOL-001",
    "old_version": "v1",
    "new_version": "v2"
})

print(response)