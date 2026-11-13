"""Heat index tests. Expected values come from the NWS heat index chart:
https://www.weather.gov/safety/heat-index
The NWS formula is accurate to about +/-1.3F, so we allow 1.5F.
"""
import pytest

from heat_index import heat_index, risk_level

# (temperature F, humidity %, value on the NWS chart)
NWS_CHART = [
    (80, 40, 80),
    (86, 50, 88),
    (86, 85, 102),
    (88, 60, 95),
    (90, 40, 91),
    (90, 70, 105),
    (92, 55, 101),
    (94, 45, 100),
    (96, 40, 101),
    (96, 65, 121),
    (98, 50, 113),
    (100, 40, 109),
    (104, 40, 119),
    (110, 40, 136),
]


@pytest.mark.parametrize("temp, rh, expected", NWS_CHART)
def test_matches_nws_chart(temp, rh, expected):
    assert heat_index(temp, rh) == pytest.approx(expected, abs=1.5)


def test_cool_day_stays_close_to_air_temp():
    # Below 80F the simple formula is used: 0.5*(70+61+2.4+4.7) = 69.05
    assert heat_index(70, 50) == pytest.approx(69.05, abs=0.1)


def test_bad_humidity_gives_error():
    with pytest.raises(ValueError):
        heat_index(90, 120)


@pytest.mark.parametrize("hi, level", [
    (79, "Lower risk"),
    (85, "Caution"),
    (95, "Extreme Caution"),
    (110, "Danger"),
    (130, "Extreme Danger"),
])
def test_risk_levels(hi, level):
    assert risk_level(hi) == level
