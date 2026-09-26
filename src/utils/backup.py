"""
数据备份与恢复模块

提供：
1. ChromaDB 向量数据库备份
2. 会话数据归档
3. 自动备份调度
4. 备份完整性验证
"""

import json
import os
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from .logging import SessionLogger

_log = SessionLogger("backup")


class BackupManager:
    """
    备份管理器

    支持：
    - 全量备份
    - 增量备份
    - 备份恢复
    - 备份验证
    """

    def __init__(
        self,
        backup_dir: str = "./data/backups",
        chroma_dir: str = "./data/chroma_db",
        max_backups: int = 7,
    ):
        self.backup_dir = Path(backup_dir)
        self.chroma_dir = Path(chroma_dir)
        self.max_backups = max_backups
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def create_backup(self, label: str = "") -> dict:
        """创建全量备份"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"backup_{timestamp}"
        if label:
            backup_name += f"_{label}"
        backup_path = self.backup_dir / backup_name

        try:
            backup_path.mkdir(parents=True, exist_ok=True)

            if self.chroma_dir.exists():
                chroma_backup = backup_path / "chroma_db"
                shutil.copytree(self.chroma_dir, chroma_backup)

            metadata = {
                "timestamp": time.time(),
                "datetime": datetime.now().isoformat(),
                "label": label,
                "type": "full",
                "chroma_exists": self.chroma_dir.exists(),
            }
            meta_path = backup_path / "metadata.json"
            meta_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2))

            self._cleanup_old_backups()

            _log.info(
                "backup_created",
                backup_name=backup_name,
                path=str(backup_path),
            )

            return {"success": True, "backup_name": backup_name, "path": str(backup_path)}

        except Exception as exc:
            _log.error("backup_failed", error=str(exc))
            return {"success": False, "error": str(exc)}

    def restore_backup(self, backup_name: str) -> dict:
        """从备份恢复"""
        backup_path = self.backup_dir / backup_name

        if not backup_path.exists():
            return {"success": False, "error": f"备份不存在: {backup_name}"}

        try:
            chroma_backup = backup_path / "chroma_db"
            if chroma_backup.exists():
                if self.chroma_dir.exists():
                    archive_name = f"chroma_db_pre_restore_{int(time.time())}"
                    self.chroma_dir.rename(self.backup_dir / archive_name)
                shutil.copytree(chroma_backup, self.chroma_dir)

            _log.info("backup_restored", backup_name=backup_name)
            return {"success": True, "backup_name": backup_name}

        except Exception as exc:
            _log.error("restore_failed", error=str(exc))
            return {"success": False, "error": str(exc)}

    def verify_backup(self, backup_name: str) -> dict:
        """验证备份完整性"""
        backup_path = self.backup_dir / backup_name

        if not backup_path.exists():
            return {"valid": False, "error": "备份不存在"}

        checks = {
            "metadata_exists": False,
            "metadata_valid": False,
            "chroma_backup_exists": False,
        }

        meta_path = backup_path / "metadata.json"
        if meta_path.exists():
            checks["metadata_exists"] = True
            try:
                meta = json.loads(meta_path.read_text())
                checks["metadata_valid"] = "timestamp" in meta
            except Exception:
                pass

        chroma_backup = backup_path / "chroma_db"
        if chroma_backup.exists():
            checks["chroma_backup_exists"] = True

        all_ok = all(checks.values())
        return {"valid": all_ok, "checks": checks}

    def list_backups(self) -> list[dict]:
        """列出所有备份"""
        backups = []
        if not self.backup_dir.exists():
            return backups

        for entry in sorted(self.backup_dir.iterdir(), reverse=True):
            if entry.is_dir() and entry.name.startswith("backup_"):
                meta_path = entry / "metadata.json"
                if meta_path.exists():
                    try:
                        meta = json.loads(meta_path.read_text())
                        backups.append({
                            "name": entry.name,
                            "datetime": meta.get("datetime", ""),
                            "label": meta.get("label", ""),
                            "type": meta.get("type", "full"),
                        })
                    except Exception:
                        backups.append({"name": entry.name, "datetime": "", "label": "", "type": "unknown"})
        return backups

    def _cleanup_old_backups(self):
        """清理超出保留数量的旧备份"""
        backups = sorted(
            [d for d in self.backup_dir.iterdir() if d.is_dir() and d.name.startswith("backup_")],
            key=lambda d: d.stat().st_mtime,
        )
        while len(backups) > self.max_backups:
            oldest = backups.pop(0)
            shutil.rmtree(oldest, ignore_errors=True)
            _log.info("old_backup_removed", name=oldest.name)


class SessionArchiver:
    """
    会话归档器

    将已结束的会话数据归档到文件
    """

    def __init__(self, archive_dir: str = "./data/session_archives"):
        self.archive_dir = Path(archive_dir)
        self.archive_dir.mkdir(parents=True, exist_ok=True)

    def archive_session(self, session_id: str, data: dict) -> dict:
        """归档单个会话"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d")
            archive_file = self.archive_dir / f"{timestamp}.jsonl"

            record = {
                "session_id": session_id,
                "archived_at": time.time(),
                "data": data,
            }

            with open(archive_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")

            _log.info("session_archived", session_id=session_id)
            return {"success": True, "file": str(archive_file)}

        except Exception as exc:
            _log.error("archive_failed", session_id=session_id, error=str(exc))
            return {"success": False, "error": str(exc)}

    def query_archives(
        self,
        session_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> list[dict]:
        """查询归档数据"""
        results = []

        for archive_file in sorted(self.archive_dir.glob("*.jsonl")):
            file_date = archive_file.stem
            if start_date and file_date < start_date:
                continue
            if end_date and file_date > end_date:
                continue

            with open(archive_file, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        record = json.loads(line.strip())
                        if session_id and record.get("session_id") != session_id:
                            continue
                        results.append(record)
                    except Exception:
                        continue

        return results


# ─── 全局实例 ────────────────────────────────────────────────────────────────

backup_manager = BackupManager()
session_archiver = SessionArchiver()
