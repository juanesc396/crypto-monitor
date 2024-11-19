import time
import sys
from dateutil import parser
import json

from kafka import KafkaProducer
import news_pb2
import time

import requests
from lxml import html
from urllib.parse import urlparse

import logging

logging.basicConfig(stream=sys.stdout, level=logging.INFO)

class NewsScraper:
    def __init__(self,
                 url,
                 newspaper_name,
                 news_xpath,
                 title_xpath,
                 ep_xpath,
                 release_date_xpath,
                 paragraph_xpath):
        self.url = url
        self.newspaper_name = newspaper_name
        self.url_dom = f'https://{urlparse(url).netloc}'
        self.headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.121 Safari/537.36',
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                        'Accept-Language': 'en-US,en;q=0.5',
                        'Connection': 'keep-alive'}
        self.news_xpath = news_xpath
        self.title_xpath = title_xpath
        self.ep_xpath = ep_xpath
        self.release_date_xpath = release_date_xpath
        self.paragraph_xpath = paragraph_xpath
        self.last_news = []
        self.producer = None
        self.raw_data_topic_name = 'RawNewsTopic'
        self.encoded_data_topic_name = 'EncodedNewsTopic'

    def set_connection(self):
        for _ in range(3):
            try:
                self.producer = KafkaProducer(bootstrap_servers='kafka:9092')
            except Exception:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                msg = 'Error trying to connect to Kafka'
                logging.error(f'{msg}: {exc_type}: {exc_obj} - Line: {exc_tb.tb_lineno}')
                time.sleep(5)
                

    def protobuf_encoding(self, news):
        n = news_pb2.News()
        n.title = news['title']
        n.date = news['date']
        n.newspaper_name = self.newspaper_name
        n.epigraph = news['epigraph']
        n.paragraph = news['paragraph']

        msg = n.SerializeToString()
        return msg

    def scrape_news(self):
        """
        Method to scrape news.
        """
        try:
            r = requests.get(self.url,
                             headers=self.headers)
            tree = html.fromstring(r.content)

            # get only the new links
            links = list(set(tree.xpath(self.news_xpath)))
            new = [n for n in links if n not in self.last_news]
            self.last_news = links

            # getting the data from news
            if len(new) > 0:
                scraped_news = list()
                for n in new:
                    if not n.startswith(('http://', 'https://')):
                        n = self.url_dom+n
                    nr = requests.get(n, headers=self.headers)
                    n_tree = html.fromstring(nr.content)
                    date = (parser.isoparse(n_tree.xpath(self.release_date_xpath)[0])).strftime("%Y-%m-%d %H:%M:%S")
                    scraped_news.append({'title': n_tree.xpath(self.title_xpath)[0],
                                         'date': date,
                                         'epigraph': n_tree.xpath(self.ep_xpath)[0],
                                         'paragraph': ''.join(n_tree.xpath(self.paragraph_xpath))})
                logging.info(f'Scraped {len(new)} news.')

                # sorting data by date
                scraped_news = sorted(scraped_news, key = lambda x: x['date'], reverse = True)

                for item in scraped_news:
                    # sending raw data
                    self.producer.send(self.raw_data_topic_name, value=json.dumps(item).encode('utf-8'))
                    self.producer.flush()
                    # sending encoded data
                    self.producer.send(self.encoded_data_topic_name, value = self.protobuf_encoding(item))
                    self.producer.flush()
                logging.info('News sent to Kafka.')
            else:
                logging.info('There are no new scraped news at the moment.')

        except Exception:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            msg = 'Error trying to scrape news'
            logging.error(f'{msg}: {exc_type}: {exc_obj} - Line: {exc_tb.tb_lineno}')

    def run(self, interval=300):
        if not self.producer:
            logging.critical('Kafka producer has not been initialized.')
            exit()
        else:
            try:
                while True:
                    print("Scraping news...")
                    self.scrape_news()
                    print(f'Waiting {interval / 60} minutes for the new iteration...\n')
                    time.sleep(interval)
            except KeyboardInterrupt:
                logging.info("Stoping the scraper.")


if __name__ == '__main__':
    url = 'https://www.coindesk.com/livewire/'
    news_xpath = '//a[contains(@class, "CardTitleWrapper")]/@href'
    title_xpath = '//h1/text()'
    release_date_xpath = '//meta[@property="article:published_time"]/@content'
    ep_xpath = '//h2/text()'
    paragraph_xpath = '//div[contains(@class, "typography")]//text()'

    scraper = NewsScraper(url = url,
                          newspaper_name = 'CoinDesk',
                          news_xpath=news_xpath,
                          title_xpath=title_xpath,
                          release_date_xpath=release_date_xpath,
                          ep_xpath=ep_xpath,
                          paragraph_xpath=paragraph_xpath)
    scraper.set_connection()
    scraper.run()