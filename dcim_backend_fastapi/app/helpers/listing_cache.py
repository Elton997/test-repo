"""
Simple in-memory cache for listing responses.

Intended to reduce load for high-frequency dropdown/listing calls that often
reuse the same parameters. The cache layer is deliberately lightweight so it
can be replaced with Redis or another backend later if needed.
"""
from __future__ import annotations

import json
import time
from copy import deepcopy
from datetime import date
from hashlib import sha256
from threading import RLock
from typing import Any, Dict, Optional, Set

from app.core.config import settings
from app.helpers.listing_types import ListingType


def _is_cache_enabled() -> bool:
    return settings.LISTING_CACHE_TTL_SECONDS > 0 and settings.LISTING_CACHE_MAX_ENTRIES > 0


class _ListingResponseCache:
    def __init__(self) -> None:
        self._lock = RLock()
        self._store: Dict[str, tuple[float, Dict[str, Any]]] = {}
        self._entity_index: Dict[str, Set[str]] = {}

    @staticmethod
    def _normalize_entity(entity: ListingType | str | None) -> Optional[str]:
        if entity is None:
            return None
        if isinstance(entity, ListingType):
            return entity.value
        return str(entity)

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Get cached payload if available and not expired."""
        if not _is_cache_enabled():
            return None

        now = time.time()
        with self._lock:
            record = self._store.get(key)
            if not record:
                return None

            expires_at, payload = record
            if expires_at <= now:
                # Expired - use evict_key to properly clean up both store and index
                self._evict_key(key)
                return None

            return deepcopy(payload)

    def set(self, key: str, value: Dict[str, Any], *, entity: ListingType | str | None) -> None:
        """Set cached payload with expiration and entity indexing."""
        if not _is_cache_enabled():
            return

        expires_at = time.time() + settings.LISTING_CACHE_TTL_SECONDS
        entry = deepcopy(value)
        entity_key = self._normalize_entity(entity)

        with self._lock:
            # Evict oldest entry if cache is full (FIFO eviction)
            if len(self._store) >= settings.LISTING_CACHE_MAX_ENTRIES:
                oldest_key = next(iter(self._store))
                self._evict_key(oldest_key)

            # Store the entry
            self._store[key] = (expires_at, entry)
            
            # Index by entity for efficient invalidation
            if entity_key:
                self._entity_index.setdefault(entity_key, set()).add(key)

    def _evict_key(self, cache_key: str) -> None:
        record = self._store.pop(cache_key, None)
        if not record:
            return
        for entity_key, key_set in list(self._entity_index.items()):
            if cache_key in key_set:
                key_set.discard(cache_key)
                if not key_set:
                    self._entity_index.pop(entity_key, None)

    def clear_prefix(self, prefix: str) -> None:
        with self._lock:
            keys_to_delete = [cache_key for cache_key in self._store if cache_key.startswith(prefix)]
            for cache_key in keys_to_delete:
                self._evict_key(cache_key)

    def invalidate_entity(self, entity: ListingType | str) -> None:
        entity_key = self._normalize_entity(entity)
        if not entity_key:
            return

        with self._lock:
            keys = list(self._entity_index.get(entity_key, []))
            for cache_key in keys:
                self._evict_key(cache_key)

    def invalidate_all(self) -> None:
        with self._lock:
            self._store.clear()
            self._entity_index.clear()


listing_cache = _ListingResponseCache()


def build_listing_cache_key(
    *,
    entity: ListingType,
    offset: int,
    page_size: int,
    user_id: Optional[int],
    access_level: Optional[str],
    **filters: Any,
) -> str:
    """
    Build a deterministic cache key for listing responses.
    Includes all filter parameters in the cache key.
    Optimized to skip None values and handle dates efficiently.
    """
    fingerprint_payload = {
        "entity": entity.value if hasattr(entity, "value") else str(entity),
        "offset": offset,
        "page_size": page_size,
    }
    
    # Only include non-None values to reduce key size and improve cache efficiency
    if user_id is not None:
        fingerprint_payload["user_id"] = user_id
    if access_level is not None:
        fingerprint_payload["access_level"] = access_level
    
    # Add all filter parameters (skip None values and empty strings for efficiency)
    for key, value in sorted(filters.items()):
        if value is None or value == "":
            continue  # Skip None values and empty strings to reduce cache key size
        
        # Convert date objects to strings for consistent hashing
        if isinstance(value, date):
            fingerprint_payload[key] = value.isoformat()
        else:
            fingerprint_payload[key] = value
    
    # Use sort_keys=True for deterministic ordering
    fingerprint_json = json.dumps(fingerprint_payload, sort_keys=True, default=str)
    return sha256(fingerprint_json.encode("utf-8")).hexdigest()


def invalidate_listing_cache_for_entity(entity: ListingType | str) -> None:
    listing_cache.invalidate_entity(entity)


def clear_all_listing_cache() -> None:
    listing_cache.invalidate_all()

