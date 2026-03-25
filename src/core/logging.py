"""Structured logging with JSON Lines output."""

import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
from threading import Lock


class JSONLinesHandler(logging.Handler):
    """Logging handler that outputs JSON Lines format.

    Implements J2: Structured logging to JSON Lines files.
    """

    def __init__(
        self,
        log_file: str = "logs/app.jsonl",
        audit_log_file: Optional[str] = "logs/audit_logs.jsonl",
        max_size_mb: int = 100,
        backup_count: int = 5,
    ):
        """Initialize JSON Lines handler.

        Args:
            log_file: Path to main application log file.
            audit_log_file: Optional path to audit log file.
            max_size_mb: Maximum file size before rotation.
            backup_count: Number of backup files to keep.
        """
        super().__init__()
        self.log_file = Path(log_file)
        self.audit_log_file = Path(audit_log_file) if audit_log_file else None
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.backup_count = backup_count
        self._lock = Lock()

        # Ensure log directory exists
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        if self.audit_log_file:
            self.audit_log_file.parent.mkdir(parents=True, exist_ok=True)

    def emit(self, record: logging.LogRecord):
        """Emit a log record as JSON line.

        Args:
            record: Log record to emit.
        """
        try:
            log_entry = self._format_entry(record)
            self._write(log_entry, self.log_file)

            # Also write to audit log if this is an audit event
            if hasattr(record, "is_audit") and record.is_audit and self.audit_log_file:
                self._write(log_entry, self.audit_log_file)
        except Exception:
            self.handleError(record)

    def _format_entry(self, record: logging.LogRecord) -> str:
        """Format log record as JSON.

        Args:
            record: Log record.

        Returns:
            JSON string.
        """
        entry = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add extra fields
        if hasattr(record, "extra"):
            entry.update(record.extra)

        # Add trace_id if available
        if hasattr(record, "trace_id") and record.trace_id:
            entry["trace_id"] = record.trace_id

        # Add exception info if present
        if record.exc_info:
            entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(entry, ensure_ascii=False)

    def _write(self, entry: str, file_path: Path):
        """Write entry to file with rotation.

        Args:
            entry: JSON string to write.
            file_path: Path to log file.
        """
        with self._lock:
            # Check for rotation
            if file_path.exists() and file_path.stat().st_size >= self.max_size_bytes:
                self._rotate(file_path)

            with open(file_path, "a", encoding="utf-8") as f:
                f.write(entry + "\n")

    def _rotate(self, file_path: Path):
        """Rotate log file.

        Args:
            file_path: Path to log file.
        """
        # Remove oldest backup
        oldest = file_path.with_suffix(f".{self.backup_count}")
        if oldest.exists():
            oldest.unlink()

        # Rotate existing backups
        for i in range(self.backup_count - 1, 0, -1):
            src = file_path.with_suffix(f".{i}")
            if src.exists():
                dst = file_path.with_suffix(f".{i + 1}")
                src.rename(dst)

        # Rotate current file
        file_path.rename(file_path.with_suffix(".1"))


class AuditLogger:
    """Audit logger for tracking sensitive operations.

    Implements J2: Audit logging with patient data anonymization.
    """

    def __init__(self, audit_log_file: str = "logs/audit_logs.jsonl"):
        """Initialize audit logger.

        Args:
            audit_log_file: Path to audit log file.
        """
        self.audit_log_file = Path(audit_log_file)
        self.audit_log_file.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()

    def log(
        self,
        action: str,
        actor: Optional[str] = None,
        patient_id: Optional[str] = None,
        resource: Optional[str] = None,
        result: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        trace_id: Optional[str] = None,
    ):
        """Log an audit event.

        Args:
            action: Action performed (e.g., "PATIENT_LOOKUP", "BOOKING_CREATE").
            actor: User/system performing the action.
            patient_id: Patient ID (will be partially anonymized).
            resource: Resource being acted upon.
            result: Result of the action (e.g., "SUCCESS", "DENIED").
            metadata: Additional metadata.
            trace_id: Associated trace ID.
        """
        entry = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "actor": actor or "system",
            "patient_id": self._anonymize_id(patient_id) if patient_id else None,
            "resource": resource,
            "result": result,
            "trace_id": trace_id,
            "metadata": metadata or {},
        }

        with self._lock:
            with open(self.audit_log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def _anonymize_id(self, patient_id: str) -> str:
        """Anonymize patient ID for privacy.

        Args:
            patient_id: Patient ID to anonymize.

        Returns:
            Anonymized ID (e.g., "P***123").
        """
        if not patient_id or len(patient_id) < 4:
            return "***"
        return f"{patient_id[:2]}{'*' * (len(patient_id) - 4)}{patient_id[-2:]}"


def setup_logging(
    log_level: str = "INFO",
    log_file: str = "logs/app.jsonl",
    audit_log_file: str = "logs/audit_logs.jsonl",
):
    """Setup structured logging.

    Args:
        log_level: Logging level.
        log_file: Path to log file.
        audit_log_file: Path to audit log file.
    """
    # Create handler
    handler = JSONLinesHandler(log_file=log_file, audit_log_file=audit_log_file)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    root_logger.handlers.clear()
    root_logger.addHandler(handler)

    # Also add console handler for development
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.DEBUG)
    console.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
    root_logger.addHandler(console)

    return handler


# Global audit logger instance
_audit_logger: Optional[AuditLogger] = None


def get_audit_logger() -> AuditLogger:
    """Get the global audit logger instance.

    Returns:
        AuditLogger instance.
    """
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger
