import scrapy
from scrapy.spiders import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
from ..items import SnappfoodItem
import re
import json


class ExtractLinks(CrawlSpider):
    name = 'restaurant_links'
    allowed_domains = ['snappfood.ir']
    start_urls = ['https://snappfood.ir/restaurant/city/Tehran?services=RESTAURANT&page={}'.format(page) for page in
                  range(1, 260)]
    rules = (
        Rule(LinkExtractor(restrict_xpaths=('//div[@class="kk-pp-btn"]',)),
             callback='parse_links', follow=False),
    )
    comments_url = 'comment/vendor/'

    def parse_links(self, response):
        url = response.url
        comment_regex = re.compile('(https?://.*/)menu/(.{6})')
        result = comment_regex.match(url)
        base_url = result.group(1)
        vendor_hash_url = result.group(2)
        comment_url = '{}{}{}/0'.format(base_url, self.comments_url, vendor_hash_url)
        yield scrapy.Request(comment_url, callback=self.count_comments)

    def count_comments(self, response):
        json_res = json.loads(response.body)
        comment_base_url = response.url[:-2]
        count = json_res['data']['count']
        for i in range(count // 10):
            page_url = '{}/{}'.format(comment_base_url, i)
            yield scrapy.Request(page_url, callback=self.crawl_comment)

    def crawl_comment(self, response):
        json_res = json.loads(response.body)
        data = json_res['data']['comments']
        for elem in data:
            if elem['feeling'] == 'HAPPY':
                item = SnappfoodItem(comment=elem['commentText'], label=1)
            elif elem['feeling'] == 'SAD':
                item = SnappfoodItem(comment=elem['commentText'], label=0)
            else:
                continue
            yield item
