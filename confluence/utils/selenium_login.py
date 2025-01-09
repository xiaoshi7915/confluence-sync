import os
import time
import pickle
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import logging

# 配置日志
logger = logging.getLogger('selenium_login')

def get_cookies(url, username, password, max_retries=3):
    """获取登录后的cookies"""
    retry_count = 0
    while retry_count < max_retries:
        try:
            # 设置Chrome选项
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')  # 设置窗口大小
            chrome_options.add_argument('--start-maximized')  # 最大化窗口
            
            # 初始化WebDriver
            driver = webdriver.Chrome(
                executable_path='/opt/maxkb/chromedriver-linux64/chromedriver',
                options=chrome_options
            )
            
            try:
                # 访问登录页面
                logger.info(f"正在访问登录页面... 第{retry_count + 1}次尝试")
                driver.get(f"{url}/login.action")
                
                # 等待页面加载完成
                WebDriverWait(driver, 20).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
                
                # 尝试多种可能的用户名输入框选择器
                username_selectors = [
                    (By.ID, "os_username"),
                    (By.ID, "username"),
                    (By.NAME, "os_username"),
                    (By.NAME, "username"),
                    (By.CSS_SELECTOR, "input[type='text']")
                ]
                
                username_input = None
                for selector_type, selector_value in username_selectors:
                    try:
                        username_input = WebDriverWait(driver, 5).until(
                            EC.presence_of_element_located((selector_type, selector_value))
                        )
                        logger.info(f"找到用户名输入框: {selector_type}={selector_value}")
                        break
                    except:
                        continue
                
                if not username_input:
                    raise NoSuchElementException("无法找到用户名输入框")
                
                # 清除并输入用户名
                username_input.clear()
                username_input.send_keys(username)
                logger.info("已输入用户名")
                
                # 尝试多种可能的密码输入框选择器
                password_selectors = [
                    (By.ID, "os_password"),
                    (By.ID, "password"),
                    (By.NAME, "os_password"),
                    (By.NAME, "password"),
                    (By.CSS_SELECTOR, "input[type='password']")
                ]
                
                password_input = None
                for selector_type, selector_value in password_selectors:
                    try:
                        password_input = WebDriverWait(driver, 5).until(
                            EC.presence_of_element_located((selector_type, selector_value))
                        )
                        logger.info(f"找到密码输入框: {selector_type}={selector_value}")
                        break
                    except:
                        continue
                
                if not password_input:
                    raise NoSuchElementException("无法找到密码输入框")
                
                # 清除并输入密码
                password_input.clear()
                password_input.send_keys(password)
                logger.info("已输入密码")
                
                # 尝试多种可能的登录按钮选择器
                login_button_selectors = [
                    (By.ID, "loginButton"),
                    (By.NAME, "login"),
                    (By.CSS_SELECTOR, "input[type='submit']"),
                    (By.CSS_SELECTOR, "button[type='submit']")
                ]
                
                login_button = None
                for selector_type, selector_value in login_button_selectors:
                    try:
                        login_button = WebDriverWait(driver, 5).until(
                            EC.element_to_be_clickable((selector_type, selector_value))
                        )
                        logger.info(f"找到登录按钮: {selector_type}={selector_value}")
                        break
                    except:
                        continue
                
                if not login_button:
                    raise NoSuchElementException("无法找到登录按钮")
                
                # 点击登录按钮
                login_button.click()
                logger.info("已点击登录按钮")
                
                # 等待登录完成
                time.sleep(10)  # 增加等待时间
                
                # 验证登录是否成功
                if "/login.action" in driver.current_url:
                    raise Exception("登录失败，仍在登录页面")
                
                # 获取cookies
                cookies = driver.get_cookies()
                
                if not cookies:
                    raise Exception("未获取到cookies")
                    
                # 确保目录存在
                os.makedirs(os.path.dirname(os.path.abspath("confluence/cookies.pkl")), exist_ok=True)
                
                # 保存cookies
                with open("confluence/cookies.pkl", "wb") as f:
                    pickle.dump(cookies, f)
                    
                logger.info(f"成功保存 {len(cookies)} 个cookies")
                return True
                
            except Exception as e:
                logger.error(f"登录过程中发生错误: {str(e)}")
                retry_count += 1
                if retry_count < max_retries:
                    logger.info(f"将在5秒后进行第{retry_count + 1}次重试")
                    time.sleep(5)
                continue
                
            finally:
                driver.quit()
                
        except Exception as e:
            logger.error(f"初始化WebDriver时发生错误: {str(e)}")
            retry_count += 1
            if retry_count < max_retries:
                logger.info(f"将在5秒后进行第{retry_count + 1}次重试")
                time.sleep(5)
            continue
    
    logger.error(f"登录失败，已重试{max_retries}次")
    return False
        
if __name__ == "__main__":
    from confluence.config import CONFLUENCE_CONFIG
    get_cookies(
        CONFLUENCE_CONFIG['base_url'],
        CONFLUENCE_CONFIG['username'],
        CONFLUENCE_CONFIG['password']
    )
