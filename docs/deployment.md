# Deployment & CI/CD Specification

This document details local execution, containerization, Infrastructure as Code with Terraform, and automated deployment via GitHub Actions.

---

## 1. Local Development (`uv`)

Run the application locally using Python virtual environments managed by `uv`:

```bash
# Sync dependencies
uv sync

# Run FastAPI development server
uv run uvicorn main:app --reload
```

---

## 2. Containerization (`Docker`)

The application is containerized using `Dockerfile`:

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml README.md ./
COPY agent/ ./agent/
COPY main.py ./

RUN pip install --no-cache-dir .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Build and run locally:
```bash
docker build -t langgraph-app .
docker run -p 8000:8000 langgraph-app
```

---

## 3. Infrastructure Provisioning (`Terraform`)

All infrastructure resides in [`terrafrom-started/`](file:///Users/nikhiltejachilakbattina/Desktop/langgraph/terrafrom-started/main.tf).

### Configuration Files:
- `terraform.tfvars`: Environment configuration (`environment = "dev"`).
- `variables.tf`: Computes `local.prefix = "langgraph-${var.environment}"`.
- `main.tf`: Provisions ECR repository (`langgraph-dev-repo`), VPC (`langgraph-dev-vpc`), ECS cluster (`langgraph-dev-cluster`), ECS service (`langgraph-dev-service`), and IAM Task roles with Bedrock model invoke policies.
- `outputs.tf`: Outputs `ecr_repository_url`.

### Deploying Infrastructure:
```bash
cd terrafrom-started
terraform init
terraform plan
terraform apply
```

---

## 4. Automated CI/CD (`GitHub Actions`)

The workflow file [`.github/workflows/docker-image.yml`](file:///Users/nikhiltejachilakbattina/Desktop/langgraph/.github/workflows/docker-image.yml) automates deployment on push to `main`:

```yaml
name: Docker Image CI & Push to ECR

on:
  push:
    branches: [ "main" ]

jobs:
  build-and-push:
    runs-on: ubuntu-latest

    steps:
    - name: Checkout Code
      uses: actions/checkout@v4

    - name: Configure AWS Credentials
      uses: aws-actions/configure-aws-credentials@v4
      with:
        aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
        aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
        aws-region: ${{ secrets.AWS_REGION }}

    - name: Login to Amazon ECR
      id: login-ecr
      uses: aws-actions/amazon-ecr-login@v2

    - name: Build, tag, and push image to Amazon ECR
      env:
        ECR_REGISTRY: ${{ steps.login-ecr.outputs.registry }}
        ECR_REPOSITORY: langgraph-dev-repo
        IMAGE_TAG: latest
      run: |
        docker build -t $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG .
        docker push $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG

    - name: Force ECS Deployment
      run: |
        aws ecs update-service \
          --cluster langgraph-dev-cluster \
          --service langgraph-dev-service \
          --force-new-deployment
```

### GitHub Secrets Required:
- `AWS_ACCESS_KEY_ID`: IAM user access key with ECR & ECS deployment permissions.
- `AWS_SECRET_ACCESS_KEY`: IAM user secret key.
- `AWS_REGION`: Target region (`us-east-1`).
