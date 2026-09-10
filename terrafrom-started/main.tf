provider "aws" {
  region = "us-east-1"
}


resource "aws_ecr_repository" "elastic_container_registry" {
  name                 = "${local.prefix}-repo"
  image_tag_mutability = "MUTABLE"
  force_delete         = true

  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "aws_ecr_lifecycle_policy" "elastic_container_registry" {
  repository = aws_ecr_repository.elastic_container_registry.name

  policy = <<EOF
{
  "rules": [
    {
      "rulePriority": 1,
      "description": "Expire images older than 14 days",
      "selection": {
        "tagStatus": "untagged",
        "countType": "sinceImagePushed",
        "countUnit": "days",
        "countNumber": 14
      },
      "action": {
        "type": "expire"
      }
    }
  ]
}
EOF
}


module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "6.7.0"

  name = "${local.prefix}-vpc"
  cidr = "10.0.0.0/16"

  azs             = ["us-east-1a", "us-east-1b", "us-east-1c"]
  private_subnets = ["10.0.1.0/24", "10.0.2.0/24"]
  public_subnets  = ["10.0.101.0/24", "10.0.102.0/24"]

  enable_dns_hostnames = true
}


module "ecs" {
  source  = "terraform-aws-modules/ecs/aws"
  version = "~> 7.6"

  cluster_name = "${local.prefix}-cluster"

  cluster_capacity_providers = ["FARGATE"]

  services = {
    "${local.prefix}-service" = {
      cpu    = 256
      memory = 512

      assign_public_ip = true
      subnet_ids       = module.vpc.public_subnets

      tasks_iam_role_statements = [
        {
          effect = "Allow"
          actions = [
            "bedrock:InvokeModel",
            "bedrock:InvokeModelWithResponseStream"
          ]
          resources = ["*"]
        }
      ]

      container_definitions = {
        fastapi-app = {
          cpu       = 256
          memory    = 512
          essential = true

          cloudwatch_log_group_name = "/aws/ecs/${local.prefix}/fastapi-app"
          image                     = "${aws_ecr_repository.elastic_container_registry.repository_url}:latest"
          readonlyRootFilesystem    = false
          portMappings = [
            {
              name          = "http"
              containerPort = 8080
              protocol      = "tcp"
            }
          ]
        }
      }

      security_group_ingress_rules = {
        allow_fastapi = {
          description = "Allow FastAPI traffic"
          from_port   = 8080
          to_port     = 8080
          ip_protocol = "tcp"
          cidr_ipv4   = "0.0.0.0/0"
        }
      }

      security_group_egress_rules = {
        allow_all_outbound = {
          ip_protocol = "-1"
          cidr_ipv4   = "0.0.0.0/0"
        }
      }
    }
  }
}