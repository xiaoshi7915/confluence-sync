#!/bin/bash

# 设置工作目录
WORK_DIR="/opt/maxkb/confluence"
cd $WORK_DIR

# 激活虚拟环境
source venv/bin/activate

# 设置Python路径
export PYTHONPATH=/opt/maxkb/confluence

# 创建日志目录
mkdir -p logs

# 设置日志文件
LOG_FILE="logs/incremental_update.log"

# 日志函数
log_message() {
    local TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$TIMESTAMP] $1" >> $LOG_FILE
}

# 开始执行
log_message "开始执行增量更新..."

# 执行增量更新（包括爬取和比较页面ID）
python3 -c "
from confluence.spiders.incremental_update import perform_incremental_update
perform_incremental_update()
" >> $LOG_FILE 2>&1

# 发送更新汇总邮件
python3 -c "
from confluence.utils.email_sender import send_daily_summary
from confluence.spiders.incremental_update import get_daily_updates
updates = get_daily_updates()
if updates:
    send_daily_summary(updates)
    print('发送更新汇总邮件成功')
else:
    print('本次没有新的更新')
" >> $LOG_FILE 2>&1

log_message "增量更新执行完成"
echo "----------------------------------------" >> $LOG_FILE 