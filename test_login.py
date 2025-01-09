#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import sys
from confluence.utils.selenium_login import get_cookies
from confluence.config import CONFLUENCE_CONFIG

# 配置日志输出到控制台
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)

def test_login():
    """测试登录功能"""
    logger.info("开始测试登录...")
    
    try:
        result = get_cookies(
            CONFLUENCE_CONFIG['base_url'],
            CONFLUENCE_CONFIG['username'],
            CONFLUENCE_CONFIG['password']
        )
        
        if result:
            logger.info("登录测试成功！")
        else:
            logger.error("登录测试失败！")
            
    except Exception as e:
        logger.error(f"测试过程中发生错误: {str(e)}")
        
if __name__ == "__main__":
    test_login() 