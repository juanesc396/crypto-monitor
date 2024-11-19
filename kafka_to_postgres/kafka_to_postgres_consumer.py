import psycopg2
from kafka import KafkaConsumer
import news_pb2
import os
import sys
import logging
import time

logging.basicConfig(stream=sys.stdout, level=logging.INFO)

postgres_pass = os.environ.get('KAFKA_CONSUMER_PG_PASS')
consumer = ps_conn = None


def kafka_connection():
    for _ in range(3):
        try:
            consumer = KafkaConsumer('EncodedNewsTopic', bootstrap_servers='kafka:9092')
            logging.info('Connected to Kafka.')
            return consumer
        except Exception:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            msg = 'Error trying to connect to Kafka'
            logging.error(f'{msg}: {exc_type}: {exc_obj} - Line: {exc_tb.tb_lineno}')
            time.sleep(5)

def postgres_connection():
    for _ in range(3):
        try:
            conn = psycopg2.connect(database='news',
                                    user='kafkaconsumer',
                                    password=postgres_pass,
                                    host='postgres',
                                    port='5432')
            logging.info('Connected to Postgres.')
            return conn
        except Exception:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            msg = 'Error trying to connect to Postgres'
            logging.error(f'{msg}: {exc_type}: {exc_obj} - Line: {exc_tb.tb_lineno}')
            time.sleep(5)


if __name__ == '__main__':
    kafka_consumer = kafka_connection()
    ps_conn = postgres_connection()
    
    if all([kafka_consumer, ps_conn]):
        cursor = ps_conn.cursor()
        try:
            for msg in kafka_consumer:
                # Deserialize Protobuf binary message
                news = news_pb2.News()
                news.ParseFromString(msg.value)

                table = news.newspaper_name
                cursor.execute(f"""
                    INSERT INTO {table} (Title, Date, Epigraph, Paragraph)
                    VALUES (%s, %s, %s, %s);
                """, (news.title, news.date, news.epigraph, news.paragraph))
                ps_conn.commit()
                logging.info(f'Database updated: New entry added to {table}.')
        except Exception:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                msg = 'Error trying to update Postgres Database'
                logging.error(f'{msg}: {exc_type}: {exc_obj} - Line: {exc_tb.tb_lineno}')