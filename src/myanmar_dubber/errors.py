class DubbingError(Exception):
    """Base exception for the dubbing service."""


class UserFacingError(DubbingError):
    """An expected error whose message is safe and useful for the Telegram user."""


class ConfigurationError(DubbingError):
    """Raised when required runtime configuration is missing or invalid."""


class MediaError(DubbingError):
    """Raised when ffprobe or ffmpeg cannot process a media file."""
