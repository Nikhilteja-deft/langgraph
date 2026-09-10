# Clinical Protocol Impact Agent

A LangGraph-based AI workflow for analyzing clinical protocol amendments, evaluating site operational impact, collecting supporting evidence, and routing assessments through Human-in-the-Loop (HITL) review.

The application is exposed through FastAPI, containerized with Docker, deployed to AWS ECS Fargate using Terraform, and continuously deployed through GitHub Actions.

---

## Architecture Overview

```text
                        Developer
                           │
                        git push
                           │
                           ▼
                    GitHub Actions
                           │
                build Docker image
                           │
                           ▼
                    Amazon ECR
                  container registry
                           │
                     ECS pulls image
                           │
                           ▼
┌──────────────────────────────────────────────────────┐
│                         AWS                          │
│                                                      │
│   VPC                                                │
│   ┌──────────────────────────────────────────────┐   │
│   │                                              │   │
│   │          ECS Fargate Task                    │   │
│   │          ┌─────────────────────┐             │   │
│   │          │ Docker Container    │             │   │
│   │          │                     │             │   │
│   │ Client → │ FastAPI :8000       │             │   │
│   │          │       │             │             │   │
│   │          │       ▼             │             │   │
│   │          │   LangGraph         │             │   │
│   │          │       │             │             │   │
│   │          │       ├─ retry      │             │   │
│   │          │       ├─ routing    │             │   │
│   │          │       ├─ Send       │             │   │
│   │          │       ├─ loop       │             │   │
│   │          │       └─ HITL       │             │   │
│   │          │            │        │             │   │
│   │          └────────────┼────────┘             │   │
│   │                       │                      │   │
│   └───────────────────────┼──────────────────────┘   │
│                           │                          │
│                           ▼                          │
│                    Amazon Bedrock                    │
│                     Nova Pro                         │
│                                                      │
│   Container stdout/stderr ───────→ CloudWatch Logs  │
└──────────────────────────────────────────────────────┘
```

---

## Agent Workflow

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

### Execution Steps
1. **Retrieve Protocol**: Fetches protocol versions from the store with automatic retries for transient failures.
2. **Compare Protocols**: Compares protocol baseline (`old_version`) against the new amendment (`new_version`).
3. **Extract Changes**: Identifies specific clinical criteria modifications (eligibility, visit schedules, consent).
4. **Fan-Out Analysis (`Send`)**: Dynamically spawns parallel analysis workers per extracted change.
5. **LLM Reasoning**: Analyzes each change using Amazon Bedrock Nova Pro (`us.amazon.nova-pro-v1:0`) with fast fallback handling.
6. **Impact Assessment**: Synthesizes change analysis and evaluates overall site impact.
7. **Evidence Retrieval Loop**: Recursively gathers supporting documentation (SOPs, site activation data) if evidence is initially insufficient.
8. **Human Review (`interrupt()`)**: Pauses state execution, saving state against a persistent `thread_id`.
9. **Resume Workflow (`Command(resume=...)`)**: Resumes the exact state upon receiving reviewer decision (`approve`, `revise`, `reject`).
10. **Idempotent Record**: Persists review outcomes using deterministic key upserts.

---

## API Documentation

### 1. Start Protocol Assessment
**Endpoint:** `POST /api/v1/protocol/compare`

**Request Body:**
```json
{
  "protocol_id": "PROTOCOL-002",
  "old_version": "v2",
  "new_version": "v3"
}
```

**Response (Interrupted for Human Review):**
```json
{
  "thread_id": "04931431-65e4-4fb2-97fe-bc5a87e3f7b2",
  "result": {
    "protocol_id": "PROTOCOL-002",
    "impact": "Potential site impact detected with supporting evidence",
    "__interrupt__": [
      {
        "value": {
          "question": "Review the protocol impact assessment",
          "allowed_actions": ["approve", "revise", "reject"]
        }
      }
    ]
  }
}
```

### 2. Resume Human Review
**Endpoint:** `POST /api/v1/protocol/review`

**Request Body:**
```json
{
  "thread_id": "04931431-65e4-4fb2-97fe-bc5a87e3f7b2",
  "action": "approve",
  "comment": "Approved following protocol amendment verification."
}
```

---

## Infrastructure & Deployment

- **Containerization**: Docker container running FastAPI with Uvicorn on port `8000`.
- **Amazon ECR**: Private container registry (`langgraph-dev-repo`) storing application images.
- **Amazon ECS Fargate**: Serverless container execution hosting the FastAPI + LangGraph service.
- **Terraform IaC**: Infrastructure provisioning located in [`terrafrom-started/`](file:///Users/nikhiltejachilakbattina/Desktop/langgraph/terrafrom-started/main.tf), managing VPCs, subnets, ECR, ECS Fargate, IAM Task Roles, and CloudWatch Log Groups.
- **GitHub Actions CI/CD**: Automated pipeline in [`.github/workflows/docker-image.yml`](file:///Users/nikhiltejachilakbattina/Desktop/langgraph/.github/workflows/docker-image.yml) that builds Docker images, pushes to ECR, and forces ECS service redeployments on push to `main`.

---

## Amazon Bedrock Integration

- **Model**: Amazon Nova Pro (`us.amazon.nova-pro-v1:0` via `ChatBedrockConverse`).
- **IAM Authorization**: ECS Task Role is granted `bedrock:InvokeModel` and `bedrock:InvokeModelWithResponseStream` permissions via Terraform.
- **Fault Tolerance**: Standard `max_retries=0` fail-fast settings combined with inline try-except fallbacks ensure API resilience under model throttling or quota limits.

---

## Observability & Documentation

- **Logging**: ECS task logs stream directly to CloudWatch Log Group `/aws/ecs/langgraph-dev/fastapi-app`.
- **Detailed Documentation**:
  - [Architecture Guide](file:///Users/nikhiltejachilakbattina/Desktop/langgraph/docs/architecture.md)
  - [LangGraph Workflow Specification](file:///Users/nikhiltejachilakbattina/Desktop/langgraph/docs/langgraph-flow.md)
  - [Deployment & CI/CD Guide](file:///Users/nikhiltejachilakbattina/Desktop/langgraph/docs/deployment.md)

---

## Current Development Notes

The workflow engine currently uses `InMemorySaver` for local state persistence across nodes.

*Note for production deployment:* A persistent PostgreSQL/Aurora-backed checkpointer (`AsyncPostgresSaver`) will be introduced to maintain state durability across container restarts or ECS task auto-scaling.
