from langgraph.graph import StateGraph, START, END
from langgraph.types import Send, RetryPolicy
from langgraph.runtime import Runtime

from pydantic import BaseModel, Field
from typing import Annotated
import operator


# ==================================================
# STATE
# ==================================================

class ProtocolState(BaseModel):
    protocol_id: str
    old_version: str
    new_version: str

    # Reducer: accumulate detected changes
    changes: Annotated[list[str], operator.add] = Field(
        default_factory=list
    )

    # Reducer: collect results from Send workers
    analyzed_changes: Annotated[list[str], operator.add] = Field(
        default_factory=list
    )

    # Reducer: accumulate retrieved evidence
    evidence: Annotated[list[str], operator.add] = Field(
        default_factory=list
    )

    protocol_exists: bool = False
    changes_found: bool = False

    impact: str | None = None

    evidence_sufficient: bool = False
    evidence_attempts: int = 0


# ==================================================
# NODES
# ==================================================

def retrieve_protocol(
    state: ProtocolState,
    runtime: Runtime
):
    attempt = runtime.execution_info.node_attempt

    print(f"Retrieve protocol attempt: {attempt}")

    # Mock technical failure on first attempt
    if attempt == 1:
        print("Temporary database connection failure")

        raise ConnectionError(
            "Aurora connection failed"
        )

    protocol_ids = [
        "PROTOCOL-001",
        "PROTOCOL-002",
        "PROTOCOL-003"
    ]

    print("Protocol retrieval successful")

    return {
        "protocol_exists":
            state.protocol_id in protocol_ids
    }


def compare_protocols(state: ProtocolState):

    print(
        f"Comparing {state.old_version} "
        f"with {state.new_version}"
    )

    return {}


def extract_changes(state: ProtocolState):

    # Mock changes for now.
    # Later an LLM/comparison service can generate these.

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


# Send gives this node a custom dictionary,
# not the entire ProtocolState object.
def analyze_change(state: dict):

    current_change = state["current_change"]

    print(
        f"Analyzing: {current_change}"
    )

    return {
        "analyzed_changes": [
            f"Analyzed {current_change}"
        ]
    }


def assess_impact(state: ProtocolState):

    print("Assessing impact...")

    # First assessment:
    # we intentionally say evidence is insufficient.
    if state.evidence_attempts == 0:

        print("Evidence is insufficient")

        return {
            "evidence_sufficient": False,
            "impact": "More evidence required"
        }

    # After retrieve_evidence has executed
    print("Evidence is sufficient")

    return {
        "evidence_sufficient": True,
        "impact":
            "Potential site impact detected "
            "with supporting evidence"
    }


def retrieve_evidence(state: ProtocolState):

    print("Retrieving additional evidence...")

    return {
        "evidence": [
            "Site activation data",
            "Protocol amendment documentation",
            "Relevant SOP evidence"
        ],

        "evidence_attempts":
            state.evidence_attempts + 1
    }


# ==================================================
# ROUTING FUNCTIONS
# ==================================================

def route_protocol(state: ProtocolState):

    if state.protocol_exists:
        return "compare_protocols"

    return END


def route_changes(state: ProtocolState):

    if not state.changes_found:
        return END

    # Dynamic fan-out
    return [
        Send(
            "analyze_change",
            {
                "current_change": change
            }
        )
        for change in state.changes
    ]


def route_assessment(state: ProtocolState):

    # Business condition satisfied
    if state.evidence_sufficient:
        return END

    # Safety condition
    if state.evidence_attempts >= 2:
        return END

    # Business loop
    return "retrieve_evidence"


# ==================================================
# GRAPH
# ==================================================

graph = StateGraph(ProtocolState)


# --------------------------------------------------
# REGISTER NODES
# --------------------------------------------------

graph.add_node(
    "retrieve_protocol",
    retrieve_protocol,

    # Technical retry
    retry_policy=RetryPolicy(
        max_attempts=3,
        retry_on=ConnectionError
    )
)

graph.add_node(
    "compare_protocols",
    compare_protocols
)

graph.add_node(
    "extract_changes",
    extract_changes
)

graph.add_node(
    "analyze_change",
    analyze_change
)

graph.add_node(
    "assess_impact",
    assess_impact
)

graph.add_node(
    "retrieve_evidence",
    retrieve_evidence
)


# ==================================================
# EDGES
# ==================================================

# START
graph.add_edge(
    START,
    "retrieve_protocol"
)


# Conditional:
# protocol found → compare
# not found → END
graph.add_conditional_edges(
    "retrieve_protocol",
    route_protocol
)


# Normal edge
graph.add_edge(
    "compare_protocols",
    "extract_changes"
)


# Conditional + Send:
# no changes → END
# changes → dynamic analyze_change executions
graph.add_conditional_edges(
    "extract_changes",
    route_changes
)


# Fan-in:
# all dynamically-created analyze_change tasks
# feed into assess_impact
graph.add_edge(
    "analyze_change",
    "assess_impact"
)


# Business decision
graph.add_conditional_edges(
    "assess_impact",
    route_assessment
)


# Business loop
graph.add_edge(
    "retrieve_evidence",
    "assess_impact"
)


# ==================================================
# COMPILE
# ==================================================

graph = graph.compile()


# ==================================================
# INVOKE
# ==================================================

response = graph.invoke({
    "protocol_id": "PROTOCOL-001",
    "old_version": "v1",
    "new_version": "v2"
})


print("\nFINAL STATE")
print(response)