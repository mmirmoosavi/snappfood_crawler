import scrapy
from scrapy.spiders import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
from scrapy.link import Link
from ..items import SnappfoodItem
import re
import json

all_rest_num = 0
extract_rest_call = 0
city_dict = {'Tehran': 300,
             'Esfahan': 45,
             'Mashhad': 37
             }


class CityLinkExtractor(LinkExtractor):
    def extract_links(self, response):
        links = super().extract_links(response)
        final_links = []
        max_page = 260
        for link in links:
            base_url = link.url
            for i in range(max_page + 1):
                changed_url = '{}?page={}'.format(base_url, i)
                new_link = Link(changed_url, link.text)
                final_links.append(new_link)
        print('city_pages_count: {}'.format(len(final_links)))
        return final_links


class RestaurantLinkExtractor(LinkExtractor):
    def extract_links(self, response):
        links = super().extract_links(response)
        return links


class ExtractLinks(CrawlSpider):
    name = 'restaurant_links'
    allowed_domains = ['snappfood.ir']
    start_urls = ['https://snappfood.ir/']
    # start_urls = ['https://snappfood.ir/restaurant/city/Tehran?services=RESTAURANT&page={}'.format(page) for page in
    #               range(1, 2)]

    # rules = (
    #     Rule(CityLinkExtractor(restrict_xpaths='//ul[@class="newfooter__citie-list"]'),
    #          callback='extract_restaurants'),)

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

    def parse_start_url(self, response, **kwargs):
        city_extractor = CityLinkExtractor(restrict_xpaths='//ul[@class="newfooter__citie-list"]')
        city_links = city_extractor.extract_links(response)
        for link in city_links:
            yield scrapy.Request(link.url, callback=self.extract_restaurants)

    def extract_restaurants(self, response):
        global all_rest_num, extract_rest_call
        link_extractor = RestaurantLinkExtractor(restrict_xpaths=('//div[@class="kk-pp-btn"]',))
        links = link_extractor.extract_links(response)
        # print('restaurants_number: {}'.format(len(links)))
        all_rest_num += len(links)
        extract_rest_call += 1
        print(all_rest_num, extract_rest_call)
        for link in links:
            yield scrapy.Request(link.url, callback=self.extract_comment_link)

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
            yield

    def crawl_comment_without_page(self, response):
        comment_base_url = response.url[:-2]
        i = 0
        while True:
            page_url = '{}/{}'.format(comment_base_url, i)
            i += 1
            yield scrapy.Request(page_url, callback=self.crawl_comment)
