import os
import logging
from datetime import datetime
import subprocess
import signal
from confluence.config import DIRS, FILES, CONFLUENCE_CONFIG
from confluence.spiders.selenium_login import get_cookies
import time

logger = logging.getLogger('full_update')

def run_spider_with_timeout(spider_name, timeout=3600, **kwargs):
    """运行爬虫并设置超时"""
    try:
        # 获取 cookies
        logger.info("获取 cookies")
        cookies = get_cookies(
            CONFLUENCE_CONFIG['base_url'],
            CONFLUENCE_CONFIG['username'],
            CONFLUENCE_CONFIG['password']
        )
        
        if not cookies:
            logger.error("获取 cookies 失败")
            return False
            
        # 构建命令
        scrapy_path = os.path.join(DIRS['venv_dir'], 'bin', 'scrapy')
        cmd = [scrapy_path, 'crawl', spider_name]
        
        # 添加其他参数
        for k, v in kwargs.items():
            cmd.extend(['-a', f'{k}={v}'])
            
        logger.info(f"执行命令: {' '.join(cmd)}")
        
        # 设置环境变量
        env = os.environ.copy()
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        env['PYTHONPATH'] = base_dir
        env['SCRAPY_SETTINGS_MODULE'] = 'confluence.settings'
        
        # 确保工作目录正确
        work_dir = base_dir
        if not os.path.exists(work_dir):
            logger.error(f"工作目录不存在: {work_dir}")
            return False
            
        logger.info(f"使用工作目录: {work_dir}")
        
        # 使用超时运行爬虫，并实时输出日志
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1,
            env=env,
            cwd=work_dir
        )
        
        start_time = time.time()
        last_output_time = start_time
        
        while True:
            # 检查是否超时
            current_time = time.time()
            if current_time - start_time > timeout:
                logger.error(f"爬虫执行超时（{timeout}秒）")
                process.kill()
                return False
            
            # 检查是否长时间没有输出
            if current_time - last_output_time > 300:
                logger.warning("爬虫已经5分钟没有输出，可能已经卡住")
            
            # 实时读取输出
            output = process.stdout.readline()
            if output:
                logger.info(output.strip())
                last_output_time = current_time
                
            # 检查进程是否结束
            if process.poll() is not None:
                break
                
            time.sleep(0.1)
                
        # 获取剩余输出
        remaining_output = process.stdout.read()
        if remaining_output:
            for line in remaining_output.splitlines():
                logger.info(line.strip())
            
        # 检查返回码
        if process.returncode != 0:
            logger.error(f"爬虫执行失败，返回码: {process.returncode}")
            # 对于confluence爬虫，即使有页面失败也继续执行
            if spider_name == 'confluence':
                logger.warning("虽然有页面下载失败，但继续执行")
                return True
            return False
            
        return True
        
    except Exception as e:
        logger.error(f"运行爬虫出错: {str(e)}")
        return False

def perform_full_update():
    """执行全量更新"""
    try:
        # 读取父页面ID
        father_ids_file = os.path.join(DIRS['records_dir'], FILES['father_page_ids'])
        if not os.path.exists(father_ids_file):
            logger.error("父页面ID文件不存在")
            return
            
        with open(father_ids_file, 'r', encoding='utf-8') as f:
            # 只取每行第一列（以制表符分隔）作为父页面ID
            father_ids = {line.split('\t')[0] for line in f if line.strip()}
        logger.info(f"读取到 {len(father_ids)} 个父页面ID")
        
        # 运行页面树爬虫获取所有子页面ID
        logger.info("开始获取所有子页面ID")
        if not run_spider_with_timeout('confluence_page_tree', timeout=1800):
            logger.error("获取页面ID失败")
            return
            
        # 读取所有页面ID（包括父页面和子页面）
        all_ids_file = os.path.join(DIRS['records_dir'], FILES['all_page_ids'])
        if not os.path.exists(all_ids_file):
            logger.error("页面ID文件不存在")
            return
            
        with open(all_ids_file, 'r', encoding='utf-8') as f:
            page_ids = []
            for line in f:
                parts = line.strip().split('\t')
                if len(parts) >= 3:
                    page_ids.append((parts[0], parts[1], parts[2]))
        logger.info(f"总共读取到 {len(page_ids)} 个页面ID")
        
        # 将所有页面ID写入临时文件
        update_ids_file = os.path.join(DIRS['records_dir'], 'update_page_ids.txt')
        with open(update_ids_file, 'w', encoding='utf-8') as f:
            for page_id, department, code in page_ids:
                f.write(f"{page_id}\t{department}\t{code}\n")
                
        # 运行主爬虫下载所有页面的PDF
        logger.info("开始下载所有页面的PDF")
        success = run_spider_with_timeout(
            'confluence',
            timeout=7200,  # 2小时超时
            page_ids_file=update_ids_file
        )
        
        if not success:
            logger.error("PDF下载失败")
            return False
        else:
            logger.info("PDF下载完成")
            return True
            
    except Exception as e:
        logger.error(f"全量更新失败: {str(e)}")
        return False
        
    finally:
        # 清理临时文件
        update_ids_file = os.path.join(DIRS['records_dir'], 'update_page_ids.txt')
        if os.path.exists(update_ids_file):
            os.remove(update_ids_file)
        
        logger.info("全量更新结束")

if __name__ == "__main__":
    perform_full_update() 