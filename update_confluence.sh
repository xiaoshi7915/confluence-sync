#!/bin/bash

# 设置工作目录
WORK_DIR="/opt/maxkb/confluence"
cd $WORK_DIR

# 清理旧的日志文件
rm -f update_confluence.log

# 设置日志文件
LOG_FILE="update_confluence.log"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

# 记录开始时间
echo "[$TIMESTAMP] 开始增量更新" >> $LOG_FILE

# 设置Python路径
export PYTHONPATH=$WORK_DIR

# 初始化数据库
echo "[$TIMESTAMP] 初始化数据库" >> $LOG_FILE
PYTHONPATH=$WORK_DIR python3 confluence/init_db.py >> $LOG_FILE 2>&1

# 创建必要的目录和文件
echo "[$TIMESTAMP] 创建必要的目录和文件" >> $LOG_FILE
PYTHONPATH=$WORK_DIR python3 $WORK_DIR/setup.py >> $LOG_FILE 2>&1

# 清理旧的cookies和进程
rm -f confluence/cookies.pkl
pkill -f "chrome"
pkill -f "chromedriver"

# 重新获取cookies
echo "[$TIMESTAMP] 重新获取cookies" >> $LOG_FILE
python3 - << EOF >> $LOG_FILE 2>&1
from confluence.spiders.selenium_login import get_cookies
from confluence.config import CONFLUENCE_CONFIG
get_cookies(CONFLUENCE_CONFIG['url'], CONFLUENCE_CONFIG['username'], CONFLUENCE_CONFIG['password'])
EOF

# 执行增量更新
echo "[$TIMESTAMP] 开始增量更新" >> $LOG_FILE
PYTHONPATH=$WORK_DIR python3 - << EOF >> $LOG_FILE 2>&1
from confluence.spiders.incremental_update import perform_incremental_update
perform_incremental_update()
EOF

# 记录完成时间
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
echo "[$TIMESTAMP] 增量更新完成" >> $LOG_FILE
echo "----------------------------------------" >> $LOG_FILE