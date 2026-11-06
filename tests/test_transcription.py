from types import SimpleNamespace

from myanmar_dubber.transcription import normalise_segments


def test_normalise_segments_sorts_and_cleans_values() -> None:
    raw = [
        {"start": 3, "end": 5, "text": "  Second line  "},
        SimpleNamespace(start=-1, end=2, text=" First line "),
        {"start": 5, "end": 5, "text": "No duration"},
        {"start": 5, "end": 6, "text": "   "},
        {"start": "bad", "end": 8, "text": "Bad timestamp"},
        {"start": 8, "end": 20, "text": "Last line"},
    ]
    segments = normalise_segments(raw, duration=10)
    assert [(item.start, item.end, item.text) for item in segments] == [
        (0.0, 2.0, "First line"),
        (3.0, 5.0, "Second line"),
        (8.0, 10.0, "Last line"),
    ]


def test_normalise_segments_accepts_empty_input() -> None:
    assert normalise_segments(None, duration=10) == []
