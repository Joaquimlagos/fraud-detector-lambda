output "lambda_function_name" {
  description = "Nome da função Lambda"
  value       = aws_lambda_function.fraud_detection.function_name
}

output "lambda_function_arn" {
  description = "ARN da função Lambda"
  value       = aws_lambda_function.fraud_detection.arn
}

output "lambda_role_arn" {
  description = "ARN da IAM role da Lambda"
  value       = aws_iam_role.lambda_role.arn
}

output "analysis_lambda_function_name" {
  description = "Nome da Lambda de análise RAG"
  value       = aws_lambda_function.analysis.function_name
}

output "analysis_lambda_function_arn" {
  description = "ARN da Lambda de análise RAG"
  value       = aws_lambda_function.analysis.arn
}
