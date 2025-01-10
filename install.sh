#!/bin/bash

# 设置颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 设置工作目录
WORK_DIR="/opt/maxkb/confluence"
VENV_DIR="$WORK_DIR/venv"
LOG_DIR="$WORK_DIR/logs"
RECORDS_DIR="$WORK_DIR/records"
PDF_DIR="$WORK_DIR/PDF_document"
CACHE_DIR="$RECORDS_DIR/page_tree_cache"
DRIVER_DIR="/opt/maxkb/chromedriver-linux64"

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO] $1${NC}"
}

log_warn() {
    echo -e "${YELLOW}[WARN] $1${NC}"
}

log_error() {
    echo -e "${RED}[ERROR] $1${NC}"
}

# 检查系统要求
check_system() {
    log_info "检查系统要求..."
    
    # 检查Python版本
    if ! command -v python3 &> /dev/null; then
        log_error "未找到Python3，请先安装Python3"
        exit 1
    fi
    
    # 检查pip
    if ! command -v pip3 &> /dev/null; then
        log_error "未找到pip3，请先安装pip3"
        exit 1
    fi
    
    # 检查Chrome和ChromeDriver
    if ! command -v google-chrome &> /dev/null; then
        log_warn "未找到Chrome浏览器，正在安装..."
        if command -v yum &> /dev/null; then
            # CentOS/RHEL
            cat << EOF > /etc/yum.repos.d/google-chrome.repo
[google-chrome]
name=google-chrome
baseurl=http://dl.google.com/linux/chrome/rpm/stable/x86_64
enabled=1
gpgcheck=1
gpgkey=https://dl.google.com/linux/linux_signing_key.pub
EOF
            yum install -y google-chrome-stable
        else
            log_error "不支持的系统类型，请手动安装Chrome浏览器"
            exit 1
        fi
    fi
    
    # 检查并安装ChromeDriver
    if [ ! -f "$DRIVER_DIR/chromedriver" ]; then
        log_warn "未找到ChromeDriver，正在安装..."
        mkdir -p "$DRIVER_DIR"
        CHROME_VERSION=$(google-chrome --version | cut -d ' ' -f 3 | cut -d '.' -f 1)
        wget -q "https://edgedl.me.gvt1.com/edgedl/chrome/chrome-for-testing/$CHROME_VERSION.0.6261.94/linux64/chromedriver-linux64.zip" -O /tmp/chromedriver.zip
        unzip -q /tmp/chromedriver.zip -d "$DRIVER_DIR"
        chmod +x "$DRIVER_DIR/chromedriver"
        rm /tmp/chromedriver.zip
    fi
    
    # 检查必要的系统包
    log_info "检查并安装必要的系统包..."
    if command -v yum &> /dev/null; then
        yum groupinstall -y "Development Tools"
        yum install -y python3-devel mysql-devel
    fi
}

# 创建目录结构
create_directories() {
    log_info "创建目录结构..."
    
    # 创建主目录
    mkdir -p "$WORK_DIR"
    
    # 创建子目录
    mkdir -p "$LOG_DIR"
    mkdir -p "$RECORDS_DIR"
    mkdir -p "$PDF_DIR"
    mkdir -p "$CACHE_DIR"
    mkdir -p "$WORK_DIR/confluence"
    
    # 设置权限
    chmod 755 "$WORK_DIR"
    chmod -R 755 "$LOG_DIR"
    chmod -R 755 "$RECORDS_DIR"
    chmod -R 755 "$PDF_DIR"
    chmod -R 755 "$CACHE_DIR"
    
    # 创建必要的空文件
    touch "$RECORDS_DIR/all_father_page_ids.txt"
    touch "$RECORDS_DIR/all_page_ids.txt"
    touch "$RECORDS_DIR/failed_pages.txt"
    touch "$RECORDS_DIR/no_permission_pages.txt"
}

# 设置Python虚拟环境
setup_virtualenv() {
    log_info "设置Python虚拟环境..."
    
    # 创建虚拟环境
    python3 -m venv "$VENV_DIR"
    
    # 激活虚拟环境
    source "$VENV_DIR/bin/activate"
    
    # 升级pip
    pip install --upgrade pip
    
    # 安装依赖
    pip install -r requirements.txt
}

# 设置配置文件
setup_config() {
    log_info "设置配置文件..."
    
    if [ ! -f "$WORK_DIR/confluence/config.py" ]; then
        log_warn "未找到配置文件，创建默认配置..."
        cat > "$WORK_DIR/confluence/config.py" << EOF
import os

# 基础路径配置
BASE_DIR = '/opt/maxkb/confluence'
PDF_DIR = os.path.join(BASE_DIR, 'PDF_document')
RECORDS_DIR = os.path.join(BASE_DIR, 'records')
LOGS_DIR = os.path.join(BASE_DIR, 'logs')

# 创建必要的目录
os.makedirs(RECORDS_DIR, exist_ok=True)
os.makedirs(PDF_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)

# Confluence配置
CONFLUENCE_CONFIG = {
    'base_url': 'https://confluence.flamelephant.com',
    'username': 'your_username',
    'password': 'your_password'
}

# 数据库配置
DB_CONFIG = {
    'host': '47.118.250.53',
    'user': 'maxkb',
    'password': 'admin123456!',
    'database': 'maxkb',
    'port': 3306,
    'charset': 'utf8mb4'
}

# 目录配置
DIRS = {
    'pdf_dir': PDF_DIR,
    'records_dir': RECORDS_DIR,
    'driver_path': '/opt/maxkb/chromedriver-linux64/chromedriver',
    'venv_dir': '/opt/maxkb/confluence/venv',
    'logs_dir': LOGS_DIR
}

# 文件配置
FILES = {
    'father_page_ids': 'all_father_page_ids.txt',
    'all_page_ids': 'all_page_ids.txt',
    'failed_pages': 'failed_pages.txt',
    'no_permission_pages': 'no_permission_pages.txt'
}

# 邮件配置
EMAIL_CONFIG = {
    'smtp_server': 'smtp.qiye.aliyun.com',
    'smtp_port': 465,
    'username': 'your_email@flamelephant.com',
    'password': 'your_email_password',
    'sender': 'your_email@flamelephant.com',
    'recipients': ['recipient1@flamelephant.com']
}
EOF
    fi
}

# 设置定时任务
setup_cron() {
    log_info "设置定时任务..."
    
    # 设置脚本权限
    chmod +x "$WORK_DIR/incremental_update.sh"
    chmod +x "$WORK_DIR/full_update.sh"
    chmod +x "$WORK_DIR/setup_cron.sh"
    
    # 运行定时任务设置脚本
    "$WORK_DIR/setup_cron.sh"
}

# 主安装流程
main() {
    log_info "开始安装 Confluence 文档同步工具..."
    
    # 执行安装步骤
    check_system
    create_directories
    setup_virtualenv
    setup_config
    setup_cron
    
    log_info "安装完成！"
    log_info "请确保完成以下操作："
    echo "1. 修改 confluence/config.py 中的配置信息"
    echo "2. 在 records/all_father_page_ids.txt 中设置父页面ID"
    echo "3. 运行 source venv/bin/activate 激活虚拟环境"
    echo "4. 运行 ./incremental_update.sh 测试增量更新"
    echo "5. 检查 logs/update_confluence.log 查看运行日志"
}

# 执行主函数
main
