#!/usr/bin/env python3
"""
系统资源监控 - 不依赖 psutil，使用系统命令
"""

import os
import re
import subprocess
from typing import Dict, Optional


def get_memory_info() -> Optional[Dict]:
    """获取内存信息（Linux）"""
    try:
        with open('/proc/meminfo', 'r') as f:
            content = f.read()
        
        # 解析内存信息
        total = re.search(r'MemTotal:\s+(\d+)', content)
        available = re.search(r'MemAvailable:\s+(\d+)', content)
        free = re.search(r'MemFree:\s+(\d+)', content)
        
        if total and available:
            total_kb = int(total.group(1))
            available_kb = int(available.group(1))
            total_gb = total_kb / (1024 * 1024)
            available_gb = available_kb / (1024 * 1024)
            used_percent = ((total_kb - available_kb) / total_kb) * 100
            
            return {
                'total_gb': round(total_gb, 2),
                'available_gb': round(available_gb, 2),
                'percent': round(used_percent, 1)
            }
    except:
        pass
    return None


def get_cpu_info() -> Optional[Dict]:
    """获取CPU信息"""
    try:
        # 使用 top 命令获取CPU使用率（单次采样）
        result = subprocess.run(
            ['top', '-bn1'],
            capture_output=True,
            text=True,
            timeout=2
        )
        
        # 解析CPU行
        cpu_line = re.search(r'%Cpu\(s\):\s+([\d.]+)\s+us', result.stdout)
        if cpu_line:
            user_percent = float(cpu_line.group(1))
            return {
                'percent': round(user_percent, 1),
                'core_count': os.cpu_count()
            }
    except:
        pass
    return None


def get_disk_info(path: str = '.') -> Optional[Dict]:
    """获取磁盘信息"""
    try:
        stat = os.statvfs(path)
        free_gb = (stat.f_bavail * stat.f_frsize) / (1024**3)
        total_gb = (stat.f_blocks * stat.f_frsize) / (1024**3)
        used_percent = ((total_gb - free_gb) / total_gb) * 100
        
        return {
            'free_gb': round(free_gb, 2),
            'total_gb': round(total_gb, 2),
            'used_percent': round(used_percent, 1)
        }
    except:
        return None


if __name__ == "__main__":
    print("内存:", get_memory_info())
    print("CPU:", get_cpu_info())
    print("磁盘:", get_disk_info())
