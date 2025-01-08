#!/bin/bash

# 设置工作目录
WORK_DIR="/opt/maxkb/confluence"
cd $WORK_DIR

# 创建新的crontab文件
cat > confluence_cron << 'EOF'
# 每小时执行一次增量更新
0 * * * * cd /opt/maxkb/confluence && ./incremental_update.sh >> /opt/maxkb/confluence/logs/incremental_update.log 2>&1

# 每天18点执行每日汇总
0 18 * * * cd /opt/maxkb/confluence && source venv/bin/activate && PYTHONPATH=/opt/maxkb/confluence python3 -c "from confluence.utils.email_sender import send_daily_summary; from confluence.spiders.incremental_update import get_daily_updates; updates = get_daily_updates(); send_daily_summary(updates)" >> /opt/maxkb/confluence/logs/daily_summary.log 2>&1
EOF

# 安装新的crontab
crontab confluence_cron

# 删除临时文件
rm confluence_cron

echo "定时任务已设置：
1. 每小时整点执行增量更新
2. 每天18:00发送每日汇总邮件"

# 显示当前crontab内容
echo "当前crontab内容："
crontab -l
