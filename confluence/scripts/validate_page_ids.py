import os
import requests
import logging
from ..config import CONFLUENCE_CONFIG, DIRS, FILES
from ..utils.selenium_login import get_cookies
import pickle
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

def setup_logging():
    """配置日志"""
    logger = logging.getLogger('validate_page_ids')
    logger.setLevel(logging.INFO)
    
    if logger.handlers:
        logger.handlers.clear()
        
    log_file = os.path.join(DIRS['logs_dir'], 'validate_page_ids.log')
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    
    fh = logging.FileHandler(log_file, encoding='utf-8')
    fh.setLevel(logging.INFO)
    
    formatter = logging.Formatter('[%(asctime)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    fh.setFormatter(formatter)
    
    logger.addHandler(fh)
    logger.propagate = False
    
    return logger

def setup_driver():
    """设置Chrome驱动"""
    logger = logging.getLogger('validate_page_ids')
    try:
        logger.info("开始设置Chrome驱动...")
        chrome_options = Options()
        chrome_options.add_argument('--headless')  # 无界面模式
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--disable-infobars')
        
        logger.info(f"Chrome驱动路径: {DIRS['driver_path']}")
        driver = webdriver.Chrome(
            executable_path=DIRS['driver_path'],
            options=chrome_options
        )
        logger.info("Chrome驱动设置成功")
        return driver
    except Exception as e:
        logger.error(f"设置Chrome驱动时出错: {str(e)}")
        raise

def validate_page_with_selenium(driver, page_id, base_url):
    """使用Selenium验证页面是否可访问"""
    logger = logging.getLogger('validate_page_ids')
    url = f"{base_url}/pages/viewpage.action?pageId={page_id}"
    
    try:
        # 设置页面加载超时
        driver.set_page_load_timeout(20)
        
        logger.info(f"开始访问页面: {url}")
        try:
            driver.get(url)
        except:
            logger.error(f"页面加载超时: {page_id}")
            return False
            
        time.sleep(1)  # 等待页面加载
        
        # 获取当前URL和页面标题
        try:
            current_url = driver.current_url
            page_title = driver.title
            logger.info(f"当前URL: {current_url}")
            logger.info(f"页面标题: {page_title}")
        except:
            logger.error(f"无法获取页面信息: {page_id}")
            return False
        
        # 检查是否需要登录
        if "login.action" in current_url:
            logger.info(f"页面 {page_id} 需要登录，尝试登录...")
            try:
                # 等待用户名输入框出现
                username_input = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.ID, "os_username"))
                )
                logger.info("找到用户名输入框: id=os_username")
                
                # 等待密码输入框出现
                password_input = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.ID, "os_password"))
                )
                logger.info("找到密码输入框: id=os_password")
                
                # 等待登录按钮出现
                login_button = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.ID, "loginButton"))
                )
                logger.info("找到登录按钮: id=loginButton")
                
                # 输入用户名和密码
                username_input.send_keys(CONFLUENCE_CONFIG['username'])
                logger.info("已输入用户名")
                password_input.send_keys(CONFLUENCE_CONFIG['password'])
                logger.info("已输入密码")
                
                # 点击登录按钮
                login_button.click()
                logger.info("已点击登录按钮")
                
                # 等待页面加载
                time.sleep(2)
                
                # 重新访问页面
                logger.info("重新访问页面")
                try:
                    driver.get(url)
                except:
                    logger.error(f"登录后页面加载超时: {page_id}")
                    return False
                    
                time.sleep(1)
                
                # 获取登录后的URL和标题
                current_url = driver.current_url
                page_title = driver.title
                logger.info(f"登录后URL: {current_url}")
                logger.info(f"登录后标题: {page_title}")
                
            except Exception as e:
                logger.error(f"登录过程出错: {str(e)}")
                return False
        
        # 检查页面是否存在和是否有权限访问
        if "login.action" in current_url and "permissionViolation=true" in current_url:
            logger.warning(f"无权限访问页面: {page_id}")
            return "no_permission"
        elif "404" in page_title or "页面未找到" in page_title:
            logger.error(f"页面不存在: {page_id}")
            return False
            
        # 尝试查找页面标题元素，确认页面内容是否正常加载
        try:
            title_element = WebDriverWait(driver, 3).until(
                EC.presence_of_element_located((By.ID, "title-text"))
            )
            logger.info(f"页面有效且有访问权限: {page_id}")
            return True
        except:
            if "permissionViolation=true" in current_url:
                logger.warning(f"无权限访问页面: {page_id}")
                return "no_permission"
            else:
                logger.error(f"页面内容加载失败: {page_id}")
                return False
        
    except Exception as e:
        logger.error(f"验证页面时出错: {str(e)}")
        return False

def validate_page_ids():
    """验证页面ID的有效性"""
    logger = setup_logging()
    driver = None
    
    try:
        # 设置Chrome驱动
        driver = setup_driver()
        
        # 读取父页面ID文件
        father_ids_path = os.path.join(DIRS['records_dir'], FILES['father_page_ids'])
        if not os.path.exists(father_ids_path):
            logger.error("父页面ID文件不存在")
            return False
            
        valid_pages = []
        invalid_pages = []
        no_permission_pages = []
        
        # 读取并验证每个页面ID
        with open(father_ids_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            total_pages = len(lines)
            
            for index, line in enumerate(lines, 1):
                line = line.strip()
                if not line:
                    continue
                    
                parts = line.split()
                if len(parts) >= 3:
                    page_id, department, code = parts[:3]
                    
                    logger.info(f"正在验证第 {index}/{total_pages} 个页面...")
                    
                    # 验证页面是否存在
                    url = f"{CONFLUENCE_CONFIG['base_url']}/pages/viewpage.action?pageId={page_id}"
                    logger.info(f"验证页面: {url}")
                    
                    result = validate_page_with_selenium(driver, page_id, CONFLUENCE_CONFIG['base_url'])
                    if result is True:
                        valid_pages.append(line)
                        logger.info(f"页面有效: {line}")
                    elif result == "no_permission":
                        no_permission_pages.append(line)
                        logger.warning(f"无权限访问: {line}")
                    else:
                        invalid_pages.append(line)
                        logger.warning(f"页面无效: {line}")
                        
                    # 每验证5个页面重启一次浏览器，避免内存泄漏
                    if index % 5 == 0:
                        logger.info("重启浏览器以释放内存...")
                        driver.quit()
                        driver = setup_driver()
                else:
                    logger.error(f"无效的行格式: {line}")
                    
        if valid_pages or no_permission_pages:
            # 备份原文件
            backup_path = father_ids_path + '.bak'
            os.rename(father_ids_path, backup_path)
            logger.info(f"原文件已备份为: {backup_path}")
            
            # 写入有效的页面ID
            with open(father_ids_path, 'w', encoding='utf-8') as f:
                for line in valid_pages:
                    f.write(line + '\n')
            
            # 保存无权限的页面到单独的文件
            no_permission_path = os.path.join(DIRS['records_dir'], 'no_permission_pages.txt')
            with open(no_permission_path, 'w', encoding='utf-8') as f:
                for line in no_permission_pages:
                    f.write(line + '\n')
                    
            logger.info(f"验证完成:")
            logger.info(f"- 有效且有权限的页面: {len(valid_pages)} 个")
            logger.info(f"- 无权限的页面: {len(no_permission_pages)} 个")
            logger.info(f"- 无效的页面: {len(invalid_pages)} 个")
            
            if invalid_pages:
                logger.info("无效的页面:")
                for page in invalid_pages:
                    logger.info(f"  {page}")
                    
            if no_permission_pages:
                logger.info("无权限的页面:")
                for page in no_permission_pages:
                    logger.info(f"  {page}")
        else:
            logger.warning("没有找到任何有效且有权限的页面，保留原文件不变")
                
        return True
        
    except Exception as e:
        logger.error(f"验证页面ID时出错: {str(e)}")
        return False
        
    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass

if __name__ == "__main__":
    validate_page_ids() 