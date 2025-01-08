# Scrapy settings for confluence project
#
# For simplicity, this file contains only settings considered important or
# commonly used. You can find more settings consulting the documentation:
#
#     https://docs.scrapy.org/en/latest/topics/settings.html
#     https://docs.scrapy.org/en/latest/topics/downloader-middleware.html
#     https://docs.scrapy.org/en/latest/topics/spider-middleware.html

BOT_NAME = 'confluence'

SPIDER_MODULES = ['confluence.spiders']
NEWSPIDER_MODULE = 'confluence.spiders'

# Crawl responsibly by identifying yourself (and your website) on the user-agent
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

# Obey robots.txt rules
ROBOTSTXT_OBEY = False

# Configure maximum concurrent requests performing at the same time to the same domain
CONCURRENT_REQUESTS = 8
CONCURRENT_REQUESTS_PER_DOMAIN = 8

# Configure a delay for requests for the same website (default: 0)
DOWNLOAD_DELAY = 1

# Enable or disable downloader middlewares
# See https://docs.scrapy.org/en/latest/topics/downloader-middleware.html
DOWNLOADER_MIDDLEWARES = {
   'scrapy.downloadermiddlewares.useragent.UserAgentMiddleware': None,
}

# Configure item pipelines
# See https://docs.scrapy.org/en/latest/topics/item-pipeline.html
ITEM_PIPELINES = {
   'confluence.pipelines.ConfluencePipeline': 300,
}

# 日志配置
LOG_LEVEL = 'INFO'
LOG_FILE = 'update_confluence.log'
LOG_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
LOG_ENABLED = True

# 启用Cookie
COOKIES_ENABLED = True
COOKIES_DEBUG = True

# 重试设置
RETRY_ENABLED = True
RETRY_TIMES = 3
RETRY_HTTP_CODES = [500, 502, 503, 504, 522, 524, 408, 429]

# 下载超时
DOWNLOAD_TIMEOUT = 30


