from langgraph.graph import StateGraph, START, END
from langgraph.types import Send, RetryPolicy, interrupt, Command
from langgraph.runtime import Runtime
from langgraph.checkpoint.memory import InMemorySaver

from pydantic import BaseModel, Field
from typing import Annotated
import operator


# ============================================================
# MOCK DATABASE FOR IDEMPOTENCY DEMO
# ============================================================

# Pretend this is an Aurora/PostgreSQL review table.
#
# We use a deterministic key and UPSERT behavior.
# Running the same write again replaces the same record
# instead of creating duplicates.

REVIEW_STORE = {}


# ============================================================
# STATE
# ============================================================

class ProtocolState(BaseModel):
    protocol_id: str
    old_version: str
    new_version: str

    # Reducer
    changes: Annotated[list[str], operator.add] = Field(
        default_factory=list
    )

    # Reducer for Send worker results
    analyzed_changes: Annotated[list[str], operator.add] = Field(
        default_factory=list
    )

    # Reducer
    evidence: Annotated[list[str], operator.add] = Field(
        default_factory=list
    )

    protocol_exists: bool = False
    changes_found: bool = False

    impact: str | None = None

    evidence_sufficient: bool = False
    evidence_attempts: int = 0

    # -----------------------------
    # HITL STATE
    # -----------------------------

    review_decision: str | None = None
    review_comment: str | None = None
    review_status: str = "pending"

    review_recorded: bool = False


# ============================================================
# NODES
# ============================================================

def retrieve_protocol(
    state: ProtocolState,
    runtime: Runtime
):
    attempt = runtime.execution_info.node_attempt

    print(
        f"Retrieve protocol attempt: {attempt}"
    )

    # --------------------------------------------------------
    # RETRY DEMO
    # --------------------------------------------------------
    # Pretend Aurora/network fails once.
    # Remove this mocked failure later.

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

    if state.old_version != state.new_version:

        return {
            "changes_found": True,

            # Mocked for now
            "changes": [
                "Eligibility criteria changed",
                "Visit schedule changed",
                "Consent language changed"
            ]
        }

    return {
        "changes_found": False
    }


# ------------------------------------------------------------
# SEND WORKER
# ------------------------------------------------------------

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
    # evidence is intentionally insufficient

    if state.evidence_attempts == 0:

        print("Evidence is insufficient")

        return {
            "evidence_sufficient": False,
            "impact": "More evidence required"
        }

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


# ============================================================
# 20. INTERRUPT / HUMAN REVIEW
# ============================================================

def human_review(state: ProtocolState):

    # IMPORTANT:
    #
    # Do NOT perform a non-idempotent database write
    # before interrupt().
    #
    # When resumed, LangGraph starts this node again
    # from the beginning.

    reviewer_response = interrupt(
        {
            "question":
                "Review the protocol impact assessment",

            "protocol_id":
                state.protocol_id,

            "impact":
                state.impact,

            "changes":
                state.analyzed_changes,

            "evidence":
                state.evidence,

            "allowed_actions": [
                "approve",
                "revise",
                "reject"
            ]
        }
    )

    # Command(resume=...) value appears here

    decision = reviewer_response["action"]
    comment = reviewer_response.get(
        "comment",
        ""
    )

    print(
        f"Reviewer decision: {decision}"
    )

    return {
        "review_decision": decision,
        "review_comment": comment,
        "review_status": decision
    }


# ============================================================
# 22. IDEMPOTENT SIDE EFFECT
# ============================================================

def record_review(state: ProtocolState):

    # Deterministic idempotency key
    review_key = (
        f"{state.protocol_id}:"
        f"{state.old_version}:"
        f"{state.new_version}"
    )

    # --------------------------------------------------------
    # IDEMPOTENT UPSERT
    # --------------------------------------------------------
    #
    # Same review_key will update the same record.
    #
    # It will NOT:
    #
    # INSERT row 1
    # INSERT row 2
    # INSERT row 3
    #
    # if this operation gets executed again.

    REVIEW_STORE[review_key] = {
        "protocol_id":
            state.protocol_id,

        "old_version":
            state.old_version,

        "new_version":
            state.new_version,

        "decision":
            state.review_decision,

        "comment":
            state.review_comment
    }

    print(
        f"Review persisted: {review_key}"
    )

    return {
        "review_recorded": True
    }


# ============================================================
# ROUTING FUNCTIONS
# ============================================================

def route_protocol(state: ProtocolState):

    if state.protocol_exists:
        return "compare_protocols"

    return END


# ------------------------------------------------------------
# SEND — dynamic fan-out
# ------------------------------------------------------------

def route_changes(state: ProtocolState):

    if not state.changes_found:
        return END

    return [
        Send(
            "analyze_change",
            {
                "current_change": change
            }
        )
        for change in state.changes
    ]


# ------------------------------------------------------------
# BUSINESS LOOP
# ------------------------------------------------------------

def route_assessment(state: ProtocolState):

    if state.evidence_sufficient:
        return "human_review"

    # Safety condition
    if state.evidence_attempts >= 2:
        return "human_review"

    return "retrieve_evidence"


# ============================================================
# GRAPH
# ============================================================

builder = StateGraph(ProtocolState)


# ------------------------------------------------------------
# NODES
# ------------------------------------------------------------

builder.add_node(
    "retrieve_protocol",
    retrieve_protocol,

    retry_policy=RetryPolicy(
        max_attempts=3,
        retry_on=ConnectionError
    )
)

builder.add_node(
    "compare_protocols",
    compare_protocols
)

builder.add_node(
    "extract_changes",
    extract_changes
)

builder.add_node(
    "analyze_change",
    analyze_change
)

builder.add_node(
    "assess_impact",
    assess_impact
)

builder.add_node(
    "retrieve_evidence",
    retrieve_evidence
)

builder.add_node(
    "human_review",
    human_review
)

builder.add_node(
    "record_review",
    record_review
)


# ============================================================
# EDGES
# ============================================================

builder.add_edge(
    START,
    "retrieve_protocol"
)


builder.add_conditional_edges(
    "retrieve_protocol",
    route_protocol
)


builder.add_edge(
    "compare_protocols",
    "extract_changes"
)


# Send / dynamic fan-out
builder.add_conditional_edges(
    "extract_changes",
    route_changes
)


# Send workers fan back in
builder.add_edge(
    "analyze_change",
    "assess_impact"
)


# Business loop OR human review
builder.add_conditional_edges(
    "assess_impact",
    route_assessment
)


# Evidence loop
builder.add_edge(
    "retrieve_evidence",
    "assess_impact"
)


# After human resumes
builder.add_edge(
    "human_review",
    "record_review"
)


builder.add_edge(
    "record_review",
    END
)


# ============================================================
# 17. CHECKPOINTER
# ============================================================

checkpointer = InMemorySaver()


# ============================================================
# 19. PERSISTENCE ENABLED DURING COMPILE
# ============================================================

graph = builder.compile(
    checkpointer=checkpointer
)

"""
KEEP OUTSIDE __main__
─────────────────────
State
nodes
routers
builder
nodes registration
edges
InMemorySaver
graph = builder.compile(...)


PUT INSIDE __main__
─────────────────────
config
graph.invoke(...)
get_state(...)
input(...)
Command(resume=...)
prints

"""

if __name__=="__main__":

    # ============================================================
    # 18. THREAD ID
    # ============================================================

    config = {
        "configurable": {
            "thread_id":
                "protocol-PROTOCOL-001-review-001"
        }
    }

    # ============================================================
    # FIRST RUN
    # ============================================================

    print("\n========== STARTING GRAPH ==========\n")

    result = graph.invoke(
        {
            "protocol_id":
                "PROTOCOL-001",

            "old_version":
                "v1",

            "new_version":
                "v2"
        },

        config=config
    )

    # ============================================================
    # GRAPH SHOULD NOW BE PAUSED
    # ============================================================

    print("\n========== INTERRUPTED ==========\n")

    print(result)

    # ============================================================
    # 19. INSPECT PERSISTED STATE
    # ============================================================

    snapshot = graph.get_state(config)

    print("\n========== SAVED CHECKPOINT ==========\n")

    print("Saved state:")
    print(snapshot.values)

    print("\nNext node:")
    print(snapshot.next)

    # ============================================================
    # SIMULATE HUMAN REVIEWER
    # ============================================================

    print("\n========== HUMAN REVIEW ==========\n")

    decision = input(
        "Enter decision "
        "(approve / revise / reject): "
    ).strip().lower()

    while decision not in {
        "approve",
        "revise",
        "reject"
    }:
        decision = input(
            "Invalid decision. "
            "Enter approve / revise / reject: "
        ).strip().lower()

    comment = input(
        "Reviewer comment: "
    )

    # ============================================================
    # 21. COMMAND(RESUME=...)
    # ============================================================

    print("\n========== RESUMING GRAPH ==========\n")

    final_result = graph.invoke(
        Command(
            resume={
                "action": decision,
                "comment": comment
            }
        ),

        # SAME thread_id is critical
        config=config
    )

    # ============================================================
    # FINAL RESULT
    # ============================================================

    print("\n========== FINAL STATE ==========\n")

    print(final_result)

    # ============================================================
    # SHOW IDEMPOTENT REVIEW RECORD
    # ============================================================

    print("\n========== REVIEW STORE ==========\n")

    print(REVIEW_STORE)
