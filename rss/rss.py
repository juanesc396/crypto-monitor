import PyRSS2Gen
from flask import Flask, Response
from kafka import KafkaConsumer
import news_pb2
import threading
import datetime
import logging
import sys
import time

logging.basicConfig(stream=sys.stdout, level=logging.INFO)

rss_items = list()
rss_app = Flask(__name__)


def rss_kafka_consumer():
    for _ in range(3):
        try:
            consumer = KafkaConsumer('EncodedNewsTopic', bootstrap_servers='kafka:9092')
            print('consumer on')
            for msg in consumer:
                # Deserialize the Protobuf binary message
                news = news_pb2.News()
                news.ParseFromString(msg.value)

                new_item = PyRSS2Gen.RSSItem(title=news.title,
                                            description=news.epigraph,
                                            guid=PyRSS2Gen.Guid(f"{datetime.datetime.now()}"),
                                            pubDate=news.date)
                rss_items.append(new_item)
                print('news added')

        except Exception:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            msg = 'Error trying to connect to Kafka'
            logging.error(f'{msg}: {exc_type}: {exc_obj} - Line: {exc_tb.tb_lineno}')
            time.sleep(5)


@rss_app.route('/rss')
def build_rss():
    sorted_rss_items = sorted(rss_items, key=lambda item: item.pubDate, reverse=True)
    rss = PyRSS2Gen.RSS2(title='BTC News.',
                         link='https://www.coindesk.com/',
                         description='RSS Feed updated with BTC news.',
                         language='en-US',
                         items=sorted_rss_items[:20])
    return Response(rss.to_xml(encoding='utf-8'), mimetype='application/rss+xml')

if __name__ == '__main__':
    kafka_thread = threading.Thread(target=rss_kafka_consumer)
    kafka_thread.daemon = True
    kafka_thread.start()

    rss_app.run(debug=True,
                use_reloader=False,
                host='0.0.0.0',
                port=5000)