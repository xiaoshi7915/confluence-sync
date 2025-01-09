import requests
import pickle
import os
import logging
import scrapy
from ..config import CONFLUENCE_CONFIG, DIRS, FILES
import time
import json
from datetime import datetime, timedelta

def parse_iso_datetime(iso_string):
    """解析ISO格式的时间字符串（兼容Python 3.6）"""
    try:
        # 处理带毫秒的情况
        if '.' in iso_string:
            main_time, ms = iso_string.split('.')
            ms = ms.replace('Z', '').ljust(6, '0')
            return datetime.strptime(f"{main_time}.{ms}", "%Y-%m-%dT%H:%M:%S.%f")
        # 处理不带毫秒的情况
        return datetime.strptime(iso_string.replace('Z', ''), "%Y-%m-%dT%H:%M:%S")
    except Exception:
        # 如果解析失败，返回一个很旧的时间，强制更新缓存
        return datetime(2000, 1, 1)

class ConfluencePageTreeSpider(scrapy.Spider):
    name = 'confluence_page_tree'
    custom_settings = {
        'CONCURRENT_REQUESTS': 4,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 4,
        'DOWNLOAD_DELAY': 1,
        'COOKIES_ENABLED': True,
        'COOKIES_DEBUG': True,
        'RETRY_ENABLED': True,
        'RETRY_TIMES': 3,
        'RETRY_HTTP_CODES': [401, 403, 500, 502, 503, 504, 522, 524, 408, 429],
        'DOWNLOAD_TIMEOUT': 30,
        'ROBOTSTXT_OBEY': False,
        'DEFAULT_REQUEST_HEADERS': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'X-Requested-With': 'XMLHttpRequest',
            'Connection': 'keep-alive',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache'
        },
        'LOG_LEVEL': 'DEBUG',
        'LOG_FILE': os.path.join(DIRS['logs_dir'], 'update_confluence.log'),
        'LOG_FORMAT': '%(asctime)s - %(levelname)s - %(message)s'
    }
    
    def __init__(self, base_url=None, cookies=None, *args, **kwargs):
        """初始化爬虫"""
        super().__init__(*args, **kwargs)
        self.base_url = base_url or CONFLUENCE_CONFIG['base_url']
        self.all_pages = set()
        self.processed_count = 0
        self.start_time = None
        self.last_log_time = None
        self.last_processed_count = 0
        self.last_save_time = time.time()
        # 修改缓存目录到固定位置
        self.cache_dir = os.path.join(DIRS['records_dir'], 'page_tree_cache')
        self.cache = {}
        self.cache_expire_days = 7
        # 加载历史记录和缓存
        self.load_history()
        self.load_cache()
        
    def load_history(self):
        """加载历史页面ID记录"""
        try:
            history_file = os.path.join(DIRS['records_dir'], FILES['all_page_ids'])
            if os.path.exists(history_file):
                with open(history_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        parts = line.strip().split('\t')
                        if len(parts) >= 3:
                            page_id, department, code = parts[:3]
                            self.all_pages.add((page_id, department, code))
                self.logger.info(f"已加载 {len(self.all_pages)} 个历史页面ID记录")
        except Exception as e:
            self.logger.error(f"加载历史记录失败: {str(e)}")
            self.all_pages = set()

    def load_cache(self):
        """加载缓存数据"""
        try:
            if not os.path.exists(self.cache_dir):
                os.makedirs(self.cache_dir)
                return
                
            cache_file = os.path.join(self.cache_dir, 'page_tree_cache.json')
            if os.path.exists(cache_file):
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                    # 检查并清理过期缓存
                    current_time = datetime.now()
                    self.cache = {
                        k: v for k, v in cache_data.items()
                        if parse_iso_datetime(v['timestamp']) + timedelta(days=self.cache_expire_days) > current_time
                    }
                self.logger.info(f"已加载 {len(self.cache)} 条缓存记录")
        except Exception as e:
            self.logger.error(f"加载缓存失败: {str(e)}")
            self.cache = {}
            
    def save_cache(self):
        """保存缓存数据"""
        try:
            cache_file = os.path.join(self.cache_dir, 'page_tree_cache.json')
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
            self.logger.info(f"已保存 {len(self.cache)} 条缓存记录")
        except Exception as e:
            self.logger.error(f"保存缓存失败: {str(e)}")
            
    def get_cache(self, url):
        """获取缓存数据"""
        cache_data = self.cache.get(url)
        if cache_data:
            cache_time = parse_iso_datetime(cache_data['timestamp'])
            if cache_time + timedelta(days=self.cache_expire_days) > datetime.now():
                return cache_data['data']
        return None
        
    def set_cache(self, url, data):
        """设置缓存数据"""
        self.cache[url] = {
            'data': data,
            'timestamp': datetime.now().isoformat()
        }
        # 每100个新缓存保存一次
        if len(self.cache) % 100 == 0:
            self.save_cache()

    def save_progress(self, force=False):
        """实时保存进度"""
        current_time = time.time()
        if force or (current_time - self.last_save_time) >= 60:
            try:
                output_path = os.path.join(DIRS['records_dir'], FILES['all_page_ids'])
                temp_path = output_path + '.tmp'
                
                # 读取现有记录
                existing_pages = set()
                if os.path.exists(output_path):
                    with open(output_path, 'r', encoding='utf-8') as f:
                        for line in f:
                            parts = line.strip().split('\t')
                            if len(parts) >= 3:
                                existing_pages.add(tuple(parts[:3]))
                
                # 合并新旧记录
                all_pages = existing_pages.union(self.all_pages)
                
                # 保存合并后的记录
                with open(temp_path, 'w', encoding='utf-8') as f:
                    unique_pages = sorted(all_pages, key=lambda x: int(x[0]))
                    for page_id, department, code in unique_pages:
                        f.write(f"{page_id}\t{department}\t{code}\n")
                        
                os.replace(temp_path, output_path)
                self.last_save_time = current_time
                self.logger.info(f"已保存进度，当前收集到 {len(all_pages)} 个页面ID")
            except Exception as e:
                self.logger.error(f"保存进度失败: {str(e)}")

    def start_requests(self):
        """开始请求，从父页面ID文件读取起始页面"""
        try:
            self.start_time = time.time()
            self.last_log_time = self.start_time
            
            # 读取cookies
            cookies_path = os.path.join("confluence", "cookies.pkl")
            self.logger.info(f"读取cookies文件: {cookies_path}")
            if not os.path.exists(cookies_path):
                self.logger.error(f"cookies文件不存在: {cookies_path}")
                from ..utils.selenium_login import get_cookies
                if not get_cookies(self.base_url, CONFLUENCE_CONFIG['username'], CONFLUENCE_CONFIG['password']):
                    self.logger.error("获取cookies失败")
                    return
                self.logger.info("成功重新获取cookies")
                
            with open(cookies_path, "rb") as f:
                cookies = pickle.load(f)
                self.logger.info(f"成功读取 {len(cookies)} 个cookies")
            
            # 读取父页面ID文件
            father_ids_path = os.path.join(DIRS['records_dir'], FILES['father_page_ids'])
            self.logger.info(f"读取父页面ID文件: {father_ids_path}")
            if not os.path.exists(father_ids_path):
                self.logger.error(f"父页面ID文件不存在: {father_ids_path}")
                return
            
            # 读取并处理父页面信息
            parent_pages = []
            with open(father_ids_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    parts = line.split()  # 使用空格分割
                    if len(parts) >= 3:
                        parent_id, department, code = parts[:3]
                        parent_pages.append((parent_id, department, code))
                    else:
                        self.logger.error(f"无效的行格式: {line}")
            
            self.total_parent_pages = len(parent_pages)
            self.logger.info(f"读取到 {self.total_parent_pages} 个父页面")
            
            if not parent_pages:
                self.logger.error("没有读取到任何父页面ID，请检查文件格式")
                return
                
            # 生成请求
            for i, (parent_id, department, code) in enumerate(parent_pages, 1):
                self.logger.info(f"处理父页面 {i}/{self.total_parent_pages} (ID: {parent_id})")
                # 修改API URL格式
                api_url = f"{self.base_url}/rest/api/content/{parent_id}/child/page?expand=version,space,body.view,metadata.labels"
                
                # 保存父页面信息
                self.all_pages.add((parent_id, department, code))
                self.save_progress(force=True)
                
                # 添加更多的请求头
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'application/json, text/javascript, */*; q=0.01',
                    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                    'X-Requested-With': 'XMLHttpRequest',
                    'Referer': f"{self.base_url}/pages/viewpage.action?pageId={parent_id}"
                }
                
                yield scrapy.Request(
                    url=api_url,
                    headers=headers,
                    cookies=cookies,
                    callback=self.parse,
                    errback=self.handle_error,
                    meta={
                        'parent_id': parent_id,
                        'department': department,
                        'code': code,
                        'depth': 0,
                        'parent_index': i
                    },
                    dont_filter=True
                )
                
        except Exception as e:
            self.logger.error(f"启动爬虫失败: {str(e)}")

    def parse(self, response):
        try:
            self.logger.info(f"正在处理URL: {response.url}")
            self.logger.info(f"响应头: {response.headers}")
            
            if response.status != 200:
                self.logger.error(f"请求失败，状态码: {response.status}, URL: {response.url}")
                self.logger.error(f"响应内容: {response.text[:500]}")  # 只显示前500个字符
                # 如果是认证相关错误，尝试重新获取cookie
                if response.status in [401, 403]:
                    self.logger.error(f"认证失败，尝试重新获取cookies")
                    try:
                        from ..utils.selenium_login import get_cookies
                        if get_cookies(self.base_url, CONFLUENCE_CONFIG['username'], CONFLUENCE_CONFIG['password']):
                            self.logger.info("成功重新获取cookies")
                            # 重新读取cookies
                            cookies_path = os.path.join("confluence", "cookies.pkl")
                            with open(cookies_path, "rb") as f:
                                cookies = pickle.load(f)
                            # 重新发送请求
                            yield scrapy.Request(
                                url=response.url,
                                cookies=cookies,
                                callback=self.parse,
                                meta=response.meta,
                                dont_filter=True
                            )
                    except Exception as e:
                        self.logger.error(f"重新获取cookies失败: {str(e)}")
                return

            # 检查缓存
            cached_data = self.get_cache(response.url)
            if cached_data:
                self.logger.debug(f"使用缓存数据: {response.url}")
                data = cached_data
            else:
                data = json.loads(response.text)
                # 保存到缓存
                self.set_cache(response.url, data)

            results = data.get('results', [])
            parent_id = response.meta['parent_id']
            department = response.meta['department']
            code = response.meta['code']
            depth = response.meta.get('depth', 0)
            parent_index = response.meta.get('parent_index', 0)
            
            # 处理子页面
            child_count = len(results)
            if child_count > 0:
                self.logger.info(f"父页面 {parent_index}/{self.total_parent_pages} (ID: {parent_id}) 在深度 {depth} 发现 {child_count} 个子页面")
            
            for result in results:
                page_id = str(result['id'])
                self.all_pages.add((page_id, department, code))
                
                # 检查是否已经处理过这个页面
                if (page_id, department, code) in self.all_pages:
                    continue
                    
                if depth < 5:
                    api_url = f"{self.base_url}/rest/api/content/{page_id}/child/page"
                    # 检查缓存
                    cached_data = self.get_cache(api_url)
                    if cached_data:
                        # 如果有缓存，直接处理缓存数据
                        yield from self.process_cached_data(cached_data, page_id, department, code, depth, parent_index)
                    else:
                        # 如果没有缓存，发起请求
                        yield scrapy.Request(
                            url=api_url,
                            cookies=response.request.cookies,
                            callback=self.parse,
                            meta={
                                'parent_id': page_id,
                                'department': department,
                                'code': code,
                                'depth': depth + 1,
                                'parent_index': parent_index
                            },
                            dont_filter=True,
                            errback=self.handle_error
                        )
            
            # 更新处理计数并保存进度
            self.processed_count += 1
            self.save_progress()
            
            # 每处理10个页面打印一次日志
            if self.processed_count % 10 == 0:
                current_time = time.time()
                time_elapsed = current_time - self.last_log_time
                pages_since_last_log = self.processed_count - self.last_processed_count
                pages_per_second = pages_since_last_log / time_elapsed if time_elapsed > 0 else 0
                
                self.logger.info(
                    f"已处理 {self.processed_count} 个页面，"
                    f"当前收集到 {len(self.all_pages)} 个唯一页面ID，"
                    f"处理速度: {pages_per_second:.2f} 页/秒"
                )
                
                self.last_log_time = current_time
                self.last_processed_count = self.processed_count
                
        except json.JSONDecodeError:
            self.logger.error(f"解析响应失败: {response.text[:200]}")
        except Exception as e:
            self.logger.error(f"处理页面时出错: {str(e)}")
            
    def process_cached_data(self, data, parent_id, department, code, depth, parent_index):
        """处理缓存数据"""
        try:
            # 读取cookies
            cookies_path = os.path.join("confluence", "cookies.pkl")
            if not os.path.exists(cookies_path):
                self.logger.error("cookies文件不存在，尝试重新获取")
                from ..utils.selenium_login import get_cookies
                if not get_cookies(self.base_url, CONFLUENCE_CONFIG['username'], CONFLUENCE_CONFIG['password']):
                    self.logger.error("获取cookies失败")
                    return []
                self.logger.info("成功重新获取cookies")
                
            with open(cookies_path, "rb") as f:
                cookies_list = pickle.load(f)
                cookies = {cookie['name']: cookie['value'] for cookie in cookies_list}
            
            # 添加必要的请求头
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Cache-Control': 'max-age=0',
                'Sec-Fetch-Site': 'same-origin',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-User': '?1',
                'Sec-Fetch-Dest': 'document',
                'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"'
            }
            
            # 先访问父页面
            view_url = f"{self.base_url}/pages/viewpage.action?pageId={parent_id}"
            try:
                response = requests.get(view_url, cookies=cookies, headers=headers, timeout=10, allow_redirects=False)
                if response.status_code == 302:
                    location = response.headers.get('Location', '')
                    if 'login' in location:
                        self.logger.error("会话已过期，尝试重新获取cookies")
                        if get_cookies(self.base_url, CONFLUENCE_CONFIG['username'], CONFLUENCE_CONFIG['password']):
                            self.logger.info("成功重新获取cookies")
                            with open(cookies_path, "rb") as f:
                                cookies_list = pickle.load(f)
                                cookies = {cookie['name']: cookie['value'] for cookie in cookies_list}
                            response = requests.get(view_url, cookies=cookies, headers=headers, timeout=10)
                    else:
                        self.logger.error(f"重定向到未知页面: {location}")
                        return []
                elif response.status_code == 404:
                    self.logger.warning(
                        f"页面不存在或无访问权限: 父页面 {parent_index}/{self.total_parent_pages} "
                        f"(ID: {parent_id})，深度: {depth}，部门: {department}，代码: {code}"
                    )
                    if (parent_id, department, code) in self.all_pages:
                        self.all_pages.remove((parent_id, department, code))
                    return []
                elif response.status_code != 200:
                    self.logger.error(f"访问页面时出现未知错误: {response.status_code}")
                    return []
                
                # 获取子页面列表
                children_url = f"{self.base_url}/plugins/pagetree/naturalchildren.action?decorator=none&excerpt=false&sort=position&reverse=false&disableLinks=false&expandCurrent=true&hasRoot=true&pageId={parent_id}&treeId=0&startDepth=0"
                headers.update({
                    'Accept': '*/*',
                    'X-Requested-With': 'XMLHttpRequest',
                    'Referer': view_url
                })
                
                try:
                    response = requests.get(children_url, cookies=cookies, headers=headers, timeout=10)
                    if response.status_code != 200:
                        self.logger.error(f"获取子页面列表失败: {response.status_code}")
                        return []
                        
                    # 解析HTML获取子页面ID
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(response.text, 'html.parser')
                    child_links = soup.select('a[href*="pageId="]')
                    child_ids = []
                    for link in child_links:
                        href = link.get('href', '')
                        if 'pageId=' in href:
                            page_id = href.split('pageId=')[-1].split('&')[0]
                            child_ids.append(page_id)
                            
                    # 处理每个子页面
                    for page_id in child_ids:
                        self.all_pages.add((page_id, department, code))
                        
                        if depth < 5:
                            # 递归处理子页面
                            child_url = f"{self.base_url}/plugins/pagetree/naturalchildren.action?decorator=none&excerpt=false&sort=position&reverse=false&disableLinks=false&expandCurrent=true&hasRoot=true&pageId={page_id}&treeId=0&startDepth=0"
                            cached_data = self.get_cache(child_url)
                            if cached_data:
                                yield from self.process_cached_data(cached_data, page_id, department, code, depth + 1, parent_index)
                            else:
                                yield scrapy.Request(
                                    url=child_url,
                                    cookies=cookies,
                                    headers=headers,
                                    callback=self.parse,
                                    meta={
                                        'parent_id': page_id,
                                        'department': department,
                                        'code': code,
                                        'depth': depth + 1,
                                        'parent_index': parent_index
                                    },
                                    dont_filter=True,
                                    errback=self.handle_error
                                )
                            
                except Exception as e:
                    self.logger.error(f"获取子页面列表时出错: {str(e)}")
                    return []
                    
            except Exception as e:
                self.logger.error(f"访问页面时出错: {str(e)}")
                return []
                
        except Exception as e:
            self.logger.error(f"处理缓存数据时出错: {str(e)}")
            return []
    
    def handle_error(self, failure):
        """处理请求错误"""
        parent_index = failure.request.meta.get('parent_index', 0)
        parent_id = failure.request.meta.get('parent_id', 'unknown')
        depth = failure.request.meta.get('depth', 0)
        department = failure.request.meta.get('department', '')
        code = failure.request.meta.get('code', '')
        
        # 获取完整的URL
        url = failure.request.url
        
        # 如果是404错误，记录并继续
        if hasattr(failure.value, 'response') and failure.value.response.status == 404:
            self.logger.warning(
                f"页面不存在或无访问权限: 父页面 {parent_index}/{self.total_parent_pages} "
                f"(ID: {parent_id})，深度: {depth}，部门: {department}，代码: {code}"
            )
            # 从 all_pages 中移除这个页面
            if (parent_id, department, code) in self.all_pages:
                self.all_pages.remove((parent_id, department, code))
            return
        
        # 如果是认证相关错误，尝试重新获取cookie
        if hasattr(failure.value, 'response') and failure.value.response.status in [401, 403]:
            self.logger.error(f"认证失败，尝试重新获取cookies")
            try:
                from ..utils.selenium_login import get_cookies
                if get_cookies(self.base_url, CONFLUENCE_CONFIG['username'], CONFLUENCE_CONFIG['password']):
                    self.logger.info("成功重新获取cookies")
                    # 重新读取cookies
                    cookies_path = os.path.join("confluence", "cookies.pkl")
                    with open(cookies_path, "rb") as f:
                        cookies = pickle.load(f)
                    # 重新发送请求
                    return failure.request.replace(cookies=cookies)
            except Exception as e:
                self.logger.error(f"重新获取cookies失败: {str(e)}")
        
        error_msg = (
            f"请求失败: {failure.value}, "
            f"状态码: {failure.value.response.status if hasattr(failure.value, 'response') else 'unknown'}, "
            f"父页面 {parent_index}/{self.total_parent_pages} (ID: {parent_id})，深度: {depth}, "
            f"URL: {url}"
        )
        
        self.logger.error(error_msg)
    
    def closed(self, reason):
        """爬虫关闭时的处理"""
        try:
            self.save_progress(force=True)
            self.save_cache()
            
            total_time = time.time() - self.start_time
            hours = int(total_time // 3600)
            minutes = int((total_time % 3600) // 60)
            seconds = int(total_time % 60)
            
            self.logger.info(
                f"爬虫完成，原因: {reason}\n"
                f"总运行时间: {hours:02d}:{minutes:02d}:{seconds:02d}\n"
                f"处理页面数: {self.processed_count}\n"
                f"唯一页面数: {len(self.all_pages)}\n"
                f"缓存数量: {len(self.cache)}\n"
                f"平均处理速度: {self.processed_count/total_time:.2f} 页/秒"
            )
        except Exception as e:
            self.logger.error(f"关闭爬虫时出错: {str(e)}")

    def get_page_info(self, page_id):
        """获取页面信息"""
        try:
            self.logger.info(f"获取页面信息: {page_id}")
            api_url = f"{self.base_url}/rest/api/content/{page_id}?expand=version,space,body.view,metadata.labels"
            self.logger.debug(f"API URL: {api_url}")
            
            response = self.session.get(api_url)
            if response.status_code == 200:
                data = response.json()
                self.logger.info(f"成功获取页面信息: {data.get('title', 'Unknown Title')}")
                return data
            else:
                self.logger.error(f"获取页面信息失败: HTTP {response.status_code}")
                self.logger.error(f"响应内容: {response.text}")
                return None
        except Exception as e:
            self.logger.error(f"获取页面信息异常: {str(e)}")
            return None
            
    def get_child_pages(self, parent_id):
        """获取子页面列表"""
        try:
            self.logger.info(f"获取子页面列表: {parent_id}")
            api_url = f"{self.base_url}/rest/api/content/{parent_id}/child/page?expand=version"
            self.logger.debug(f"API URL: {api_url}")
            
            response = self.session.get(api_url)
            if response.status_code == 200:
                data = response.json()
                results = data.get('results', [])
                self.logger.info(f"找到 {len(results)} 个子页面")
                return results
            else:
                self.logger.error(f"获取子页面列表失败: HTTP {response.status_code}")
                self.logger.error(f"响应内容: {response.text}")
                return []
        except Exception as e:
            self.logger.error(f"获取子页面列表异常: {str(e)}")
            return []
            
    def get_all_pages(self, parent_ids):
        """获取所有页面信息"""
        all_pages = []
        visited = set()
        
        def traverse(page_id):
            if page_id in visited:
                self.logger.debug(f"页面已访问过: {page_id}")
                return
                
            visited.add(page_id)
            self.logger.info(f"遍历页面: {page_id}")
            
            # 获取页面信息
            page_info = self.get_page_info(page_id)
            if page_info:
                all_pages.append(page_info)
                
                # 获取子页面
                child_pages = self.get_child_pages(page_id)
                for child in child_pages:
                    child_id = child['id']
                    traverse(child_id)
            else:
                self.logger.warning(f"无法获取页面信息: {page_id}")
                
        # 遍历所有父页面
        for parent_id in parent_ids:
            self.logger.info(f"开始遍历父页面: {parent_id}")
            traverse(parent_id)
            
        self.logger.info(f"总共获取到 {len(all_pages)} 个页面")
        return all_pages
        
    def get_page_updates(self, start_time=None):
        """获取页面更新信息"""
        try:
            self.logger.info("获取页面更新信息")
            if start_time:
                self.logger.info(f"开始时间: {start_time}")
            
            # 读取父页面ID
            with open('records/all_father_page_ids.txt', 'r') as f:
                parent_ids = [line.strip() for line in f if line.strip()]
            self.logger.info(f"读取到 {len(parent_ids)} 个父页面ID")
            
            # 获取所有页面
            all_pages = self.get_all_pages(parent_ids)
            
            # 过滤更新的页面
            updates = []
            for page in all_pages:
                try:
                    last_modified = datetime.fromisoformat(
                        page['version']['when'].replace('Z', '+00:00'))
                    
                    if not start_time or last_modified > start_time:
                        update = {
                            'id': page['id'],
                            'title': page['title'],
                            'url': f"{self.base_url}/pages/viewpage.action?pageId={page['id']}",
                            'space': page['space']['name'],
                            'author': page['version']['by']['displayName'],
                            'last_modified': last_modified.strftime('%Y-%m-%d %H:%M:%S'),
                            'department': next((label['name'] for label in 
                                page['metadata']['labels']['results']
                                if label['name'].startswith('部门/')), '未知')
                        }
                        updates.append(update)
                        self.logger.info(f"找到更新: {update['title']}")
                except Exception as e:
                    self.logger.error(f"处理页面更新信息异常: {str(e)}")
                    continue
                    
            self.logger.info(f"总共找到 {len(updates)} 个更新")
            return updates
        except Exception as e:
            self.logger.error(f"获取页面更新信息异常: {str(e)}")
            return []






