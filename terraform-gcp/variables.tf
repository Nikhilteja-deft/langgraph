variable "environment" {
  type        = string
  description = "Deployment environment name"
  default     = "dev"

}
locals {
  prefix = "langgraph-${var.environment}"
}

variable "project" {
  default = "langgraphagentv0"
}

variable "region" {
  default = "us-central1"
}

variable "zone" {
  default = "us-central1-c"
}
