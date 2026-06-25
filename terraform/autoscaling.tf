resource "aws_appautoscaling_target" "ageoverflow" {
  max_capacity       = 20
  min_capacity       = 1
  resource_id        = "service/ageoverflow/ageoverflow"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"

  depends_on = [aws_ecs_service.ageoverflow]
}

resource "aws_appautoscaling_policy" "ageoverflow" {
  name               = "ageoverflow-cpu"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.ageoverflow.resource_id
  scalable_dimension = aws_appautoscaling_target.ageoverflow.scalable_dimension
  service_namespace  = aws_appautoscaling_target.ageoverflow.service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
    target_value = 40 // if CPU above 40% scale up, if below scale down
  }
}

# Queue's

resource "aws_appautoscaling_target" "worker_urgent" {
  max_capacity       = 20
  min_capacity       = 2
  resource_id        = "service/ageoverflow/ageoverflow_worker_urgent"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"

  depends_on = [aws_ecs_service.ageoverflow_worker_urgent]
}

resource "aws_appautoscaling_policy" "ageoverflow_worker_urgent_sqs" {
  name               = "worker-urgent-sqs"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.worker_urgent.resource_id
  scalable_dimension = aws_appautoscaling_target.worker_urgent.scalable_dimension
  service_namespace  = aws_appautoscaling_target.worker_urgent.service_namespace

  target_tracking_scaling_policy_configuration {
    customized_metric_specification {
      metric_name = "ApproximateNumberOfMessagesVisible"
      namespace   = "AWS/SQS"
      statistic   = "Average"
      dimensions {
        name  = "QueueName"
        value = aws_sqs_queue.eng_urgent_queue.name
      }
    }
    target_value = 3 # Number of jobs in the urgent queue
  }
}

resource "aws_appautoscaling_policy" "ageoverflow_worker_urgent_cpu" {
  name               = "worker-urgent-cpu"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.worker_urgent.resource_id
  scalable_dimension = aws_appautoscaling_target.worker_urgent.scalable_dimension
  service_namespace  = aws_appautoscaling_target.worker_urgent.service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
    target_value = 60
  }
}

resource "aws_appautoscaling_target" "worker_non_urgent" {
  max_capacity       = 20
  min_capacity       = 2
  resource_id        = "service/ageoverflow/ageoverflow_worker_non_urgent"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"

  depends_on = [aws_ecs_service.ageoverflow_worker_non_urgent]
}

resource "aws_appautoscaling_policy" "ageoverflow_worker_non_urgent_sqs" {
  name               = "worker-non-urgent-sqs"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.worker_non_urgent.resource_id
  scalable_dimension = aws_appautoscaling_target.worker_non_urgent.scalable_dimension
  service_namespace  = aws_appautoscaling_target.worker_non_urgent.service_namespace

  target_tracking_scaling_policy_configuration {
    customized_metric_specification {
      metric_name = "ApproximateNumberOfMessagesVisible"
      namespace   = "AWS/SQS"
      statistic   = "Average"
      dimensions {
        name  = "QueueName"
        value = aws_sqs_queue.eng_non_urgent_queue.name
      }
    }
    target_value = 3
  }
}

resource "aws_appautoscaling_policy" "ageoverflow_worker_non_urgent_cpu" {
  name               = "worker-non-urgent-cpu"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.worker_non_urgent.resource_id
  scalable_dimension = aws_appautoscaling_target.worker_non_urgent.scalable_dimension
  service_namespace  = aws_appautoscaling_target.worker_non_urgent.service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
    target_value = 60
  }
}