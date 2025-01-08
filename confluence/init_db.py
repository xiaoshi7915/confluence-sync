import os
import sys
import pymysql
import logging

# 添加项目根目录到 Python 路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from confluence.config import DB_CONFIG

def init_db():
    """初始化数据库表"""
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
        
        cursor = conn.cursor()
        
        # 创建confluence_pages表
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS confluence_pages (
            page_id VARCHAR(50) NOT NULL PRIMARY KEY,
            title VARCHAR(255) NOT NULL,
            author VARCHAR(100),
            last_modified DATETIME,
            micro_link TEXT,
            pdf_link TEXT,
            url TEXT,
            department VARCHAR(100),
            code VARCHAR(50),
            crawled_time DATETIME,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """
        
        cursor.execute(create_table_sql)
        conn.commit()
        print("数据库表初始化成功")
        
    except Exception as e:
        print(f"数据库初始化失败: {str(e)}")
        raise e
        
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    init_db() 