import os
from confluence.config import DIRS, FILES  # 修改这一行，使用完整的导入路径

def setup_directories():
    """创建必要的目录和文件"""
    # 创建目录
    for dir_path in DIRS.values():
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
            print(f"创建目录: {dir_path}")
            
    # 创建records目录下的文件
    records_dir = DIRS['records_dir']
    for file_name in FILES.values():
        file_path = os.path.join(records_dir, file_name)
        if not os.path.exists(file_path):
            open(file_path, 'w', encoding='utf-8').close()
            print(f"创建文件: {file_path}")

if __name__ == "__main__":
    setup_directories() 