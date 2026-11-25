#!/usr/bin/env python3
"""Consome a fila do RabbitMQ (antes SNS/SQS) e processa tarefas assíncronas:
thumbnails de pôsteres e PDFs de ingressos, gravados no MinIO (antes S3)."""
import json
import os
import time
import uuid
from datetime import datetime, timezone

import boto3
import pika
from botocore.client import Config
from dotenv import load_dotenv

from processors.pdf import gerar_pdf
from processors.thumbnail import gerar_thumbnail

load_dotenv()

S3_BUCKET = os.environ.get('S3_BUCKET', 'cinematix')
DYNAMO_TABLE = os.environ.get('DYNAMO_TABLE', 'dspn-projeto-dynamo-logs')
AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')
RABBITMQ_URL = os.environ.get('RABBITMQ_URL', 'amqp://guest:guest@rabbitmq:5672/')
RABBITMQ_QUEUE = os.environ.get('RABBITMQ_QUEUE', 'cinematix-tarefas')

s3 = boto3.client(
    's3',
    endpoint_url=os.environ.get('MINIO_ENDPOINT', 'http://minio:9000'),
    aws_access_key_id=os.environ['MINIO_ACCESS_KEY'],
    aws_secret_access_key=os.environ['MINIO_SECRET_KEY'],
    region_name=AWS_REGION,
    config=Config(signature_version='s3v4', s3={'addressing_style': 'path'}),
)
# DynamoDB continua na AWS; DYNAMO_ENDPOINT só para testes com DynamoDB Local.
table = boto3.resource('dynamodb', region_name=AWS_REGION,
                       endpoint_url=os.environ.get('DYNAMO_ENDPOINT') or None).Table(DYNAMO_TABLE)


def log_dynamo(acao, entidade, dados):
    table.put_item(Item={
        'id': str(uuid.uuid4()),
        'acao': acao,
        'entidade': entidade,
        'dados': json.dumps(dados, default=str, ensure_ascii=False),
        'timestamp': datetime.now(timezone.utc).isoformat(),
    })


def processar_mensagem(msg):
    action = msg.get('action')

    if action == 'thumbnail':
        original = s3.get_object(Bucket=S3_BUCKET, Key=msg['key'])['Body'].read()
        tamanho_original, tamanho_final = gerar_thumbnail(original)
        s3.put_object(
            Bucket=S3_BUCKET,
            Key=msg['thumb_key'],
            Body=gerar_thumbnail(original, return_bytes=True),
            ContentType='image/jpeg',
        )
        log_dynamo('PROCESS', 'poster', {
            'original': msg['key'],
            'thumbnail': msg['thumb_key'],
            'de': tamanho_original,
            'para': tamanho_final,
        })
        print(f"✓ thumbnail {msg['thumb_key']}", flush=True)

    elif action == 'generate_pdf':
        poster_bytes = None
        poster_key = msg.get('poster_key')
        if poster_key:
            try:
                poster_bytes = s3.get_object(Bucket=S3_BUCKET, Key=poster_key)['Body'].read()
            except Exception as e:
                print(f"⚠ pôster não encontrado: {poster_key} ({e})", flush=True)

        pdf_bytes = gerar_pdf(poster_bytes, msg['linhas'])
        s3.put_object(
            Bucket=S3_BUCKET,
            Key=msg['pdf_key'],
            Body=pdf_bytes,
            ContentType='application/pdf',
            ContentDisposition='attachment; filename="ingresso-cinematix.pdf"',
        )
        log_dynamo('PROCESS', 'ingresso_pdf', {
            'pdf_key': msg['pdf_key'],
            'ingressos_ids': [l['ingresso']['id'] for l in msg['linhas']],
            'tamanho_bytes': len(pdf_bytes),
        })
        print(f"✓ pdf {msg['pdf_key']} ({len(pdf_bytes)} bytes)", flush=True)

    else:
        print(f"⚠ ação desconhecida: {action}", flush=True)


def ao_receber(ch, method, _props, body):
    try:
        processar_mensagem(json.loads(body))
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        # Tenta de novo uma vez (como a SQS devolvendo a mensagem); na 2ª falha descarta.
        print(f"❌ erro processando mensagem: {e}", flush=True)
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=not method.redelivered)


def main():
    while True:
        try:
            conn = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
            ch = conn.channel()
            ch.queue_declare(queue=RABBITMQ_QUEUE, durable=True)
            ch.basic_qos(prefetch_count=1)
            ch.basic_consume(queue=RABBITMQ_QUEUE, on_message_callback=ao_receber)
            print(f"🚀 Worker aguardando mensagens na fila '{RABBITMQ_QUEUE}'", flush=True)
            ch.start_consuming()
        except pika.exceptions.AMQPConnectionError as e:
            print(f"⏳ RabbitMQ indisponível ({e!r}), tentando de novo em 5s", flush=True)
            time.sleep(5)


if __name__ == '__main__':
    main()
