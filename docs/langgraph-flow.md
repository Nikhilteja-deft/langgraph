# LangGraph State Machine & Workflow Specification

This document details the internal design of the LangGraph state machine, worker fan-out pattern, human-in-the-loop (HITL) interrupt/resume mechanism, and state reducers.

---

## Graph Topology

```text
POST /api/v1/protocol/compare
              │
              ▼
      retrieve_protocol
              │
         retry policy
              ▼
      compare_protocols
              │
              ▼
       extract_changes
              │
              ▼
       Send fan-out
        /     |      \
       ▼      ▼       ▼
   analyze  analyze  analyze
   change   change   change
       │      │       │
       └──────┼───────┘
              │
       Amazon Bedrock
              │
              ▼
        assess_impact
              │
     insufficient evidence?
          yes │  no
              │
      retrieve_evidence
              │
              └──────↺
                     │
                     ▼
                human_review
                     │
                  interrupt()
                     │
                     ▼
POST /api/v1/protocol/review
                     │
              Command(resume=...)
                     │
                     ▼
                record_review
                     │
                    END
```

---

## State Schema & Reducers

The workflow state is defined using Pydantic's `BaseModel` with Annotated reducers:

```python
class ProtocolState(BaseModel):
    protocol_id: str
    old_version: str
    new_version: str

    # Reducer: appends change strings across execution
    changes: Annotated[list[str], operator.add] = Field(default_factory=list)

    # Reducer: aggregates fan-out Send worker results
    analyzed_changes: Annotated[list[str], operator.add] = Field(default_factory=list)

    # Reducer: accumulates retrieved evidence
    evidence: Annotated[list[str], operator.add] = Field(default_factory=list)

    protocol_exists: bool = False
    changes_found: bool = False
    impact: str | None = None
    evidence_sufficient: bool = False
    evidence_attempts: int = 0

    # Human-in-the-Loop State
    review_decision: str | None = None
    review_comment: str | None = None
    review_status: str = "pending"
    review_recorded: bool = False
```

---

## Key Workflow Patterns

### 1. Transient Retry Policy (`RetryPolicy`)
The `retrieve_protocol` node is configured with an automatic retry policy for database/network connection drops:
```python
builder.add_node(
    "retrieve_protocol",
    retrieve_protocol,
    retry_policy=RetryPolicy(max_attempts=3, retry_on=ConnectionError)
)
```

### 2. Dynamic Fan-Out Workers (`Send`)
When protocol amendment changes are detected, `route_changes` dynamically spawns a parallel worker for each individual change:
```python
def route_changes(state: ProtocolState):
    if not state.changes_found:
        return END
    return [
        Send("analyze_change", {"current_change": change})
        for change in state.changes
    ]
```

### 3. LLM Integration with Fallback
Inside `analyze_change`, each worker invokes Amazon Bedrock Nova Pro (`ChatBedrockConverse`). To ensure resilience under AWS quota throttling, exceptions return a graceful fallback string rather than crashing the execution graph:
```python
try:
    response = model.invoke(...)
    result_text = response.content
except Exception as e:
    result_text = f"[Fallback Analysis] Change: {current_change} - Unable to reach LLM ({type(e).__name__}). Flagged for manual review."
```

### 4. Human-in-the-Loop Interrupt & Resume
- **Pause**: In `human_review`, calling `interrupt({...})` halts the execution graph and persists state against a unique `thread_id`.
- **Resume**: When a user submits their review (`approve`, `revise`, `reject`), the `/api/v1/protocol/review` endpoint passes `Command(resume={"action": decision, "comment": comment})` with the matching `thread_id` to safely resume execution.

### 5. Idempotent Writes
`record_review` constructs a deterministic key (`f"{state.protocol_id}:{state.old_version}:{state.new_version}"`) to ensure re-executing or resuming nodes does not create duplicate database records.
