"""Pure validation shared by actions and offline tests."""
from datetime import time


def departure_readback_matches(snapshot: dict, expected: dict[str, time | None]) -> bool:
    rows = (snapshot.get("charging") or {}).get("departureTimes")
    if not isinstance(rows, list):
        return False
    observed = {}
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("weekday"), str):
            return False
        day = row["weekday"].removeprefix("day_of_week_")
        if day in observed:
            return False
        observed[day] = row.get("time")
    for day, value in expected.items():
        if day not in observed:
            return False
        actual = observed[day]
        if value is None:
            if actual is not None:
                return False
        elif not isinstance(actual, dict) or (
            actual.get("hours"), actual.get("minutes")
        ) != (value.hour, value.minute):
            return False
    return True
