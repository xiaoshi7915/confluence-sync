#!/bin/bash

# 设置工作目录
WORK_DIR="/opt/maxkb/confluence"
LOGS_DIR="$WORK_DIR/logs"
LOG_FILE="$LOGS_DIR/update_confluence.log"

# 创建日志管理脚本
cat > "$WORK_DIR/manage_logs.sh" << 'EOF'
#!/bin/bash
LOGS_DIR="/opt/maxkb/confluence/logs"
CURRENT_DATE=$(date +%Y%m%d)
LOG_FILE="$LOGS_DIR/update_confluence.log"

# 如果当前日志文件存在且不为空，则进行备份
if [ -s "$LOG_FILE" ]; then
    cp "$LOG_FILE" "$LOGS_DIR/update_confluence_${CURRENT_DATE}.log"
fi

# 清空当前日志文件
echo "" > "$LOG_FILE"

# 删除7天前的日志文件
find "$LOGS_DIR" -name "update_confluence_*.log" -type f -mtime +7 -delete
EOF

# 设置日志管理脚本的执行权限
chmod +x "$WORK_DIR/manage_logs.sh"

# 创建临时文件来存储crontab内容
TEMP_CRON=$(mktemp)

# 导出当前的crontab内容
crontab -l > "$TEMP_CRON" 2>/dev/null

# 移除已存在的相关任务
sed -i '/incremental_update/d' "$TEMP_CRON"
sed -i '/update_confluence/d' "$TEMP_CRON"
sed -i '/manage_logs/d' "$TEMP_CRON"

# 添加新的定时任务
# 每3小时执行一次增量更新
echo "0 */3 * * * cd $WORK_DIR && source venv/bin/activate && ./incremental_update.sh" >> "$TEMP_CRON"

# 每天0点执行日志管理（备份当天日志并清理7天前的日志）
echo "0 0 * * * $WORK_DIR/manage_logs.sh" >> "$TEMP_CRON"

# 安装新的crontab
crontab "$TEMP_CRON"

# 删除临时文件
rm "$TEMP_CRON"

# 显示确认信息
echo "定时任务已设置："
echo "1. 每3小时执行一次增量更新"
echo "2. 每天0点备份日志并清理7天前的日志"
echo "当前crontab内容："
crontab -l
