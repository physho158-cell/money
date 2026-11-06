import math

import pytest

from myanmar_dubber.media import atempo_factors


@pytest.mark.parametrize("tempo", [0.25, 0.5, 1.0, 1.75, 2.0, 4.0, 8.0])
def test_atempo_factors_preserve_tempo_and_ffmpeg_limits(tempo: float) -> None:
    factors = atempo_factors(tempo)
    assert math.prod(factors) == pytest.approx(tempo, rel=1e-4)
    assert all(0.5 <= factor <= 2.0 for factor in factors)


@pytest.mark.parametrize("tempo", [0, -1, math.inf, math.nan])
def test_atempo_factors_reject_invalid_values(tempo: float) -> None:
    with pytest.raises(ValueError):
        atempo_factors(tempo)
