variable "aws_region" {
  description = "Região AWS"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Ambiente (dev, prod). Deve bater com o environment usado no repo fraud-detector-infra-aws — é assim que os data sources abaixo encontram os recursos certos."
  type        = string

  validation {
    condition     = contains(["dev", "prod"], var.environment)
    error_message = "Environment deve ser 'dev' ou 'prod'."
  }
}

variable "project_name" {
  description = "Nome do projeto. Deve bater com o project_name usado no repo fraud-detector-infra-aws — usado para montar os nomes dos recursos buscados via data source."
  type        = string
  default     = "fraud-detector"
}

variable "lambda_code_path" {
  description = "Caminho para a raiz do repositório, mantendo o pacote Python no diretório src/."
  type        = string
  default     = ".."
}
