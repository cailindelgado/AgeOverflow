resource "aws_lb_target_group" "ageoverflow" {
  name        = "ageoverflow"
  port        = 8080
  protocol    = "HTTP"
  vpc_id      = data.aws_vpc.default.id
  target_type = "ip"

  health_check {
    path                = "/api/v1/health"
    port                = "8080"
    protocol            = "HTTP"
    healthy_threshold   = 2
    unhealthy_threshold = 2
    timeout             = 5
    interval            = 10
  }
}

resource "aws_lb" "ageoverflow" {
  name               = "ageoverflow"
  internal           = false
  load_balancer_type = "application"
  subnets            = data.aws_subnets.private.ids
  security_groups    = [aws_security_group.ageoverflow_lb.id]
}

resource "aws_security_group" "ageoverflow_lb" {
  name        = "ageoverflow_lb"
  description = "AgeOverflow Load Balancer Security Group"

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
    Name = "ageoverflow_lb_security_group"
  }
}

resource "aws_lb_listener" "ageoverflow" {
  load_balancer_arn = aws_lb.ageoverflow.arn
  port              = "80"
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.ageoverflow.arn
  }
}

output "api" {
  value       = "http://${aws_lb.ageoverflow.dns_name}/api/v1"
  description = "DNS name of the AgeOverflow load balancer"
}
