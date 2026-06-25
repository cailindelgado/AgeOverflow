resource "aws_ecs_cluster" "ageoverflow" {
  name = "ageoverflow"
}

resource "aws_ecs_task_definition" "ageoverflow" {
  family                   = "ageoverflow"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = 1024
  memory                   = 2048
  execution_role_arn       = data.aws_iam_role.lab.arn
  task_role_arn            = data.aws_iam_role.lab.arn

  container_definitions = <<DEFINITION
  [
    {
      "image": "${local.image}",
      "cpu": 1024,
      "memory": 2048,
      "name": "gcas",
      "networkMode": "awsvpc",
      "portMappings": [
        {
          "containerPort": 8080,
          "hostPort": 8080
        }
      ],
      "environment": [
        {
        "name": "SQLALCHEMY_DATABASE_URI",
        "value": "postgresql://${local.database_username}:${local.database_password}@${aws_db_instance.ageoverflow_database.address}:${aws_db_instance.ageoverflow_database.port}/${aws_db_instance.ageoverflow_database.db_name}"
        },
        { "name": "CELERY_BROKER_URL", "value": "sqs://" }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ageoverflow/gcas",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs",
          "awslogs-create-group": "true"
        }
      }
    }
  ]
  DEFINITION
}

resource "aws_ecs_service" "ageoverflow" {
  name            = "ageoverflow"
  cluster         = aws_ecs_cluster.ageoverflow.id
  task_definition = aws_ecs_task_definition.ageoverflow.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = data.aws_subnets.private.ids
    security_groups  = [aws_security_group.ageoverflow.id]
    assign_public_ip = true
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.ageoverflow.arn
    container_name   = "gcas"
    container_port   = 8080
  }

  depends_on = [aws_lb.ageoverflow]
}

resource "aws_security_group" "ageoverflow" {
  name        = "ageoverflow"
  description = "Ageoverflow Security Group"

  ingress {
    from_port   = 8080
    to_port     = 8080
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}