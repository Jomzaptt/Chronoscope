"""通用工具函数"""

def format_seconds(seconds: int) -> str:
    """将秒数格式化为易读的时间字符串"""
    h, remainder = divmod(seconds, 3600)
    m, _ = divmod(remainder, 60)
    if h > 0:
        return f"{h}h {m}m"
    return f"{m}m"
