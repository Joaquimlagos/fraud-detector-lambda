terraform {
  required_version = ">= 1.7"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.4"
    }
  }
}

# Mesmo padrão do repo fraud-detector-infra-aws: provider único, sem alias.
# Para apontar pro LocalStack, copie local_override.tf.example -> local_override.tf
# (git-ignored). O LocalStack usado é o MESMO container do repo de infra —
# não sobe um segundo, só aponta pro mesmo http://localhost:4566.
provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  }
}

data "aws_caller_identity" "current" {}
