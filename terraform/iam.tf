# ============================================
# AWS IAM - Role e Policies da Lambda
# ============================================
#
# Migrado do repo fraud-detector-infra-aws. Única mudança de fundo: as
# referências a recursos (aws_dynamodb_table.users.arn, etc.) viraram
# referências a data sources (data.aws_dynamodb_table.users.arn), já que os
# recursos em si continuam vivendo — e sendo criados — no outro repositório.

resource "aws_iam_role" "lambda_role" {
  name = "${var.project_name}-lambda-role-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name    = "${var.project_name}-lambda-role-${var.environment}"
    Service = "iam"
  }
}

resource "aws_iam_policy" "dynamodb_access" {
  name        = "${var.project_name}-dynamodb-${var.environment}"
  description = "Permissões DynamoDB para a Lambda"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:Query"
        ]
        Resource = [
          data.aws_dynamodb_table.users.arn,
          data.aws_dynamodb_table.transactions.arn,
          "${data.aws_dynamodb_table.transactions.arn}/index/*"
        ]
      }
    ]
  })
}

resource "aws_iam_policy" "sqs_access" {
  name        = "${var.project_name}-sqs-${var.environment}"
  description = "Permissões SQS para a Lambda"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes"
        ]
        Resource = data.aws_sqs_queue.transactions.arn
      }
    ]
  })
}

resource "aws_iam_policy" "sns_publish" {
  name        = "${var.project_name}-sns-${var.environment}"
  description = "Permissões SNS para a Lambda"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = "sns:Publish"
        Resource = data.aws_sns_topic.fraud_alerts.arn
      }
    ]
  })
}

resource "aws_iam_policy" "cloudwatch_logs" {
  name        = "${var.project_name}-logs-${var.environment}"
  description = "Permissões CloudWatch Logs para a Lambda"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/lambda/${var.project_name}-fraud-detection-${var.environment}:*"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_dynamodb" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = aws_iam_policy.dynamodb_access.arn
}

resource "aws_iam_role_policy_attachment" "lambda_sqs" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = aws_iam_policy.sqs_access.arn
}

resource "aws_iam_role_policy_attachment" "lambda_sns" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = aws_iam_policy.sns_publish.arn
}

resource "aws_iam_role_policy_attachment" "lambda_logs" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = aws_iam_policy.cloudwatch_logs.arn
}
