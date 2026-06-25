terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
    docker = {
      source  = "kreuzwerker/docker"
      version = "3.6.2"
    }
  }
}

provider "aws" {
  region                   = "us-east-1"
  shared_credentials_files = ["./credentials"]
  default_tags {
    tags = {
      Course     = "CSSE6400"
      Name       = "Ageoverflow"
      Automation = "Terraform"
    }
  }
}

locals {
  image             = docker_registry_image.ageoverflow.name
  image_worker      = docker_registry_image.ageoverflow_workers.name
  database_username = "administrator"
  database_password = "verySecretPassword"
  celery_cmd        = "pipx run poetry run celery --app GCAS.tasks.eng worker --loglevel=info -Q"
}

data "aws_iam_role" "lab" {
  name = "LabRole"
}

data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "private" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}