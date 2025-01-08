# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class ConfluenceItem(scrapy.Item):
    # define the fields for your item here like:
    # name = scrapy.Field()
    page_id = scrapy.Field()
    title = scrapy.Field()
    author = scrapy.Field()
    last_modified = scrapy.Field()
    pdf_path = scrapy.Field()
    micro_link = scrapy.Field()
    pdf_link = scrapy.Field()
    url = scrapy.Field()
    crawled_time = scrapy.Field()
    department = scrapy.Field()
    code = scrapy.Field()
