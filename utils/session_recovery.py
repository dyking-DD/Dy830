#!/usr/bin/env python3
"""
会话恢复管理器 - Session Recovery Manager
处理断线重连和状态恢复
"""

import json
import time
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SessionRecoveryManager:
    """会话恢复管理器"""
    
    CHECKPOINT_FILE = "data/session_checkpoint.json"
    MAX_CHECKPOINTS = 10
    
    def __init__(self):
        self.checkpoint_path = Path(self.CHECKPOINT_FILE)
        self.checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
        self.checkpoints: List[Dict] = []
        self._load_checkpoints()
    
    def _load_checkpoints(self):
        """加载检查点"""
        if self.checkpoint_path.exists():
            try:
                with open(self.checkpoint_path, 'r') as f:
                    self.checkpoints = json.load(f)
            except:
                self.checkpoints = []
    
    def _save_checkpoints(self):
        """保存检查点"""
        try:
            with open(self.checkpoint_path, 'w') as f:
                json.dump(self.checkpoints[-self.MAX_CHECKPOINTS:], f, indent=2)
        except Exception as e:
            logger.error(f"保存检查点失败: {e}")
    
    def save_checkpoint(self, context: Dict):
        """
        保存会话检查点
        
        Args:
            context: 会话上下文
                - last_action: 最后执行的动作
                - pending_tasks: 待处理任务
                - current_phase: 当前阶段
                - user_requests: 用户请求历史
        """
        checkpoint = {
            "timestamp": datetime.now().isoformat(),
            "unix_time": time.time(),
            "context": context
        }
        
        self.checkpoints.append(checkpoint)
        self._save_checkpoints()
        logger.info(f"检查点已保存: {checkpoint['timestamp']}")
    
    def get_last_checkpoint(self) -> Optional[Dict]:
        """获取最后一个检查点"""
        if self.checkpoints:
            return self.checkpoints[-1]
        return None
    
    def recover_session(self) -> Optional[Dict]:
        """
        恢复会话
        
        Returns:
            恢复后的上下文，如果没有检查点则返回None
        """
        checkpoint = self.get_last_checkpoint()
        if not checkpoint:
            logger.info("没有找到检查点，无法恢复")
            return None
        
        # 检查检查点是否过期（超过1小时）
        age_hours = (time.time() - checkpoint.get("unix_time", 0)) / 3600
        if age_hours > 1:
            logger.warning(f"检查点已过期 ({age_hours:.1f}小时)，谨慎恢复")
        
        logger.info(f"从检查点恢复: {checkpoint['timestamp']}")
        return checkpoint.get("context", {})
    
    def is_recovery_needed(self) -> bool:
        """检查是否需要恢复"""
        checkpoint = self.get_last_checkpoint()
        if not checkpoint:
            return False
        
        # 检查是否有未完成的任务
        context = checkpoint.get("context", {})
        pending = context.get("pending_tasks", [])
        
        return len(pending) > 0
    
    def mark_task_completed(self, task_id: str):
        """标记任务已完成"""
        checkpoint = self.get_last_checkpoint()
        if checkpoint:
            context = checkpoint.get("context", {})
            pending = context.get("pending_tasks", [])
            if task_id in pending:
                pending.remove(task_id)
                context["completed_tasks"] = context.get("completed_tasks", []) + [task_id]
                self._save_checkpoints()


# 便捷函数
_checkpoint_manager: Optional[SessionRecoveryManager] = None


def get_recovery_manager() -> SessionRecoveryManager:
    """获取恢复管理器实例"""
    global _checkpoint_manager
    if _checkpoint_manager is None:
        _checkpoint_manager = SessionRecoveryManager()
    return _checkpoint_manager


def save_session_checkpoint(context: Dict):
    """保存会话检查点"""
    get_recovery_manager().save_checkpoint(context)


def recover_session() -> Optional[Dict]:
    """恢复会话"""
    return get_recovery_manager().recover_session()


def check_recovery_needed() -> bool:
    """检查是否需要恢复"""
    return get_recovery_manager().is_recovery_needed()


if __name__ == "__main__":
    # 测试
    manager = SessionRecoveryManager()
    
    # 保存检查点
    manager.save_checkpoint({
        "last_action": "创建文件",
        "pending_tasks": ["task_1", "task_2"],
        "current_phase": "开发中"
    })
    
    # 恢复
    context = manager.recover_session()
    print(f"恢复的上下文: {context}")
