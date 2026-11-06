from myanmar_dubber.models import TranscriptSegment
from myanmar_dubber.pipeline import speech_slots


def test_speech_slots_use_gaps_and_stop_at_video_end() -> None:
    segments = [
        TranscriptSegment(start=0.5, end=1.5, text="one"),
        TranscriptSegment(start=4.0, end=5.0, text="two"),
    ]
    assert speech_slots(segments, duration=8.0) == [(0.5, 3.45), (4.0, 4.0)]


def test_speech_slots_keep_a_minimum_for_close_segments() -> None:
    segments = [
        TranscriptSegment(start=1.0, end=1.1, text="one"),
        TranscriptSegment(start=1.05, end=1.2, text="two"),
    ]
    slots = speech_slots(segments, duration=2.0)
    assert slots[0][1] >= 0.05
    assert slots[-1][0] + slots[-1][1] <= 2.0
