from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str
    REDIS_URL: str
    ADMIN_TOKEN: str

    # MinIO (substitui o S3)
    MINIO_ENDPOINT: str = "http://minio:9000"
    MINIO_ACCESS_KEY: str
    MINIO_SECRET_KEY: str
    S3_BUCKET: str = "cinematix"
    # Prefixo das URLs de pôster/thumb devolvidas ao frontend (rota /arquivos da API).
    FILES_PUBLIC_URL: str = "/api/arquivos/"

    # RabbitMQ (substitui SNS/SQS)
    RABBITMQ_URL: str = "amqp://guest:guest@rabbitmq:5672/"
    RABBITMQ_QUEUE: str = "cinematix-tarefas"

    # DynamoDB continua na AWS
    DYNAMO_TABLE: str = "dspn-projeto-dynamo-logs"
    AWS_REGION: str = "us-east-1"
    DYNAMO_ENDPOINT: Optional[str] = None  # só para testar com DynamoDB Local

    class Config:
        env_file = ".env"


settings = Settings()
