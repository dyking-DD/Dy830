#!/usr/bin/env python3
"""
后台任务管理器 - Background Task Manager
用于管理长时间运行的任务，避免阻塞主会话

设计原则：
- 耗时操作放入后台执行
- 提供状态查询接口
- 失败时自动重试
- 结果持久化存储
"""

import os
import sys
import json
import time
import logging
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Callable
from dataclasses import dataclass, asdict
from enum import Enum

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


@dataclass
class Task:
    """任务定义"""
    task_id: str
    name: str
    command: List[str]
    status: TaskStatus
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    result: Optional[Dict] = None
    error: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3


class BackgroundTaskManager:
    """后台任务管理器"""
    
    def __init__(self, data_dir: str = "data/tasks"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.tasks_file = self.data_dir / "tasks.json"
        self.tasks: Dict[str, Task] = {}
        
        self._load_tasks()
    
    def _load_tasks(self):
        """加载任务列表"""
        if self.tasks_file.exists():
            try:
                with open(self.tasks_file, 'r') as f:
                    data = json.load(f)
                    for task_id, task_data in data.items():
                        self.tasks[task_id] = Task(**task_data)
            except Exception as e:
                logger.error(f"加载任务失败: {e}")
    
    def _save_tasks(self):
        """保存任务列表"""
        try:
            data = {tid: asdict(t) for tid, t in self.tasks.items()}
            with open(self.tasks_file, 'w') as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"保存任务失败: {e}")
    
    def submit_task(self, name: str, command: List[str], max_retries: int = 3) -> str:
        """
        提交后台任务
        
        Args:
            name: 任务名称
            command: 命令列表（如 ["python3", "script.py", "--arg"]）
            max_retries: 最大重试次数
        
        Returns:
            task_id: 任务ID
        """
        task_id = f"{name}_{int(time.time())}"
        
        task = Task(
            task_id=task_id,
            name=name,
            command=command,
            status=TaskStatus.PENDING,
            created_at=datetime.now().isoformat(),
            max_retries=max_retries
        )
        
        self.tasks[task_id] = task
        self._save_tasks()
        
        # 在后台启动任务
        self._start_task(task_id)
        
        logger.info(f"任务已提交: {task_id}")
        return task_id
    
    def _start_task(self, task_id: str):
        """启动任务"""
        task = self.tasks.get(task_id)
        if not task:
            return
        
        try:
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.now().isoformat()
            self._save_tasks()
            
            # 使用subprocess在后台运行
            log_file = self.data_dir / f"{task_id}.log"
            
            with open(log_file, 'w') as f:
                process = subprocess.Popen(
                    task.command,
                    stdout=f,
                    stderr=subprocess.STDOUT,
                    cwd=os.getcwd()
                )
                
                # 等待完成（非阻塞）
                returncode = process.wait()
                
                if returncode == 0:
                    task.status = TaskStatus.COMPLETED
                    task.result = {"returncode": returncode, "log_file": str(log_file)}
                    logger.info(f"任务完成: {task_id}")
                else:
                    raise Exception(f"进程返回错误码: {returncode}")
                    
        except Exception as e:
            logger.error(f"任务失败: {task_id}, 错误: {e}")
            task.error = str(e)
            
            if task.retry_count < task.max_retries:
                task.retry_count += 1
                task.status = TaskStatus.RETRYING
                logger.info(f"任务重试: {task_id} (第{task.retry_count}次)")
                time.sleep(5)  # 等待5秒后重试
                self._start_task(task_id)
            else:
                task.status = TaskStatus.FAILED
        
        task.completed_at = datetime.now().isoformat()
        self._save_tasks()
    
    def get_status(self, task_id: str) -> Optional[Dict]:
        """获取任务状态"""
        task = self.tasks.get(task_id)
        if not task:
            return None
        
        return {
            "task_id": task.task_id,
            "name": task.name,
            "status": task.status.value,
            "created_at": task.created_at,
            "started_at": task.started_at,
            "completed_at": task.completed_at,
            "retry_count": task.retry_count,
            "error": task.error
        }
    
    def get_log(self, task_id: str) -> str:
        """获取任务日志"""
        log_file = self.data_dir / f"{task_id}.log"
        if log_file.exists():
            try:
                with open(log_file, 'r') as f:
                    return f.read()
            except:
                return "无法读取日志"
        return "日志文件不存在"
    
    def list_tasks(self, status: Optional[str] = None) -> List[Dict]:
        """列出所有任务"""
        tasks = []
        for task in self.tasks.values():
            if status and task.status.value != status:
                continue
            tasks.append(self.get_status(task.task_id))
        return sorted(tasks, key=lambda x: x["created_at"], reverse=True)
    
    def cleanup_old_tasks(self, days: int = 7):
        """清理旧任务"""
        cutoff = datetime.now().timestamp() - (days * 24 * 3600)
        
        to_remove = []
        for task_id, task in self.tasks.items():
            created = datetime.fromisoformat(task.created_at).timestamp()
            if created < cutoff:
                to_remove.append(task_id)
                # 删除日志文件
                log_file = self.data_dir / f"{task_id}.log"
                if log_file.exists():
                    log_file.unlink()
        
        for task_id in to_remove:
            del self.tasks[task_id]
        
        self._save_tasks()
        logger.info(f"清理了 {len(to_remove)} 个旧任务")


# 全局任务管理器实例
_task_manager: Optional[BackgroundTaskManager] = None


def get_task_manager() -> BackgroundTaskManager:
    """获取全局任务管理器"""
    global _task_manager
    if _task_manager is None:
        _task_manager = BackgroundTaskManager()
    return _task_manager


# 便捷函数
def submit_background_task(name: str, command: List[str], max_retries: int = 3) -> str:
    """提交后台任务"""
    return get_task_manager().submit_task(name, command, max_retries)


def check_task_status(task_id: str) -> Optional[Dict]:
    """检查任务状态"""
    return get_task_manager().get_status(task_id)


def get_task_log(task_id: str) -> str:
    """获取任务日志"""
    return get_task_manager().get_log(task_id)


if __name__ == "__main__":
    # 测试
    manager = BackgroundTaskManager()
    
    # 提交测试任务
    task_id = manager.submit_task(
        "test_task",
        ["python3", "-c", "import time; print('开始'); time.sleep(2); print('完成')"]
    )
    
    print(f"任务已提交: {task_id}")
    
    # 轮询状态
    for _ in range(10):
        status = manager.get_status(task_id)
        print(f"状态: {status['status']}")
        
        if status['status'] in ['completed', 'failed']:
            print(f"日志:\n{manager.get_log(task_id)}")
            break
        
        time.sleep(1)
