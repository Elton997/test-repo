"""
In-memory cache utilities for summary endpoints.
Currently only used for location summaries but can be extended later.
"""
from __future__ import annotations

import time
from copy import deepcopy
from threading import RLock
from typing import Any, Dict, Optional

from app.core.config import settings


class _SummaryCache:
    def __init__(self) -> None:
        self._lock = RLock()
        self._payload: Optional[Dict[str, Any]] = None
        self._expires_at: float = 0.0

    def get(self) -> Optional[Dict[str, Any]]:
        ttl = settings.SUMMARY_CACHE_TTL_SECONDS
        if ttl <= 0:
            return None

        now = time.time()
        with self._lock:
            if self._payload is None or self._expires_at <= now:
                return None
            return deepcopy(self._payload)

    def set(self, payload: Dict[str, Any]) -> None:
        ttl = settings.SUMMARY_CACHE_TTL_SECONDS
        if ttl <= 0:
            return

        with self._lock:
            self._payload = deepcopy(payload)
            self._expires_at = time.time() + ttl

    def clear(self) -> None:
        with self._lock:
            self._payload = None
            self._expires_at = 0.0


_location_summary_cache = _SummaryCache()


def get_cached_location_summary() -> Optional[Dict[str, Any]]:
    return _location_summary_cache.get()


def set_cached_location_summary(payload: Dict[str, Any]) -> None:
    _location_summary_cache.set(payload)


def invalidate_location_summary_cache() -> None:
    _location_summary_cache.clear()

