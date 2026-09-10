# System Architecture

This document describes the cloud infrastructure, network topology, and application architecture for the Clinical Protocol Impact Agent.

---

## High-Level Architecture

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

## Infrastructure Components

### 1. VPC & Networking (`terraform-aws-modules/vpc/aws`)
- **VPC CIDR**: `10.0.0.0/16` scoped by environment (`langgraph-dev-vpc`).
- **Subnets**: Public subnets (`10.0.101.0/24`, `10.0.102.0/24`) for ECS task routing and internet access to AWS Bedrock APIs.
- **Internet Gateway**: Enables outbound communication to Amazon Bedrock endpoints.

### 2. Amazon ECS Fargate (`terraform-aws-modules/ecs/aws`)
- **Serverless Compute**: Runs containerized application tasks without managing EC2 instances.
- **Task CPU & Memory**: 256 CPU units (0.25 vCPU) and 512 MB RAM.
- **Security Groups**: Allows inbound TCP traffic on port `8000` (FastAPI) and unrestricted outbound TCP traffic (`0.0.0.0/0`) for API calls.

### 3. IAM Permissions & Security
- **Execution Role (`task_exec`)**: Grants ECS permissions to pull images from ECR and send container logs to CloudWatch.
- **Task Role (`tasks`)**: Grants the containerized Python application permission to invoke Amazon Bedrock models:
  - `bedrock:InvokeModel`
  - `bedrock:InvokeModelWithResponseStream`

### 4. Amazon Bedrock Integration
- **Model**: Amazon Nova Pro (`us.amazon.nova-pro-v1:0` / `amazon.nova-pro-v1:0`).
- **SDK**: `langchain_aws.ChatBedrockConverse` integrated inside parallel node execution.

### 5. Observability & Logging
- Log Driver: `awslogs` streaming container stdout/stderr directly to CloudWatch Log Group `/aws/ecs/langgraph-dev/fastapi-app`.
