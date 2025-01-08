# confluence-sync
Confluence document synchronization tool

# Confluence 文档同步工具

自动同步 Confluence 文档到本地的工具，支持 PDF 格式下载和邮件通知功能。

## 功能特点

- 自动同步 Confluence 文档到本地
- 支持 PDF 格式下载
- 每小时增量更新
- 每天定时发送更新汇总邮件
- 支持多部门文档管理
- 缓存机制，提高性能
- 完善的错误处理和日志记录

## 系统要求

- Python 3.6+
- MySQL 5.7+
- Chrome 浏览器
- Linux 系统（Ubuntu/Debian 或 CentOS/RHEL）

## 快速开始

1. 克隆仓库：
```bash
git clone https://github.com/your-username/confluence-sync.git
cd confluence-sync
```

2. 运行安装脚本：
```bash
chmod +x install.sh
sudo ./install.sh
```

3. 配置：
- 复制并编辑配置文件：
```bash
cp confluence/config.py.example confluence/config.py
vim confluence/config.py
```
- 设置父页面ID：
```bash
vim records/all_father_page_ids.txt
```

4. 测试运行：
```bash
./incremental_update.sh
```

## 目录结构

```
/opt/maxkb/confluence/
├── confluence/            # 主程序目录
│   ├── spiders/          # 爬虫脚本
│   ├── utils/            # 工具函数
│   └── config.py         # 配置文件
├── PDF_document/         # PDF文件保存目录
├── records/             # 记录文件目录
├── logs/               # 日志目录
├── install.sh          # 安装脚本
├── full_update.sh      # 全量更新脚本
└── incremental_update.sh # 增量更新脚本
```

## 配置说明

1. **Confluence 配置**
```python
CONFLUENCE_CONFIG = {
    'url': 'your_confluence_url',
    'username': 'your_username',
    'password': 'your_password'
}
```

2. **数据库配置**
```python
DB_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'database': 'confluence'
}
```

3. **邮件配置**
```python
EMAIL_CONFIG = {
    'smtp_server': 'your_smtp_server',
    'smtp_port': 465
}
```

## 定时任务

- 每小时执行增量更新
- 每天 18:00 发送更新汇总邮件

## 开发说明

1. **添加新功能**
```bash
# 创建新分支
git checkout -b feature/your-feature

# 提交代码
git add .
git commit -m "Add: your feature"
git push origin feature/your-feature
```

2. **代码规范**
- 遵循 PEP 8 规范
- 添加适当的注释
- 保持代码简洁清晰

## 常见问题

1. **安装失败**
- 检查系统依赖
- 查看日志文件

2. **更新失败**
- 确认网络连接
- 检查 Confluence 账号权限
- 查看错误日志

## 贡献指南

1. Fork 本仓库
2. 创建特性分支
3. 提交更改
4. 发起 Pull Request

## 许可证

MIT License

## 联系方式

- 作者：陈小石
- 邮箱：chenxs@flamelephant.com
