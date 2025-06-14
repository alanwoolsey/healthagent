resource "aws_iam_role" "ecs_task_app_role" {
  name = "ecsTaskAppRole"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Effect = "Allow",
      Principal = {
        Service = "ecs-tasks.amazonaws.com"
      },
      Action = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "ecs_task_app_bedrock_policy" {
  name = "AppCanUseBedrock"
  role = aws_iam_role.ecs_task_app_role.id

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Effect   = "Allow",
      Action   = "bedrock:*",
      Resource = "*"
    }]
  })
}
