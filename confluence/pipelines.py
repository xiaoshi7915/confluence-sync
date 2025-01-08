# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
from itemadapter import ItemAdapter
import logging
import pymysql
from .config import DB_CONFIG


class ConfluencePipeline:
    def __init__(self):
        self.logger = logging.getLogger('confluence_pipeline')
        self.items_buffer = []
        self.buffer_size = 10
        self.conn = None
        self.cursor = None
        
    def open_spider(self, spider):
        """爬虫启动时连接数据库"""
        try:
            self.conn = pymysql.connect(
                host=DB_CONFIG['host'],
                user=DB_CONFIG['user'],
                password=DB_CONFIG['password'],
                database=DB_CONFIG['database'],
                port=DB_CONFIG['port'],
                charset=DB_CONFIG['charset']
            )
            self.cursor = self.conn.cursor()
            self.logger.info("数据库连接成功")
        except Exception as e:
            self.logger.error(f"数据库连接失败: {str(e)}")
            raise e
            
    def close_spider(self, spider):
        """爬虫关闭时关闭数据库连接"""
        try:
            # 处理剩余的items
            if self.items_buffer:
                self.flush_buffer()
                
            if self.cursor:
                self.cursor.close()
            if self.conn:
                self.conn.close()
                self.logger.info("数据库连接已关闭")
        except Exception as e:
            self.logger.error(f"关闭数据库连接失败: {str(e)}")
            
    def process_item(self, item, spider):
        """处理每个item"""
        try:
            # 添加到缓冲区
            self.items_buffer.append(item)
            
            # 当缓冲区达到指定大小时，批量写入数据库
            if len(self.items_buffer) >= self.buffer_size:
                self.flush_buffer()
                
            return item
            
        except Exception as e:
            self.logger.error(f"处理item失败: {str(e)}")
            raise e
            
    def flush_buffer(self):
        """将缓冲区的数据写入数据库"""
        if not self.items_buffer:
            return
            
        try:
            self.logger.info(f"开始批量写入数据库，数据条数: {len(self.items_buffer)}")
            
            # 批量插入数据
            sql = """
                INSERT INTO confluence_pages 
                (page_id, title, author, last_modified, micro_link, pdf_link, url, department, code, crawled_time)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                title=VALUES(title),
                author=VALUES(author),
                last_modified=VALUES(last_modified),
                micro_link=VALUES(micro_link),
                pdf_link=VALUES(pdf_link),
                url=VALUES(url),
                department=VALUES(department),
                code=VALUES(code),
                crawled_time=VALUES(crawled_time)
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
                    item['department'],
                    item['code'],
                    item['crawled_time']
                )
                for item in self.items_buffer
            ]
            
            self.cursor.executemany(sql, values)
            self.conn.commit()
            
            self.logger.info(f"数据库写入成功: {len(self.items_buffer)} 条数据")
            for item in self.items_buffer:
                self.logger.debug(f"写入数据: page_id={item['page_id']}, title={item['title']}, department={item['department']}")
            
            # 清空缓冲区
            self.items_buffer = []
            
        except Exception as e:
            self.logger.error(f"数据库写入失败: error={str(e)}")
            self.logger.error("失败的数据:")
            for item in self.items_buffer:
                self.logger.error(f"- page_id={item['page_id']}, title={item['title']}, department={item['department']}")
            raise e
