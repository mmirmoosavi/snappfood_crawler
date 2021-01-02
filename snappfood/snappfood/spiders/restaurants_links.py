import scrapy
from scrapy.spiders import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
from ..items import SnappfoodItem
import re
import json


class CityLinkExtractor(LinkExtractor):
    pass


class RestaurantLinkExtractor(LinkExtractor):
    pass


class ExtractLinks(CrawlSpider):
    name = 'restaurant_links'
    allowed_domains = ['snappfood.ir']
    start_urls = ['https://snappfood.ir/']
    # start_urls = ['https://snappfood.ir/restaurant/city/Tehran?services=RESTAURANT&page={}'.format(page) for page in
    #               range(1, 2)]

    rules = (Rule(CityLinkExtractor(restrict_xpaths='//ul[@class="newfooter__citie-list"]')),
             Rule(RestaurantLinkExtractor(restrict_xpaths=('//div[@class="kk-pp-btn"]',)),
                  callback="extract_comment_link"),
             )
    comments_url = 'comment/vendor/'
    restaurant_url = 'menu/new-menu/load?code='

    def extract_restaurant_link(self, response):
        url = response.url
        comment_regex = re.compile('(https?://.*/)menu/(.{6})')
        result = comment_regex.match(url)
        base_url = result.group(1)
        vendor_hash_url = result.group(2)
        vendor_url = '{}{}{}'.format(base_url, self.restaurant_url, vendor_hash_url)
        # yield scrapy.Request(vendor_url, callback=self.extract_restaurant_type, meta=dict(base_url=url))
        DEFAULT_REQUEST_HEADERS = {
            'Referer': url
        }
        yield scrapy.Request(vendor_url, callback=self.extract_restaurant_type, headers=DEFAULT_REQUEST_HEADERS)

    def extract_restaurant_type(self, response):
        # url = response.meta['base_url']
        json_res = json.loads(response.body)
        vendor_info = json_res['param']['vendor']
        vendor_info = dict(
            restaurant_id=vendor_info['id'],
            restaurant_city=vendor_info['city'],
            restaurant_title=vendor_info['title'],
            restaurant_code=vendor_info['vendorCode'],
            restaurant_type=vendor_info['vendorType'],
            restaurant_sub_type=vendor_info['vendorSubType'],
            restaurant_rating=vendor_info['rating'])

        print('********* extract_restaurant_type*************')
        print(response.url)
        print(response.request.headers)
        print('********* extract_restaurant_type*************')
        yield vendor_info
        # comment_url = self.extract_comment_link(url)
        # return scrapy.Request(comment_url, callback=self.count_comments,
        #                      meta=vendor_info)

    def extract_comment_link(self, response):
        url = response.url
        comment_regex = re.compile('(https?://.*/)menu/(.{6})')
        result = comment_regex.match(url)
        base_url = result.group(1)
        vendor_hash_url = result.group(2)
        comment_url = '{}{}{}/0'.format(base_url, self.comments_url, vendor_hash_url)
        # return comment_url
        yield scrapy.Request(comment_url, callback=self.count_comments)

    def count_comments(self, response):
        # vendor_info = response.meta
        json_res = json.loads(response.body)
        comment_base_url = response.url[:-2]
        count = json_res['data']['count']
        for i in range((count // 10) + 1):
            page_url = '{}/{}'.format(comment_base_url, i)
            yield scrapy.Request(page_url, callback=self.crawl_comment)

    def crawl_comment(self, response):
        # vendor_info = response.meta
        json_res = json.loads(response.body)
        data = json_res['data']['comments']
        if data:
            for elem in data:
                # elem.update(vendor_info)
                item = SnappfoodItem(comment=elem)
                yield item
        else:
            return

    def crawl_comment_without_page(self, response):
        comment_base_url = response.url[:-2]
        i = 0
        while True:
            page_url = '{}/{}'.format(comment_base_url, i)
            i += 1
            yield scrapy.Request(page_url, callback=self.crawl_comment)
