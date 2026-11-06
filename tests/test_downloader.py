import pytest

from myanmar_dubber.downloader import is_supported_youtube_url


@pytest.mark.parametrize(
    "url",
    [
        "https://youtube.com/shorts/6fBvmLxaKdA?is=SZKWwA_jzw14HYaB",
        "https://www.youtube.com/watch?v=abc123",
        "https://m.youtube.com/live/abc123",
        "https://youtu.be/abc123?t=2",
    ],
)
def test_supported_youtube_urls(url: str) -> None:
    assert is_supported_youtube_url(url)


@pytest.mark.parametrize(
    "url",
    [
        "https://example.com/shorts/abc123",
        "https://youtube.com.evil.example/shorts/abc123",
        "https://youtube.com/",
        "https://youtu.be/",
        "ftp://youtube.com/watch?v=abc123",
        "https://user:secret@youtube.com/watch?v=abc123",
        "not a url",
    ],
)
def test_rejected_urls(url: str) -> None:
    assert not is_supported_youtube_url(url)
