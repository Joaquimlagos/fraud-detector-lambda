"""
Centraliza a leitura de configuração (variáveis de ambiente) da Lambda.
Nenhum outro módulo deve chamar os.environ diretamente — tudo passa por
aqui, para que a origem dos valores fique em um único lugar e seja fácil
de trocar por um valor de teste.
"""
import os


class Config:
    TRANSACTIONS_TABLE: str = os.environ["TRANSACTIONS_TABLE"]
    USERS_TABLE: str = os.environ["USERS_TABLE"]
    SNS_TOPIC_ARN: str = os.environ["SNS_TOPIC_ARN"]
    ENVIRONMENT: str = os.environ.get("ENVIRONMENT", "dev")

    # Regra: horário de madrugada considerado de maior risco.
    SUSPICIOUS_HOUR_START: int = int(os.environ.get("SUSPICIOUS_HOUR_START", "2"))
    SUSPICIOUS_HOUR_END: int = int(os.environ.get("SUSPICIOUS_HOUR_END", "7"))

    # Regra: velocidade de transações (quantidade em uma janela de tempo).
    VELOCITY_WINDOW_MINUTES: int = int(os.environ.get("VELOCITY_WINDOW_MINUTES", "2"))
    VELOCITY_MAX_TRANSACTIONS: int = int(os.environ.get("VELOCITY_MAX_TRANSACTIONS", "3"))
