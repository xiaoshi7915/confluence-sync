import os
import logging
from datetime import datetime
from confluence.config import DIRS, FILES, DB_CONFIG  # 添加DB_CONFIG导入
from confluence.spiders.full_update import run_spider_with_timeout  # 添加这行导入
import subprocess
import pymysql

def setup_logging():
    """配置日志"""
    logger = logging.getLogger('incremental_update')
    logger.setLevel(logging.INFO)
    
    if logger.handlers:
        logger.handlers.clear()
        
    fh = logging.FileHandler('update_confluence.log', encoding='utf-8')
    fh.setLevel(logging.INFO)
    
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    
    logger.addHandler(fh)
    logger.propagate = False
    
    return logger

def get_page_ids(file_path):
    """从文件读取页面ID"""
    if not os.path.exists(file_path):
        return set()
    with open(file_path, 'r') as f:
        # 只取每行第一列（以制表符分隔）作为页面ID
        return {int(line.split('\t')[0]) for line in f if line.strip()}

def perform_incremental_update():
    """执行增量更新"""
    logger = setup_logging()
    
    try:
        # 获取旧的页面ID列表
        old_ids_file = os.path.join(DIRS['records_dir'], FILES['all_page_ids'])
        if os.path.exists(old_ids_file):
            with open(old_ids_file, 'r', encoding='utf-8') as f:
                # 只取每行第一列（以制表符分隔）作为页面ID
                old_page_ids = {int(line.split('\t')[0]) for line in f if line.strip()}
            logger.info(f"读取到 {len(old_page_ids)} 个旧页面ID")
        else:
            old_page_ids = set()
            logger.info("未找到旧页面ID文件，将进行全量更新")
        
        # 运行页面树爬虫获取最新的页面ID
        logger.info("开始获取最新页面ID")
        if not run_spider_with_timeout('confluence_page_tree', timeout=1800):
            logger.error("获取页面ID失败")
            return
        
        # 获取新的页面ID列表
        new_ids_file = os.path.join(DIRS['records_dir'], FILES['all_page_ids'])
        if not os.path.exists(new_ids_file):
            logger.error("新页面ID文件不存在")
            return
            
        with open(new_ids_file, 'r', encoding='utf-8') as f:
            # 只取每行第一列（以制表符分隔）作为页面ID
            new_page_ids = {int(line.split('\t')[0]) for line in f if line.strip()}
        logger.info(f"获取到 {len(new_page_ids)} 个新页面ID")
        
        # 计算需要更新的页面ID
        pages_to_update = new_page_ids - old_page_ids
        logger.info(f"需要更新 {len(pages_to_update)} 个页面")
        
        if not pages_to_update:
            logger.info("没有新增页面，无需更新")
            return
            
        # 将需要更新的页面ID写入临时文件
        update_ids_file = os.path.join(DIRS['records_dir'], 'update_page_ids.txt')
        with open(update_ids_file, 'w') as f:
            for page_id in sorted(pages_to_update):
                f.write(f"{page_id}\n")
                
        # 运行主爬虫下载新增页面的PDF
        logger.info("开始下载新增页面的PDF")
        success = run_spider_with_timeout(
            'confluence',
            timeout=7200,  # 2小时超时
            page_ids_file=update_ids_file
        )
        
        if not success:
            logger.error("PDF下载失败")
        else:
            logger.info("PDF下载完成")
            
    except Exception as e:
        logger.error(f"增量更新失败: {str(e)}")
        
    finally:
        # 清理临时文件
        update_ids_file = os.path.join(DIRS['records_dir'], 'update_page_ids.txt')
        if os.path.exists(update_ids_file):
            os.remove(update_ids_file)
        
        logger.info("增量更新结束")

def get_daily_updates():
    """获取当天的更新内容"""
    try:
        # 连接数据库
        conn = pymysql.connect(
            host=DB_CONFIG['host'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password'],
            database=DB_CONFIG['database'],
            port=DB_CONFIG['port'],
            charset=DB_CONFIG['charset']
        )
        
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        
        # 查询当天更新的页面
        sql = """
            SELECT page_id, title, author, last_modified, url, department, code
            FROM confluence_pages
            WHERE DATE(last_modified) = CURDATE()
            ORDER BY last_modified DESC
        """
        
        cursor.execute(sql)
        updates = cursor.fetchall()
        
        return updates
        
    except Exception as e:
        logging.error(f"获取每日更新失败: {str(e)}")
        return []
        
    finally:
        if 'conn' in locals():
            conn.close()

def get_hourly_updates():
    """获取最近一小时的更新内容"""
    try:
        # 连接数据库
        conn = pymysql.connect(
            host=DB_CONFIG['host'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password'],
            database=DB_CONFIG['database'],
            port=DB_CONFIG['port'],
            charset=DB_CONFIG['charset']
        )
        
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        
        # 查询最近一小时更新的页面
        sql = """
            SELECT page_id, title, author, last_modified, url, department, code
            FROM confluence_pages
            WHERE last_modified >= DATE_SUB(NOW(), INTERVAL 1 HOUR)
            ORDER BY last_modified DESC
        """
        
        cursor.execute(sql)
        updates = cursor.fetchall()
        
        return updates
        
    except Exception as e:
        logging.error(f"获取每小时更新失败: {str(e)}")
        return []
        
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    perform_incremental_update()