# ============================================
# DATA SOURCES — recursos já criados pelo repo
# fraud-detector-infra-aws, buscados pelo nome.
# ============================================
#
# Não há remote state nem checkout cruzado de repositórios aqui — apenas uma
# busca por nome via API da AWS (ou LocalStack, se local_override.tf estiver
# ativo). Os nomes seguem exatamente o padrão "${project_name}-recurso-${environment}"
# definido no repo de infra. Se esses valores não baterem entre os dois repos
# (ex: environment diferente), o `terraform plan` falha com "resource not
# found" — é um erro claro, não um comportamento silencioso.
#
# Pré-requisito: rode `terraform apply` no fraud-detector-infra-aws ANTES de
# rodar `terraform apply` aqui. Sem a fila/tabelas/tópico existindo, estes
# data sources não encontram nada.

data "aws_sqs_queue" "transactions" {
  name = "${var.project_name}-transaction-queue-${var.environment}"
}

data "aws_dynamodb_table" "users" {
  name = "${var.project_name}-users-${var.environment}"
}

data "aws_dynamodb_table" "transactions" {
  name = "${var.project_name}-transactions-${var.environment}"
}

data "aws_sns_topic" "fraud_alerts" {
  name = "${var.project_name}-fraud-alerts-${var.environment}"
}
