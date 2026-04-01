#!/usr/bin/env python3
"""
系统健康检查脚本 - Health Check
定期检查系统状态，主动发现问题，支持飞书告警
"""

import os
import sys
import json
import time
import logging
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from execution.notifier import NotificationManager
except ImportError:
    NotificationManager = None

try:
    from utils.resource_monitor import get_memory_info, get_cpu_info, get_disk_info
    HAS_RESOURCE_MONITOR = True
except ImportError:
    HAS_RESOURCE_MONITOR = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class HealthChecker:
    """健康检查器"""
    
    def __init__(self, project_dir: str = ".", notify: bool = True):
        self.project_dir = Path(project_dir)
        self.checks = []
        self.issues = []
        self.warnings = []
        self.stats = {}
        
        # 初始化通知器
        self.notifier = None
        if notify and NotificationManager:
            try:
                env_file = self.project_dir / ".env"
                if env_file.exists():
                    with open(env_file, 'r') as f:
                        for line in f:
                            if '=' in line and not line.startswith('#'):
                                key, value = line.strip().split('=', 1)
                                os.environ.setdefault(key, value)
                
                self.notifier = NotificationManager()
            except Exception as e:
                logger.warning(f"通知器初始化失败: {e}")
    
    def check_disk_space(self) -> bool:
        """检查磁盘空间"""
        try:
            stat = os.statvfs(self.project_dir)
            free_gb = (stat.f_bavail * stat.f_frsize) / (1024**3)
            total_gb = (stat.f_blocks * stat.f_frsize) / (1024**3)
            used_percent = ((total_gb - free_gb) / total_gb) * 100
            
            self.stats['disk'] = {
                'free_gb': round(free_gb, 2),
                'total_gb': round(total_gb, 2),
                'used_percent': round(used_percent, 1)
            }
            
            if free_gb < 1:  # 少于1GB
                self.issues.append(f"🚨 磁盘空间不足: 仅剩 {free_gb:.1f}GB")
                return False
            elif free_gb < 3:  # 少于3GB警告
                self.warnings.append(f"⚠️ 磁盘空间紧张: 仅剩 {free_gb:.1f}GB")
            
            logger.info(f"磁盘空间: {free_gb:.1f}GB 可用 ({used_percent:.1f}% 已用)")
            return True
            
        except Exception as e:
            logger.error(f"磁盘检查失败: {e}")
            return False
    
    def check_memory(self) -> bool:
        """检查内存使用"""
        try:
            mem = get_memory_info()
            if not mem:
                logger.info("内存检查跳过")
                return True
            
            self.stats['memory'] = mem
            
            if mem['percent'] > 90:
                self.issues.append(f"🚨 内存使用率过高: {mem['percent']}%")
                return False
            elif mem['percent'] > 80:
                self.warnings.append(f"⚠️ 内存使用率较高: {mem['percent']}%")
            
            logger.info(f"内存: {mem['percent']}% 已用")
            return True
            
        except Exception as e:
            logger.error(f"内存检查失败: {e}")
            return True  # 非关键检查
    
    def check_cpu(self) -> bool:
        """检查CPU使用"""
        try:
            cpu = get_cpu_info()
            if not cpu:
                logger.info("CPU检查跳过")
                return True
            
            self.stats['cpu'] = cpu
            
            if cpu['percent'] > 95:
                self.issues.append(f"🚨 CPU使用率过高: {cpu['percent']}%")
                return False
            elif cpu['percent'] > 85:
                self.warnings.append(f"⚠️ CPU使用率较高: {cpu['percent']}%")
            
            logger.info(f"CPU: {cpu['percent']}%")
            return True
            
        except Exception as e:
            logger.error(f"CPU检查失败: {e}")
            return True
    
    def check_file_integrity(self) -> bool:
        """检查关键文件完整性"""
        critical_files = [
            "strategies/base.py",
            "strategies/minervini_sepa.py",
            "utils/akshare_fetcher.py",
            "utils/unified_fetcher.py",
            "execution/notifier.py",
            "execution/order_manager.py",
            "config/watchlist.txt",
            "scripts/daily_scanner.py",
            "scripts/news_monitor.py"
        ]
        
        all_ok = True
        for file in critical_files:
            path = self.project_dir / file
            if not path.exists():
                self.issues.append(f"🚨 关键文件缺失: {file}")
                all_ok = False
        
        if all_ok:
            logger.info("关键文件检查通过")
        
        return all_ok
    
    def check_cron_jobs(self) -> bool:
        """检查定时任务"""
        try:
            result = subprocess.run(
                ["crontab", "-l"],
                capture_output=True,
                text=True
            )
            
            cron_content = result.stdout
            
            has_sepa = "daily_scanner" in cron_content
            has_news = "news_monitor" in cron_content
            has_health = "health_check" in cron_content
            
            if not has_sepa:
                self.issues.append("🚨 SEPA扫描定时任务未配置")
            if not has_news:
                self.issues.append("🚨 新闻监控定时任务未配置")
            if not has_health:
                self.warnings.append("⚠️ 健康检查定时任务未配置")
            
            if has_sepa and has_news:
                logger.info("定时任务配置正常")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"定时任务检查失败: {e}")
            return False
    
    def check_logs(self) -> bool:
        """检查日志文件"""
        logs_dir = self.project_dir / "logs"
        
        if not logs_dir.exists():
            logger.warning("日志目录不存在")
            return True
        
        # 检查日志文件大小
        for log_file in logs_dir.glob("*.log"):
            size_mb = log_file.stat().st_size / (1024 * 1024)
            if size_mb > 100:  # 超过100MB
                msg = f"⚠️ 日志文件过大: {log_file.name} ({size_mb:.1f}MB)"
                if msg not in self.warnings:
                    self.warnings.append(msg)
        
        logger.info("日志检查通过")
        return True
    
    def check_env(self) -> bool:
        """检查环境配置"""
        env_file = self.project_dir / ".env"
        
        if not env_file.exists():
            self.issues.append("🚨 环境配置文件 .env 不存在")
            return False
        
        with open(env_file, 'r') as f:
            content = f.read()
        
        if "FEISHU_WEBHOOK" not in content:
            self.issues.append("🚨 飞书Webhook未配置")
            return False
        
        logger.info("环境配置检查通过")
        return True
    
    def check_data_freshness(self) -> bool:
        """检查数据新鲜度"""
        try:
            data_dir = self.project_dir / "data" / "raw" / "akshare"
            if not data_dir.exists():
                return True
            
            # 检查最近更新的文件
            recent_files = []
            for f in data_dir.glob("*.json"):
                age_hours = (time.time() - f.stat().st_mtime) / 3600
                if age_hours < 24:
                    recent_files.append(f.name)
            
            if len(recent_files) < 3:
                msg = "⚠️ 数据更新不够频繁，建议检查数据源"
                if msg not in self.warnings:
                    self.warnings.append(msg)
            
            return True
            
        except Exception as e:
            logger.error(f"数据新鲜度检查失败: {e}")
            return True
    
    def run_all_checks(self) -> Dict:
        """运行所有检查"""
        logger.info("=" * 50)
        logger.info("开始系统健康检查")
        logger.info("=" * 50)
        
        checks = [
            ("磁盘空间", self.check_disk_space),
            ("内存使用", self.check_memory),
            ("CPU负载", self.check_cpu),
            ("文件完整性", self.check_file_integrity),
            ("定时任务", self.check_cron_jobs),
            ("日志文件", self.check_logs),
            ("环境配置", self.check_env),
            ("数据新鲜度", self.check_data_freshness)
        ]
        
        results = {}
        for name, check_func in checks:
            try:
                results[name] = check_func()
            except Exception as e:
                logger.error(f"{name}检查异常: {e}")
                results[name] = False
        
        return {
            "timestamp": datetime.now().isoformat(),
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "checks": results,
            "issues": self.issues,
            "warnings": self.warnings,
            "stats": self.stats,
            "healthy": len(self.issues) == 0,
            "has_warnings": len(self.warnings) > 0
        }
    
    def generate_report(self) -> str:
        """生成健康报告"""
        result = self.run_all_checks()
        
        lines = []
        lines.append("=" * 50)
        lines.append("📊 量化系统健康报告")
        lines.append("=" * 50)
        lines.append(f"检查时间: {result['date']}")
        lines.append("")
        
        # 资源状态
        if 'disk' in result['stats']:
            d = result['stats']['disk']
            lines.append(f"💾 磁盘: {d['free_gb']}GB 可用 / {d['total_gb']}GB 总计")
        if 'memory' in result['stats']:
            m = result['stats']['memory']
            lines.append(f"🧠 内存: {m['percent']}% 已用")
        if 'cpu' in result['stats']:
            c = result['stats']['cpu']
            lines.append(f"⚡ CPU: {c['percent']}%")
        lines.append("")
        
        # 检查项
        for check_name, passed in result['checks'].items():
            status = "✅" if passed else "❌"
            lines.append(f"{status} {check_name}")
        
        # 问题列表
        if result['issues']:
            lines.append("")
            lines.append("🚨 严重问题:")
            for issue in result['issues']:
                lines.append(f"   {issue}")
        
        # 警告列表
        if result['warnings']:
            lines.append("")
            lines.append("⚠️ 警告:")
            for warning in result['warnings']:
                lines.append(f"   {warning}")
        
        lines.append("")
        if result['healthy']:
            lines.append("🎉 系统运行正常！")
        else:
            lines.append("🔴 系统存在问题，需要立即处理！")
        
        if result['has_warnings'] and result['healthy']:
            lines.append("💡 有一些优化建议，请查看警告列表")
        
        lines.append("=" * 50)
        
        return "\n".join(lines)
    
    def send_notification(self, report: str, result: Dict):
        """发送飞书通知"""
        if not self.notifier or not self.notifier.enabled:
            logger.warning("通知器未启用，跳过发送")
            return
        
        try:
            # 根据状态选择通知级别
            if not result['healthy']:
                # 严重问题 - 发送告警
                self.notifier.send_risk_alert(
                    title="系统健康检查异常",
                    content=f"发现 {len(result['issues'])} 个严重问题，请立即查看！",
                    level="error"
                )
            elif result['has_warnings']:
                # 有警告 - 发送信息提醒
                self.notifier.send_risk_alert(
                    title="系统健康检查警告",
                    content=f"系统运行正常，但有 {len(result['warnings'])} 个优化建议",
                    level="warning"
                )
            else:
                # 完全正常 - 发送日报
                # 只在特定时间发送日报（避免每次检查都发送）
                hour = datetime.now().hour
                if hour == 9:  # 每天上午9点发送日报
                    self.notifier.send_daily_report(report)
            
            logger.info("通知发送完成")
            
        except Exception as e:
            logger.error(f"发送通知失败: {e}")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='系统健康检查')
    parser.add_argument('--project-dir', default='.', help='项目目录')
    parser.add_argument('--json', action='store_true', help='输出JSON格式')
    parser.add_argument('--no-notify', action='store_true', help='不发送通知')
    parser.add_argument('--daily-report', action='store_true', help='强制发送日报')
    
    args = parser.parse_args()
    
    checker = HealthChecker(args.project_dir, notify=not args.no_notify)
    result = checker.run_all_checks()
    
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        report = checker.generate_report()
        print(report)
    
    # 保存检查结果
    health_file = Path(args.project_dir) / "data" / "health_status.json"
    health_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(health_file, 'w') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    # 发送通知（如果启用）
    if not args.no_notify:
        report = checker.generate_report()
        checker.send_notification(report, result)
    
    # 返回退出码（用于cron）
    return 0 if result['healthy'] else 1


if __name__ == "__main__":
    sys.exit(main())
