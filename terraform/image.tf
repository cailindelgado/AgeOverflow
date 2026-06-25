data "aws_ecr_authorization_token" "ecr_token" {}

provider "docker" {
  registry_auth {
    address  = data.aws_ecr_authorization_token.ecr_token.proxy_endpoint
    username = data.aws_ecr_authorization_token.ecr_token.user_name
    password = data.aws_ecr_authorization_token.ecr_token.password
  }
}

resource "docker_image" "ageoverflow" {
  name = "${aws_ecr_repository.ageoverflow.repository_url}:latest"
  build {
    context = "."
  }
}

resource "docker_registry_image" "ageoverflow" {
  name = docker_image.ageoverflow.name
}

resource "aws_ecr_repository" "ageoverflow" {
  name = "ageoverflow"
}

resource "docker_image" "ageoverflow_workers" {
  name = "${aws_ecr_repository.ageoverflow_workers.repository_url}:latest"
  build {
    context    = "."
    dockerfile = "Dockerfile.worker"
  }
}

resource "docker_registry_image" "ageoverflow_workers" {
  name = docker_image.ageoverflow_workers.name
}

resource "aws_ecr_repository" "ageoverflow_workers" {
  name = "ageoverflow-workers"
}