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
        if command -v apt &> /dev/null; then
            # Debian/Ubuntu
            wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
            sudo sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list'
            sudo apt update
            sudo apt install -y google-chrome-stable
        elif command -v yum &> /dev/null; then
            # CentOS/RHEL
            sudo yum install -y google-chrome-stable
        else
            log_error "不支持的系统类型，请手动安装Chrome浏览器"
            exit 1
        fi
    fi
    
    # 检查必要的系统包
    log_info "检查并安装必要的系统包..."
    if command -v apt &> /dev/null; then
        sudo apt update
        sudo apt install -y python3-venv python3-dev default-libmysqlclient-dev build-essential
    elif command -v yum &> /dev/null; then
        sudo yum groupinstall -y "Development Tools"
        sudo yum install -y python3-devel mysql-devel
    fi
}

# 创建目录结构
create_directories() {
    log_info "创建目录结构..."
    
    # 创建主目录
    sudo mkdir -p "$WORK_DIR"
    sudo chown -R $USER:$USER "$WORK_DIR"
    
    # 创建子目录
    mkdir -p "$LOG_DIR"
    mkdir -p "$RECORDS_DIR"
    mkdir -p "$PDF_DIR"
    mkdir -p "$RECORDS_DIR/page_tree_cache"
    
    # 设置权限
    chmod 755 "$WORK_DIR"
    chmod -R 755 "$LOG_DIR"
    chmod -R 755 "$RECORDS_DIR"
    chmod -R 755 "$PDF_DIR"
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
        log_warn "未找到配置文件，请创建 confluence/config.py 并设置以下内容："
        echo "
CONFLUENCE_CONFIG = {
    'url': 'https://confluence.flamelephant.com',
    'username': 'your_username',
    'password': 'your_password'
}

DB_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'your_db_user',
    'password': 'your_db_password',
    'database': 'confluence',
    'charset': 'utf8mb4'
}

EMAIL_CONFIG = {
    'smtp_server': 'smtp.qiye.aliyun.com',
    'smtp_port': 465,
    'username': 'your_email',
    'password': 'your_email_password',
    'sender': 'your_sender_email',
    'recipients': ['recipient1@example.com', 'recipient2@example.com']
}

DIRS = {
    'pdf_dir': '$PDF_DIR',
    'records_dir': '$RECORDS_DIR',
    'logs_dir': '$LOG_DIR'
}

FILES = {
    'father_page_ids': 'all_father_page_ids.txt',
    'all_page_ids': 'all_page_ids.txt'
}
"
    fi
}

# 设置定时任务
setup_cron() {
    log_info "设置定时任务..."
    
    # 设置脚本权限
    chmod +x "$WORK_DIR/incremental_update.sh"
    chmod +x "$WORK_DIR/full_update.sh"
    
    # 运行定时任务设置脚本
    "$WORK_DIR/setup_cron.sh"
}

# 主安装流程
main() {
    log_info "开始安装 Confluence 文档同步工具..."
    
    # 检查是否为root用户
    if [ "$EUID" -ne 0 ]; then
        log_error "请使用root用户运行此脚本"
        exit 1
    }
    
    # 执行安装步骤
    check_system
    create_directories
    setup_virtualenv
    setup_config
    setup_cron
    
    log_info "安装完成！"
    log_info "请确保完成以下操作："
    echo "1. 配置 confluence/config.py 文件"
    echo "2. 在 records/all_father_page_ids.txt 中设置父页面ID"
    echo "3. 测试运行 ./incremental_update.sh"
}

# 执行主函数
main
