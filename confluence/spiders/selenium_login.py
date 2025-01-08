import os
import time
import pickle
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import logging

# 配置日志
logger = logging.getLogger('selenium_login')

def get_cookies(url, username, password, max_retries=3):
    """获取登录后的cookies"""
    try:
        # 设置Chrome选项
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        
        # 初始化WebDriver
        driver = webdriver.Chrome(
            executable_path='/opt/maxkb/chromedriver-linux64/chromedriver',
            options=chrome_options
        )
        
        try:
            # 访问登录页面
            logger.info("正在访问登录页面...")
            driver.get(f"{url}/login.action")
            
            # 等待用户名输入框出现
            username_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "os_username"))
            )
            
            # 输入用户名和密码
            logger.info("正在输入登录信息...")
            username_input.send_keys(username)
            password_input = driver.find_element(By.ID, "os_password")
            password_input.send_keys(password)
            
            # 点击登录按钮
            login_button = driver.find_element(By.ID, "loginButton")
            login_button.click()
            
            # 等待登录完成
            logger.info("等待登录完成...")
            time.sleep(5)
            
            # 获取cookies
            cookies = driver.get_cookies()
            
            if not cookies:
                logger.error("未获取到cookies")
                return False
                
            # 确保目录存在
            os.makedirs(os.path.dirname(os.path.abspath("confluence/cookies.pkl")), exist_ok=True)
            
            # 保存cookies
            with open("confluence/cookies.pkl", "wb") as f:
                pickle.dump(cookies, f)
                
            logger.info(f"成功保存 {len(cookies)} 个cookies")
            return True
            
        except Exception as e:
            logger.error(f"登录过程中发生错误: {str(e)}")
            return False
            
        finally:
            driver.quit()
            
    except Exception as e:
        logger.error(f"初始化WebDriver时发生错误: {str(e)}")
        return False
        
if __name__ == "__main__":
    from confluence.config import CONFLUENCE_CONFIG
    get_cookies(
        CONFLUENCE_CONFIG['url'],
        CONFLUENCE_CONFIG['username'],
        CONFLUENCE_CONFIG['password']
    )
