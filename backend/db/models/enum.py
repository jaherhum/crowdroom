"""Enumerations used throughout the application."""

from enum import Enum


class StreamingPlatforms(str, Enum):
    """Enumeration of supported music streaming platforms."""

    SPOTIFY = "spotify"
    TIDAL = "tidal"


class ItemStatus(str, Enum):
    """Lifecycle state of a queue item and playback status in one unified enum.

    Transitions: QUEUED → NOW_PLAYING → PLAYING → PAUSED/STOPPED/BUFFERING/FINISHED
    """

    QUEUED = "queued"
    NOW_PLAYING = "now_playing"
    PLAYING = "playing"
    PAUSED = "paused"
    STOPPED = "stopped"
    BUFFERING = "buffering"
    ERROR = "error"
    FINISHED = "finished"


class TokenType(str, Enum):
    """Represents the type of token that can be generated."""

    ACCESS = "access"
    REFRESH = "refresh"

class ConnectionType(str, Enum):
    CLIENT_CREDENTIALS = "client_credentials"
    AUTHORIZATION_CODE = "authorization_code"