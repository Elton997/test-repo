"""
Logger helper module for structured logging with environment-based configuration.
Supports JSON and text formats, with different log levels for dev/uat vs prod.
Automatically includes request_id and request context in all logs.
"""
import logging
import sys
import json
from contextvars import ContextVar
from datetime import datetime
from typing import Any, Dict, Optional
from pythonjsonlogger import jsonlogger
from app.core.config import settings

# Context variables for request context (thread-safe for async)
_request_id: ContextVar[Optional[str]] = ContextVar("request_id", default=None)
_request_context: ContextVar[Optional[Dict[str, Any]]] = ContextVar("request_context", default=None)


class RequestContextFilter(logging.Filter):
    """Filter that automatically adds request_id and request context to all log records."""
    
    def filter(self, record: logging.LogRecord) -> bool:
        # Get request_id from context
        request_id = _request_id.get()
        if request_id:
            record.request_id = request_id
        
        # Get request context from context
        request_context = _request_context.get()
        if request_context:
            # Add request context fields to the record
            for key, value in request_context.items():
                setattr(record, key, value)
        
        return True


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter that adds timestamp, environment info, and request context."""
    
    def add_fields(self, log_record: Dict[str, Any], record: logging.LogRecord, message_dict: Dict[str, Any]) -> None:
        super().add_fields(log_record, record, message_dict)
        
        # Add standard fields
        log_record["timestamp"] = datetime.utcnow().isoformat() + "Z"
        log_record["level"] = record.levelname
        log_record["logger"] = record.name
        log_record["environment"] = settings.ENVIRONMENT
        
        # Add request_id if available (from context filter)
        if hasattr(record, "request_id"):
            log_record["request_id"] = record.request_id
        
        # Add request context fields if available
        request_context = _request_context.get()
        if request_context:
            for key, value in request_context.items():
                if key not in log_record:  # Don't override existing fields
                    log_record[key] = value
        
        # Add exception info if present
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)


def setup_logger(name: str = "dcim_backend") -> logging.Logger:
    """
    Set up and configure a logger with environment-based settings.
    
    Args:
        name: Logger name (default: "dcim_backend")
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))
    
    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()
    
    # Create handler (console by default, file if specified)
    if settings.LOG_FILE:
        handler = logging.FileHandler(settings.LOG_FILE)
    else:
        handler = logging.StreamHandler(sys.stdout)
    
    # Set formatter based on configuration
    if settings.LOG_FORMAT == "json":
        formatter = CustomJsonFormatter(
            "%(timestamp)s %(level)s %(name)s %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S"
        )
    else:
        # Text formatter with request context
        class TextFormatter(logging.Formatter):
            """Text formatter that includes request context."""
            
            def format(self, record: logging.LogRecord) -> str:
                # Build base format
                base_msg = super().format(record)
                
                # Add request_id if available
                if hasattr(record, "request_id"):
                    base_msg = f"{base_msg} [request_id={record.request_id}]"
                
                # Add other request context fields
                request_context = _request_context.get()
                if request_context:
                    context_parts = []
                    for key, value in request_context.items():
                        if key != "request_id":  # Already added above
                            context_parts.append(f"{key}={value}")
                    if context_parts:
                        base_msg = f"{base_msg} [{', '.join(context_parts)}]"
                
                return base_msg
        
        formatter = TextFormatter(
            "[%(asctime)s] [%(levelname)s] [%(name)s] [%(environment)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
    
    handler.setFormatter(formatter)
    
    # Add request context filter to automatically include request_id
    handler.addFilter(RequestContextFilter())
    
    logger.addHandler(handler)
    
    # Prevent propagation to root logger
    logger.propagate = False
    
    return logger


def set_request_context(request_id: Optional[str] = None, **kwargs) -> None:
    """
    Set request context for logging. This will automatically be included in all subsequent logs.
    
    Args:
        request_id: Unique request ID
        **kwargs: Additional context fields (e.g., method, path, user_id)
    """
    if request_id:
        _request_id.set(request_id)
    
    if kwargs:
        _request_context.set(kwargs)
    elif request_id:
        # If only request_id is provided, set empty context
        _request_context.set({})


def clear_request_context() -> None:
    """Clear request context after request is processed."""
    _request_id.set(None)
    _request_context.set(None)


# Lazy logger instance - only created on first access
_app_logger = None


def get_app_logger() -> logging.Logger:
    """Lazy logger loader - logger is only created on first access."""
    global _app_logger
    if _app_logger is None:
        _app_logger = setup_logger("dcim_backend")
    return _app_logger


# For backwards compatibility, use a proxy class
class _LoggerProxy:
    """Proxy that lazily loads logger on first method call."""
    
    def __getattr__(self, name):
        return getattr(get_app_logger(), name)
    
    def __repr__(self):
        return repr(get_app_logger())


app_logger = _LoggerProxy()

