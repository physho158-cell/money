import json

import pytest

from myanmar_dubber.translation import parse_translation_payload


def test_parse_translation_payload_restores_requested_order() -> None:
    payload = json.dumps(
        {
            "segments": [
                {"id": 2, "text": "တတိယ"},
                {"id": 0, "text": "ပထမ"},
                {"id": 1, "text": "ဒုတိယ"},
            ]
        },
        ensure_ascii=False,
    )
    assert parse_translation_payload(payload, [0, 1, 2]) == ["ပထမ", "ဒုတိယ", "တတိယ"]


@pytest.mark.parametrize(
    "payload",
    [
        "not json",
        "{}",
        '{"segments": []}',
        '{"segments": [{"id": 0, "text": ""}]}',
        '{"segments": [{"id": 1, "text": "wrong id"}]}',
        '{"segments": [{"id": 0, "text": "one"}, {"id": 0, "text": "duplicate"}]}',
    ],
)
def test_parse_translation_payload_rejects_invalid_responses(payload: str) -> None:
    with pytest.raises((ValueError, KeyError, TypeError, json.JSONDecodeError)):
        parse_translation_payload(payload, [0])
