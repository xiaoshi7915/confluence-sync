import os
import re
import time
import glob
import logging
import queue
import pickle
import scrapy
import pymysql
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from scrapy import Spider, Request
import json
from urllib.parse import urljoin
import requests

from ..config import CONFLUENCE_CONFIG, DIRS, FILES, DB_CONFIG
from .selenium_login import get_cookies
from ..items import ConfluenceItem

class ConfluenceSpider(Spider):
    name = 'confluence'
    allowed_domains = ['confluence.flamelephant.com']
    base_url = 'https://confluence.flamelephant.com'
    
    custom_settings = {
        'DOWNLOAD_DELAY': 1,
        'CONCURRENT_REQUESTS': 8,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 8,
        'COOKIES_ENABLED': True,
        'COOKIES_DEBUG': True,
        'RETRY_ENABLED': True,
        'RETRY_TIMES': 3,
        'RETRY_HTTP_CODES': [500, 502, 503, 504, 522, 524, 408, 429],
        'DOWNLOAD_TIMEOUT': 30,
        'ROBOTSTXT_OBEY': False,
        'USER_AGENT': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'ITEM_PIPELINES': {
            'confluence.pipelines.ConfluencePipeline': 300,
        },
        'LOG_LEVEL': 'INFO',
        'LOG_FILE': 'update_confluence.log',
        'LOG_FORMAT': '%(asctime)s - %(levelname)s - %(message)s',
        'LOG_ENABLED': True
    }

    def __init__(self, page_ids_file=None, *args, **kwargs):
        """初始化爬虫"""
        super().__init__(*args, **kwargs)
        self.base_url = CONFLUENCE_CONFIG['base_url']
        self.download_dir = DIRS['pdf_dir']
        self.processed_count = 0
        self.start_time = None
        self.last_log_time = None
        self.last_processed_count = 0
        self.failed_pages = []
        self.page_ids = []
        self.items_buffer = []
        self.buffer_size = 10
        self.total_pages = 0
        
        # 设置失败日志文件
        self.failed_log_file = os.path.join(DIRS['records_dir'], 'failed_pages.txt')
        
        # 确保下载目录存在
        os.makedirs(self.download_dir, exist_ok=True)
        
        # 读取页面ID和部门信息
        if page_ids_file and os.path.exists(page_ids_file):
            with open(page_ids_file, 'r', encoding='utf-8') as f:
                for line in f:
                    parts = line.strip().split('\t')
                    if len(parts) >= 3:
                        self.page_ids.append((parts[0], parts[1], parts[2]))
            self.total_pages = len(self.page_ids)
            logging.info(f"从文件读取到 {self.total_pages} 个页面ID")
            
        # 初始化WebDriver
        logging.info("正在初始化Chrome WebDriver...")
        try:
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--disable-software-rasterizer')
            chrome_options.add_argument('--disable-extensions')
            
            # 配置下载设置
            prefs = {
                'download.default_directory': self.download_dir,
                'download.prompt_for_download': False,
                'download.directory_upgrade': True,
                'safebrowsing.enabled': True,
                'profile.default_content_settings.popups': 0,
                'profile.content_settings.exceptions.automatic_downloads.*.setting': 1
            }
            chrome_options.add_experimental_option('prefs', prefs)
            
            self.driver = webdriver.Chrome(
                executable_path='/opt/maxkb/chromedriver-linux64/chromedriver',
                options=chrome_options
            )
            
            # 设置页面加载超时
            self.driver.set_page_load_timeout(30)
            self.driver.implicitly_wait(10)
            
            logging.info("Chrome WebDriver初始化成功")
        except Exception as e:
            logging.error(f"初始化WebDriver失败: {str(e)}")
            raise e

    def start_requests(self):
        """开始请求"""
        try:
            self.start_time = time.time()
            self.last_log_time = self.start_time
            
            # 读取cookies
            cookies_path = os.path.join("confluence", "cookies.pkl")
            logging.info(f"读取cookies文件: {cookies_path}")
            if not os.path.exists(cookies_path):
                logging.error(f"cookies文件不存在: {cookies_path}")
                return
                
            with open(cookies_path, "rb") as f:
                cookies = pickle.load(f)
                logging.info(f"成功读取 {len(cookies)} 个cookies")
            
            # 生成请求
            total_pages = len(self.page_ids)
            for i, (page_id, department, code) in enumerate(self.page_ids, 1):
                logging.info(f"开始处理第 {i}/{total_pages} 个页面 (ID: {page_id})")
                
                # 获取页面详情
                api_url = f"{self.base_url}/rest/api/content/{page_id}?expand=version,body.view,metadata.labels"
                yield scrapy.Request(
                    url=api_url,
                    cookies=cookies,
                    callback=self.parse_page,
                    errback=self.handle_error,
                    meta={
                        'page_id': page_id,
                        'department': department,
                        'code': code,
                        'index': i,
                        'total': total_pages
                    },
                    dont_filter=True
                )
                
        except Exception as e:
            logging.error(f"启动爬虫失败: {str(e)}")

    def parse_page(self, response):
        """处理响应"""
        try:
            page_id = response.meta['page_id']
            department = response.meta['department']
            code = response.meta['code']
            
            logging.info(f"开始处理页面: ID={page_id}, 部门={department}, 代码={code}")
            
            # 解析API响应
            data = json.loads(response.text)
            
            # 提取页面信息
            title = data.get('title', '')
            if not title:
                title = response.css('meta[name="ajs-page-title"]::attr(content)').get() or 'Default Title'
            title = title.strip()
            
            logging.info(f"成功提取页面标题: {title}")
            
            # 提取作者信息
            author = data.get('version', {}).get('by', {}).get('displayName', '')
            if not author:
                author = response.css('table.pageInfoTable tr:nth-of-type(2) td:nth-of-type(2) a::text').get() or 'Unknown Author'
            author = author.strip()
            
            # 使用当前时间作为最后修改时间
            last_modified = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # 提取链接信息
            micro_link = f"{self.base_url}/x/{page_id}"
            url = f"{self.base_url}/pages/viewpage.action?pageId={page_id}"
            
            # 创建Item
            item = ConfluenceItem()
            item['page_id'] = page_id
            item['title'] = title
            item['author'] = author
            item['last_modified'] = last_modified
            item['micro_link'] = micro_link
            item['url'] = url
            item['department'] = department
            item['code'] = code
            item['crawled_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # 获取页面内容以下载PDF
            page_url = f"{self.base_url}/pages/viewpage.action?pageId={page_id}"
            yield scrapy.Request(
                url=page_url,
                cookies=response.request.cookies,
                callback=self.download_pdf,
                meta={
                    'page_id': page_id,
                    'title': title,
                    'department': department,
                    'code': code,
                    'item': item
                },
                dont_filter=True
            )
            
        except Exception as e:
            logging.error(f"处理页面时出错: {str(e)}")
            self.failed_pages.append((page_id, department, code))

    def handle_error(self, failure):
        """处理请求错误"""
        page_id = failure.request.meta.get('page_id', 'unknown')
        department = failure.request.meta.get('department', 'unknown')
        code = failure.request.meta.get('code', 'unknown')
        index = failure.request.meta.get('index', 0)
        total = failure.request.meta.get('total', 0)
        logging.error(f"请求失败: {failure.value}, 页面 {index}/{total} (ID: {page_id})")
        self.failed_pages.append((page_id, department, code))
    
    def closed(self, reason):
        """爬虫关闭时的处理"""
        try:
            # 关闭WebDriver
            if hasattr(self, 'driver'):
                self.driver.quit()
                logging.info("已关闭WebDriver")
            
            # 打印统计信息
            if hasattr(self, 'total_pages') and hasattr(self, 'failed_pages'):
                success_pages = self.total_pages - len(self.failed_pages)
                success_rate = (success_pages / self.total_pages * 100) if self.total_pages > 0 else 0
                
                logging.info(
                    f"\n爬虫完成，原因: {reason}\n"
                    f"总页面数: {self.total_pages}\n"
                    f"成功页面: {success_pages}\n"
                    f"失败页面: {len(self.failed_pages)}\n"
                    f"成功率: {success_rate:.1f}%"
                )
            
        except Exception as e:
            logging.error(f"关闭爬虫时出错: {str(e)}")

    def flush_buffer(self):
        """将缓冲区的数据写入数据库"""
        if not self.items_buffer:
            return
            
        try:
            self.logger.info(f"开始批量写入数据库，数据条数: {len(self.items_buffer)}")
            
            # 连接数据库
            conn = pymysql.connect(
                host=DB_CONFIG['host'],
                user=DB_CONFIG['user'],
                password=DB_CONFIG['password'],
                database=DB_CONFIG['database'],
                port=DB_CONFIG['port'],
                charset=DB_CONFIG['charset']
            )
            
            cursor = conn.cursor()
            
            # 批量插入数据
            sql = """
                INSERT INTO confluence_pages 
                (page_id, title, author, last_modified, micro_link, pdf_link, url, current_time)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                title=VALUES(title),
                author=VALUES(author),
                last_modified=VALUES(last_modified),
                micro_link=VALUES(micro_link),
                pdf_link=VALUES(pdf_link),
                url=VALUES(url),
                current_time=VALUES(current_time)
            """
            
            values = [
                (
                    item['page_id'],
                    item['title'],
                    item['author'],
                    item['last_modified'],
                    item.get('micro_link', ''),
                    item.get('pdf_link', ''),
                    item['url'],
                    item['crawled_time']
                )
                for item in self.items_buffer
            ]
            
            cursor.executemany(sql, values)
            conn.commit()
            
            self.logger.info(f"数据库写入成功: {len(self.items_buffer)} 条数据")
            for item in self.items_buffer:
                self.logger.debug(f"写入数据: page_id={item['page_id']}, title={item['title']}")
            
            # 清空缓冲区
            self.items_buffer = []
            
        except Exception as e:
            self.logger.error(f"数据库写入失败: error={str(e)}")
            self.logger.error("失败的数据:")
            for item in self.items_buffer:
                self.logger.error(f"- page_id={item['page_id']}, title={item['title']}")
        finally:
            if 'conn' in locals():
                conn.close()
                self.logger.info("数据库连接已关闭")

    def log_failed_page(self, page_id, title, department, code, error_msg):
        """记录失败的页面到日志文件"""
        try:
            with open(self.failed_log_file, 'a', encoding='utf-8') as f:
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                f.write(f"{timestamp}\t{page_id}\t{title}\t{department}\t{code}\t{error_msg}\n")
        except Exception as e:
            logging.error(f"写入失败日志出错: {str(e)}")

    def download_pdf(self, response):
        """下载PDF文件"""
        try:
            page_id = response.meta['page_id']
            title = response.meta['title']
            department = response.meta['department']
            code = response.meta['code']
            item = response.meta['item']
            
            # 从页面提取PDF下载链接
            pdf_link_relative = response.css('a[id="action-export-pdf-link"]::attr(href)').get()
            if pdf_link_relative:
                pdf_url = urljoin(response.url, pdf_link_relative)
                logging.info(f"获取到PDF链接: {pdf_url}")
                
                # 检查文件是否已存在
                new_name = f"{title}_{department}_煜象科技_{page_id}.pdf"
                new_name = re.sub(r'[<>:"/\\|?*]', '_', new_name)  # 替换非法字符
                new_path = os.path.join(self.download_dir, new_name)
                
                if os.path.exists(new_path):
                    logging.info(f"PDF文件已存在，跳过下载: {new_path}")
                    item['pdf_link'] = new_path
                else:
                    # 使用requests下载PDF
                    try:
                        cookies = {cookie['name']: cookie['value'] for cookie in response.request.cookies}
                        headers = {
                            'User-Agent': self.driver.execute_script('return navigator.userAgent;')
                        }
                        pdf_response = requests.get(pdf_url, cookies=cookies, headers=headers, stream=True)
                        
                        if pdf_response.status_code == 200:
                            try:
                                with open(new_path, 'wb') as f:
                                    for chunk in pdf_response.iter_content(chunk_size=8192):
                                        if chunk:
                                            f.write(chunk)
                                
                                # 检查文件大小
                                if os.path.getsize(new_path) < 1024:  # 小于1KB可能是错误页面
                                    error_msg = "下载的文件过小，可能不是有效的PDF"
                                    os.remove(new_path)  # 删除无效文件
                                    raise Exception(error_msg)
                                
                                logging.info(f"PDF下载成功: {new_path}")
                                item['pdf_link'] = new_path
                            except Exception as e:
                                error_msg = f"PDF文件写入失败: {str(e)}"
                                self.log_failed_page(page_id, title, department, code, error_msg)
                                self.failed_pages.append((page_id, department, code))
                        else:
                            error_msg = f"HTTP状态码: {pdf_response.status_code}"
                            self.log_failed_page(page_id, title, department, code, error_msg)
                            self.failed_pages.append((page_id, department, code))
                    except Exception as e:
                        error_msg = f"下载失败: {str(e)}"
                        self.log_failed_page(page_id, title, department, code, error_msg)
                        self.failed_pages.append((page_id, department, code))
            else:
                error_msg = "未找到PDF下载链接"
                self.log_failed_page(page_id, title, department, code, error_msg)
                self.failed_pages.append((page_id, department, code))
            
            yield item
                
        except Exception as e:
            error_msg = f"处理出错: {str(e)}"
            self.log_failed_page(page_id, title, department, code, error_msg)
            self.failed_pages.append((page_id, department, code))
            yield item
