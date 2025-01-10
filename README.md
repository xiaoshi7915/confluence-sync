# Confluence 文档同步工具

这是一个用于同步 Confluence 文档的自动化工具，支持增量更新和全量更新。

## 功能特点

- 自动登录 Confluence 并维护会话
- 支持全量更新和增量更新两种模式
- 自动处理页面访问权限问题
- 支持断点续传和错误重试
- 提供详细的日志记录
- 支持缓存机制，提高性能
- 邮件通知功能

## 项目结构

```
confluence/
├── confluence/              # 主程序包
│   ├── spiders/            # 爬虫模块
│   │   ├── confluence_spider.py     # 主爬虫
│   │   ├── confluence_page_tree.py  # 页面树爬虫
│   │   ├── full_update.py          # 全量更新
│   │   └── incremental_update.py   # 增量更新
│   ├── utils/              # 工具模块
│   │   ├── selenium_login.py       # 登录工具
│   │   └── email_sender.py         # 邮件发送
│   ├── config.py           # 配置文件
│   ├── items.py           # 数据模型
│   └── pipelines.py       # 数据处理
├── records/               # 记录文件目录
├── logs/                 # 日志目录
├── PDF_document/         # PDF文档存储
├── requirements.txt      # 依赖包列表
├── setup.py             # 安装配置
├── install.sh           # 安装脚本
├── setup_cron.sh        # 定时任务配置
├── full_update.sh       # 全量更新脚本
└── incremental_update.sh # 增量更新脚本
```

## 安装说明

1. 克隆项目并进入目录：
```bash
git clone [项目地址]
cd confluence
```

2. 运行安装脚本：
```bash
chmod +x install.sh
./install.sh
```

3. 配置定时任务：
```bash
chmod +x setup_cron.sh
./setup_cron.sh
```

## 配置说明

1. 在 `confluence/config.py` 中配置：
   - Confluence 服务器地址
   - 登录凭据
   - 数据库连接
   - 邮件通知设置

2. 在 `records/father_page_ids.txt` 中配置需要同步的父页面ID

## 使用说明

### 全量更新

执行全量更新脚本：
```bash
./full_update.sh
```

### 增量更新

执行增量更新脚本：
```bash
./incremental_update.sh
```

### 测试登录

测试登录功能：
```bash
python3 test_login.py
```

## 日志说明

- 主程序日志：`logs/update_confluence.log`
- 增量更新日志：`logs/incremental_update.log`
- 登录测试日志：控制台输出

## 缓存机制

- 页面树缓存：`records/page_tree_cache/`
- 缓存有效期：7天
- cookies缓存：`confluence/cookies.pkl`

## 错误处理

1. 登录失败：
   - 自动重试登录
   - 更新 cookies
   - 记录错误日志

2. 页面访问失败：
   - 自动重试
   - 记录失败页面
   - 跳过无权限页面

3. 网络错误：
   - 自动重试
   - 断点续传
   - 超时处理

## 维护说明

1. 定期检查日志文件大小
2. 清理过期缓存
3. 更新父页面ID列表
4. 检查数据库连接

## 依赖说明

主要依赖包：
- Scrapy 2.6.3
- Selenium 4.15.2
- PyMySQL 1.1.0
- Requests 2.31.0

详细依赖请查看 `requirements.txt`

