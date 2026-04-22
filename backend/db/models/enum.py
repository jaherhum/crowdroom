"""Enumerations used throughout the application."""
from enum import Enum


class StreamingPlatforms(str, Enum):
    """Enumeration of supported music streaming platforms."""

    SPOTIFY = "spotify"
    TIDAL = "tidal"


class PlaybackStatus(str, Enum):
    """Represents the current playback state of a music session."""

    BUFFERING = "buffering"
    PLAYING = "playing"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"


class TokenType(str, Enum):
    """Represents the type of token that can be generated."""

    ACCESS = "access"
    REFRESH = "refresh"
