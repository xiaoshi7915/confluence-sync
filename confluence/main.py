import os
import logging
import logging.config
from datetime import datetime, timedelta
from confluence.config import CONFLUENCE_CONFIG, LOGGING_CONFIG
from confluence.utils.selenium_login import get_cookies
from confluence.spiders.confluence_page_tree import ConfluencePageTreeSpider
from confluence.utils.email_sender import send_hourly_update, send_daily_summary

def setup_logging():
    """初始化日志配置"""
    # 确保日志目录存在
    os.makedirs('logs', exist_ok=True)
    
    # 配置日志
    logging.config.dictConfig(LOGGING_CONFIG)
    logger = logging.getLogger(__name__)
    logger.info("日志配置初始化完成")
    return logger

def main(mode='hourly'):
    """主函数"""
    # 初始化日志
    logger = setup_logging()
    logger.info(f"开始运行 {mode} 模式")
    
    try:
        # 获取cookies
        logger.info("获取cookies")
        cookies = get_cookies(
            CONFLUENCE_CONFIG['base_url'],
            CONFLUENCE_CONFIG['username'],
            CONFLUENCE_CONFIG['password']
        )
        
        if not cookies:
            logger.error("获取cookies失败")
            return
            
        # 初始化爬虫
        logger.info("初始化爬虫")
        spider = ConfluencePageTreeSpider(CONFLUENCE_CONFIG['base_url'], cookies)
        
        # 根据模式设置开始时间
        if mode == 'hourly':
            start_time = datetime.now() - timedelta(hours=1)
            logger.info(f"设置开始时间为1小时前: {start_time}")
        else:  # daily
            start_time = datetime.now() - timedelta(days=1)
            logger.info(f"设置开始时间为1天前: {start_time}")
            
        # 获取更新
        logger.info("获取页面更新")
        updates = spider.get_page_updates(start_time)
        
        # 发送邮件
        if mode == 'hourly':
            logger.info("发送每小时更新邮件")
            send_hourly_update(updates)
        else:  # daily
            logger.info("发送每日汇总邮件")
            send_daily_summary(updates)
            
        logger.info("运行完成")
        
    except Exception as e:
        logger.error(f"运行出错: {str(e)}")
        raise

if __name__ == '__main__':
    import sys
    mode = sys.argv[1] if len(sys.argv) > 1 else 'hourly'
    main(mode) 