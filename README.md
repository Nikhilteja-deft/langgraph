# LangGraph Protocol Impact Agent

Short project description

## Project Flow
API → LangGraph → HITL → Review → Resume

## Deployment Flow
Git push
→ GitHub Actions
→ Docker build
→ ECR
→ ECS Fargate

## AWS Architecture
VPC
→ public subnets
→ ECS Fargate
→ FastAPI :8000

ECR → ECS image pull
ECS logs → CloudWatch

## Main Components
FastAPI
LangGraph
Docker
Terraform
ECR
ECS Fargate
GitHub Actions

## Current Limitation
InMemorySaver is not durable across ECS task replacement.

## Docs
docs/architecture.md
