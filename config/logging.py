"""
MEB RAG Sistemi - Logging Configuration
"""
import sys
import logging
import json
from datetime import datetime
from typing import Any, Dict

from config.settings import get_settings


class JSONFormatter(logging.Formatter):
    """
    JSON Formatter for structured logging.
    Essential for Docker/Cloud environments (OpenTelemetry/ELK compatible).
    """
    
    def format(self, record: logging.LogRecord) -> str:
        settings = get_settings()
        
        # Base log object
        log_obj: Dict[str, Any] = {
            "timestamp": datetime.utcfromtimestamp(record.created).isoformat() + "Z",
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "env":  "dev" if settings.debug else "prod",
            "service": "meb-rag-api"
        }
        
        # Add exception info if present
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
            log_obj["stack_trace"] = self.formatStack(record.stack_info) if record.stack_info else None
            
        # Add extra fields passed via extra={}
        if hasattr(record, "extra_data"):
            log_obj.update(record.extra_data)
            
        # Add correlation IDs if available (for request tracing)
        if hasattr(record, "request_id"):
            log_obj["request_id"] = record.request_id

        return json.dumps(log_obj, ensure_ascii=False)


def configure_logging():
    """Configure root logger with JSON formatter for Docker"""
    settings = get_settings()
    
    root_logger = logging.getLogger()
    
    # Set level
    log_level = logging.DEBUG if settings.debug else logging.INFO
    root_logger.setLevel(log_level)
    
    # Console Handler (Stdout)
    handler = logging.StreamHandler(sys.stdout)
    
    if settings.debug:
        # Human readable for dev
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s'
        )
    else:
        # JSON for prod/docker
        formatter = JSONFormatter()
        
    handler.setFormatter(formatter)
    
    # Remove existing handlers to avoid duplicates
    root_logger.handlers = []
    root_logger.addHandler(handler)
    
    # Silence noisy libraries
    logging.getLogger("azure").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
