resource "aws_sqs_queue" "eng_urgent_queue" {
  name = "eng-urgent"
}

resource "aws_sqs_queue" "eng_non_urgent_queue" {
  name = "eng-non-urgent"
}