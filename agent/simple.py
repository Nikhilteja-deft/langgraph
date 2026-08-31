from langgraph.graph import StateGraph, START, END
from langgraph.types import Send
from pydantic import BaseModel, Field
from typing import Annotated
import operator


class ProtocolState(BaseModel):
    protocol_id: str
    old_version: str
    new_version: str

    changes: Annotated[list[str], operator.add] = Field(default_factory=list)

    analyzed_changes: Annotated[list[str], operator.add] = Field(
        default_factory=list
    )

    protocol_exists: bool = False
    changes_found: bool = False
    impact: str | None = None

    current_change: str | None = None


# --------------------------------------------------
# NODES
# --------------------------------------------------

def retrieve_protocol(state: ProtocolState):
    protocol_ids = [
        "PROTOCOL-001",
        "PROTOCOL-002",
        "PROTOCOL-003"
    ]

    return {
        "protocol_exists": state.protocol_id in protocol_ids
    }


def compare_protocols(state: ProtocolState):
    print(
        f"Comparing {state.old_version} "
        f"with {state.new_version}"
    )

    return {}


def extract_changes(state: ProtocolState):
    # Mocked for now.
    # Later an LLM/comparison service can detect these.

    if state.old_version != state.new_version:
        return {
            "changes_found": True,
            "changes": [
                "Eligibility criteria changed",
                "Visit schedule changed",
                "Consent language changed"
            ]
        }

    return {
        "changes_found": False
    }


def analyze_change(state: ProtocolState):
    print(f"Analyzing: {state.current_change}")

    return {
        "analyzed_changes": [
            f"Analyzed {state.current_change}"
        ]
    }


def assess_impact(state: ProtocolState):
    print("Assessing impact...")

    print("Analyzed changes:")
    for change in state.analyzed_changes:
        print(f"- {change}")

    return {
        "impact": "Potential site impact detected"
    }


# --------------------------------------------------
# ROUTING FUNCTIONS
# --------------------------------------------------

def route_protocol(state: ProtocolState):
    if state.protocol_exists:
        return "compare_protocols"

    return END


def route_changes(state: ProtocolState):
    if not state.changes_found:
        return END

    return [
        Send(
            "analyze_change",
            {
                "protocol_id": state.protocol_id,
                "old_version": state.old_version,
                "new_version": state.new_version,
                "current_change": change
            }
        )
        for change in state.changes
    ]


# --------------------------------------------------
# GRAPH
# --------------------------------------------------

graph = StateGraph(ProtocolState)

graph.add_node(retrieve_protocol)
graph.add_node(compare_protocols)
graph.add_node(extract_changes)
graph.add_node(analyze_change)
graph.add_node(assess_impact)


# START → retrieve
graph.add_edge(
    START,
    "retrieve_protocol"
)


# retrieve → compare OR END
graph.add_conditional_edges(
    "retrieve_protocol",
    route_protocol
)


# compare → extract
graph.add_edge(
    "compare_protocols",
    "extract_changes"
)


# extract → dynamic Send OR END
graph.add_conditional_edges(
    "extract_changes",
    route_changes
)


# all analyze_change executions join here
graph.add_edge(
    "analyze_change",
    "assess_impact"
)


# finish
graph.add_edge(
    "assess_impact",
    END
)


# --------------------------------------------------
# COMPILE + RUN
# --------------------------------------------------

graph = graph.compile()


response = graph.invoke({
    "protocol_id": "PROTOCOL-001",
    "old_version": "v1",
    "new_version": "v2"
})

print(response)