# ============================================
# AWS LAMBDA
# ============================================
#
# Diferença principal em relação à versão anterior (que vivia no repo de
# infra): var.lambda_code_path agora é local a ESTE repositório
# (default "../src") — sem mais cruzar pasta de outro repositório clonado
# ao lado. É por isso que essa migração resolve o problema de fragilidade
# do path relativo mencionado antes.

data "archive_file" "lambda_package" {
  type        = "zip"
  source_dir  = var.lambda_code_path
  output_path = "${path.module}/lambda-function.zip"

  excludes = [
    "__pycache__",
    "*.pyc",
    ".pytest_cache",
    "tests",
    "terraform/*"
  ]
}

resource "aws_lambda_function" "fraud_detection" {
  filename         = data.archive_file.lambda_package.output_path
  function_name    = "${var.project_name}-fraud-detection-${var.environment}"
  role             = aws_iam_role.lambda_role.arn
  handler          = "src.main.handler"
  source_code_hash = data.archive_file.lambda_package.output_base64sha256
  runtime          = "python3.11"
  timeout          = 30
  memory_size      = 256

  environment {
    variables = {
      TRANSACTIONS_TABLE = data.aws_dynamodb_table.transactions.name
      USERS_TABLE        = data.aws_dynamodb_table.users.name
      SNS_TOPIC_ARN      = data.aws_sns_topic.fraud_alerts.arn
      SQS_QUEUE_URL      = data.aws_sqs_queue.transactions.url
      ENVIRONMENT        = var.environment
    }
  }

  tags = {
    Name    = "${var.project_name}-fraud-detection-${var.environment}"
    Service = "lambda"
  }
}

resource "aws_lambda_event_source_mapping" "sqs_trigger" {
  event_source_arn        = data.aws_sqs_queue.transactions.arn
  function_name           = aws_lambda_function.fraud_detection.arn
  batch_size              = 5
  enabled                 = true
  function_response_types = ["ReportBatchItemFailures"]
}
