resource "aws_ecs_task_definition" "ageoverflow_worker_urgent" {
  family                   = "ageoverflow_workers"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = 2048
  memory                   = 4096
  execution_role_arn       = data.aws_iam_role.lab.arn
  task_role_arn            = data.aws_iam_role.lab.arn

  container_definitions = <<DEFINITION
  [
    {
      "image": "${local.image_worker}",
      "cpu": 2048,
      "memory": 4096,
      "name": "worker-urgent",
      "networkMode": "awsvpc",
      "environment": [
        {
        "name": "SQLALCHEMY_DATABASE_URI",
        "value": "postgresql://${local.database_username}:${local.database_password}@${aws_db_instance.ageoverflow_database.address}:${aws_db_instance.ageoverflow_database.port}/${aws_db_instance.ageoverflow_database.db_name}"
        },
        { "name": "CELERY_BROKER_URL", "value": "sqs://" }
      ],
      "command": ["sh", "-c", "${local.celery_cmd} eng-urgent"],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ageoverflow/worker-urgent",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs",
          "awslogs-create-group": "true"
        }
      }
    }
  ]
  DEFINITION
}

resource "aws_ecs_service" "ageoverflow_worker_urgent" {
  name            = "ageoverflow_worker_urgent"
  cluster         = aws_ecs_cluster.ageoverflow.id
  task_definition = aws_ecs_task_definition.ageoverflow_worker_urgent.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = data.aws_subnets.private.ids
    security_groups  = [aws_security_group.ageoverflow_worker_urgent_sg.id]
    assign_public_ip = true
  }

  depends_on = [aws_lb.ageoverflow, aws_db_instance.ageoverflow_database]
}

resource "aws_security_group" "ageoverflow_worker_urgent_sg" {
  name        = "ageoverflow_worker_urgent_sg"
  description = "AgeOverflow worker_urgent Security Group"

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "ageoverflow_worker_urgent_security_group"
  }
}

resource "aws_ecs_task_definition" "ageoverflow_worker_non_urgent" {
  family                   = "ageoverflow_workers"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = 2048
  memory                   = 4096
  execution_role_arn       = data.aws_iam_role.lab.arn
  task_role_arn            = data.aws_iam_role.lab.arn
  depends_on               = [aws_ecs_task_definition.ageoverflow_worker_urgent]

  container_definitions = <<DEFINITION
  [
    {
      "image": "${local.image_worker}",
      "cpu": 2048,
      "memory": 4096,
      "name": "worker-non-urgent",
      "networkMode": "awsvpc",
      "environment": [
        {
        "name": "SQLALCHEMY_DATABASE_URI",
        "value": "postgresql://${local.database_username}:${local.database_password}@${aws_db_instance.ageoverflow_database.address}:${aws_db_instance.ageoverflow_database.port}/${aws_db_instance.ageoverflow_database.db_name}"
        },
        { "name": "CELERY_BROKER_URL", "value": "sqs://" }
      ],
      "command": ["sh", "-c", "${local.celery_cmd} eng-non-urgent"],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ageoverflow/worker-non-urgent",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs",
          "awslogs-create-group": "true"
        }
      }
    }
  ]
  DEFINITION
}

resource "aws_ecs_service" "ageoverflow_worker_non_urgent" {
  name            = "ageoverflow_worker_non_urgent"
  cluster         = aws_ecs_cluster.ageoverflow.id
  task_definition = aws_ecs_task_definition.ageoverflow_worker_non_urgent.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = data.aws_subnets.private.ids
    security_groups  = [aws_security_group.ageoverflow_worker__non_urgent_sg.id]
    assign_public_ip = true
  }

  depends_on = [aws_lb.ageoverflow, aws_db_instance.ageoverflow_database]
}

resource "aws_security_group" "ageoverflow_worker__non_urgent_sg" {
  name        = "ageoverflow_worker__non_urgent_sg"
  description = "AgeOverflow worker__non_urgent Security Group"

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "ageoverflow_worker__non_urgent_security_group"
  }
}