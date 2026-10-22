from datetime import time
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[1] / "custom_components/tibber_ha"))
from validation import departure_readback_matches


@pytest.mark.parametrize("actual,expected,match", [
    ({"hours": 6, "minutes": 0}, time(6), True),
    ({"hours": 7, "minutes": 0}, time(6), False),
    (None, None, True),
    ({"hours": 6, "minutes": 0}, None, False),
    (None, time(6), False),
    ("No departure time", None, False),
])
def test_structured_departure_readback(actual, expected, match):
    snapshot = {"charging": {"departureTimes": [{
        "weekday": "day_of_week_friday", "time": actual
    }]}}
    assert departure_readback_matches(snapshot, {"friday": expected}) is match


def test_missing_and_duplicate_days_are_not_success():
    assert not departure_readback_matches({}, {"friday": None})
    row = {"weekday": "day_of_week_friday", "time": None}
    assert not departure_readback_matches({"charging": {"departureTimes": [row, row]}},
                                          {"friday": None})
