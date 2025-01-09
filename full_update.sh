#!/bin/bash

# 设置工作目录
WORK_DIR="/opt/maxkb/confluence"
cd $WORK_DIR

# 激活虚拟环境
source venv/bin/activate

# 设置Python路径
export PYTHONPATH=/opt/maxkb/confluence

# 设置超时时间（4小时）
TIMEOUT=14400

# 创建日志目录
mkdir -p logs

# 设置日志文件
LOG_FILE="logs/update_confluence.log"

# 日志函数
log_message() {
    local TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$TIMESTAMP] $1" >> $LOG_FILE
}

# 清理指定进程
kill_process() {
    local PROCESS=$1
    local FORCE=$2
    
    if pgrep -f "$PROCESS" > /dev/null; then
        log_message "尝试终止 $PROCESS 进程..."
        if [ "$FORCE" = "force" ]; then
            pkill -9 -f "$PROCESS" 2>/dev/null || true
        else
            pkill -f "$PROCESS" 2>/dev/null || true
        fi
        sleep 1
    fi
}

# 清理进程函数
cleanup() {
    log_message "开始清理进程..."
    
    # 清理 Chrome 相关进程
    kill_process "chrome" "normal"
    kill_process "chromedriver" "normal"
    
    # 如果普通终止失败，强制终止
    kill_process "chrome" "force"
    kill_process "chromedriver" "force"
    
    # Scrapy 进程单独处理
    if pgrep -f "scrapy" > /dev/null; then
        log_message "终止 scrapy 进程..."
        pkill -f "scrapy" 2>/dev/null || true
    fi
    
    # 删除临时文件
    if [ -f "confluence/confluence/cookies.pkl" ]; then
        rm -f confluence/confluence/cookies.pkl
        log_message "删除 cookies.pkl"
    fi
    
    if [ -f "records/update_page_ids.txt" ]; then
        rm -f records/update_page_ids.txt
        log_message "删除 update_page_ids.txt"
    fi
    
    log_message "清理进程完成"
}

# 错误处理函数
handle_error() {
    log_message "发生错误，开始清理..."
    cleanup
    exit 1
}

# 设置信号处理
trap 'cleanup' EXIT
trap 'handle_error' ERR INT TERM

# 初始化环境
log_message "开始全量更新"
log_message "初始化环境..."
cleanup

# 创建必要的目录
log_message "创建必要的目录"
mkdir -p PDF_document records logs

# 初始化数据库
log_message "初始化数据库"
python3 -c "
from confluence.init_db import init_db
init_db()
" >> $LOG_FILE 2>&1

if [ $? -ne 0 ]; then
    log_message "数据库初始化失败"
    exit 1
fi

# 获取 cookies
log_message "开始获取 cookies"
python3 -c "
from confluence.utils.selenium_login import get_cookies
from confluence.config import CONFLUENCE_CONFIG
get_cookies(CONFLUENCE_CONFIG['base_url'], CONFLUENCE_CONFIG['username'], CONFLUENCE_CONFIG['password'])
" >> $LOG_FILE 2>&1

if [ $? -ne 0 ]; then
    log_message "获取 cookies 失败"
    exit 1
fi

# 获取所有页面ID
log_message "开始获取所有页面ID"
python3 -c "
from confluence.spiders.full_update import run_spider_with_timeout
success = run_spider_with_timeout('confluence_page_tree', timeout=1800)
if not success:
    raise Exception('获取页面ID失败')
" >> $LOG_FILE 2>&1

if [ $? -ne 0 ]; then
    log_message "获取页面ID失败"
    exit 1
fi

# 执行全量更新
log_message "开始下载页面PDF"
timeout $TIMEOUT python3 -c "
from confluence.spiders.full_update import perform_full_update
perform_full_update()
" >> $LOG_FILE 2>&1

EXIT_CODE=$?
if [ $EXIT_CODE -ne 0 ]; then
    if [ $EXIT_CODE -eq 124 ]; then
        log_message "更新超时"
    else
        log_message "更新失败，错误码: $EXIT_CODE"
    fi
    exit 1
fi

# 发送每日汇总邮件
log_message "发送更新汇总邮件"
python3 -c "
from confluence.utils.email_sender import send_daily_summary
from confluence.spiders.incremental_update import get_daily_updates
updates = get_daily_updates()
if updates:
    send_daily_summary(updates)
    print('发送更新汇总邮件成功')
else:
    print('没有需要汇总的更新')
" >> $LOG_FILE 2>&1

# 记录完成
log_message "全量更新完成"
log_message "----------------------------------------"
