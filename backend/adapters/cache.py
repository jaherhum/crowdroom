"""Module-level TTL cache for streaming platform metadata lookups."""

from cachetools import TTLCache

from backend.core.config import settings
from backend.schemas.song_metadata import ReadSongMetadata

_metadata_cache: TTLCache[str, ReadSongMetadata] = TTLCache(
    maxsize=settings.METADATA_CACHE_MAX_SIZE,
    ttl=settings.METADATA_CACHE_TTL_SECONDS,
)


def get_cached_metadata(platform: str, external_id: str) -> ReadSongMetadata | None:
    """Retrieve cached metadata if available.

    Args:
        platform: Platform identifier string.
        external_id: Platform-specific track identifier.

    Returns:
        Cached ReadSongMetadata or None if not cached/expired.
    """
    key = f"{platform}:{external_id}"
    return _metadata_cache.get(key)


def set_cached_metadata(
    platform: str, external_id: str, metadata: ReadSongMetadata
) -> None:
    """Store metadata in the TTL cache.

    Args:
        platform: Platform identifier string.
        external_id: Platform-specific track identifier.
        metadata: The metadata to cache.
    """
    key = f"{platform}:{external_id}"
    _metadata_cache[key] = metadata


def clear_cache() -> None:
    """Clear all cached metadata."""
    _metadata_cache.clear()
