from langgraph.graph import StateGraph, START, END
from pydantic import BaseModel
from typing import Annotated
from pydantic import Field
import operator



class ProtocolState(BaseModel):
    protocol_id: str
    old_version: str
    new_version: str

    changes: Annotated[list[str], operator.add] = Field(default_factory=list)

    protocol_exists: bool = False
    changes_found: bool = False
    impact: str | None = None


def retrieve_protocol(state: ProtocolState):
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
        f"with {state.new_version}"
    )

    return {}


def extract_changes(state: ProtocolState):
    if state.old_version != state.new_version:
        return {
            "changes_found": True,
            "changes": ["Protocol version changed"]
        }

    return {
        "changes_found": False
    }


def route_changes(state: ProtocolState):
    if state.changes_found:
        return "analyze_changes"

    return END


def assess_impact(state: ProtocolState):
    print("Assessing impact...")

    return {
        "impact": "Potential site impact detected"
    }

def check_eligibility(state: ProtocolState):
    print("Checking eligibility changes")

    return {
        "changes": ["Eligibility criteria changed"]
    }


def check_schedule(state: ProtocolState):
    print("Checking schedule changes")

    return {
        "changes": ["Visit schedule changed"]
    }
def analyze_changes(state: ProtocolState):
    print("Analyzing detected changes")

    return {}


graph = StateGraph(ProtocolState)

graph.add_node(retrieve_protocol)
graph.add_node(compare_protocols)
graph.add_node(extract_changes)
graph.add_node(assess_impact)
graph.add_node(check_eligibility)
graph.add_node(check_schedule)
graph.add_node(analyze_changes)


graph.add_edge(
    START,
    "retrieve_protocol"
)

graph.add_conditional_edges(
    "retrieve_protocol",
    route_protocol
)

graph.add_edge(
    "compare_protocols",
    "extract_changes"
)
graph.add_edge(
    "analyze_changes",
    "check_eligibility"
)

graph.add_edge(
    "analyze_changes",
    "check_schedule"
)
graph.add_edge(
    "check_eligibility",
    "assess_impact"
)

graph.add_edge(
    "check_schedule",
    "assess_impact"
)

graph.add_conditional_edges(
    "extract_changes",
    route_changes
)



graph = graph.compile()


response = graph.invoke({
    "protocol_id": "PROTOCOL-001",
    "old_version": "v1",
    "new_version": "v2"
})

print(response)