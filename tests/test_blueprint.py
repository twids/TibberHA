from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from jinja2 import Environment, StrictUndefined
import pytest
import yaml


class BlueprintLoader(yaml.SafeLoader):
    pass


BlueprintLoader.add_constructor("!input", lambda loader, node: loader.construct_scalar(node))
BLUEPRINT = yaml.load(
    (Path(__file__).parents[1] / "blueprints/automation/zoe_weekday_minimum.yaml").read_text(),
    Loader=BlueprintLoader,
)


@pytest.mark.parametrize("now_text,expected", [
    ("2026-10-22T22:00:00", "2026-10-23T06:00:00+02:00"),
    ("2026-10-23T05:59:00", "2026-10-23T06:00:00+02:00"),
    ("2026-10-23T06:00:00", "2026-10-26T06:00:00+01:00"),
    ("2026-10-24T12:00:00", "2026-10-26T06:00:00+01:00"),
    ("2026-10-25T12:00:00", "2026-10-26T06:00:00+01:00"),
    ("2026-03-27T22:00:00", "2026-03-30T06:00:00+02:00"),
    ("2026-10-26T01:00:00", "2026-10-26T06:00:00+01:00"),
])
def test_real_blueprint_next_weekday_template_across_dst(now_text, expected):
    now = datetime.fromisoformat(now_text).replace(tzinfo=ZoneInfo("Europe/Stockholm"))
    env = Environment(undefined=StrictUndefined)
    result = env.from_string(BLUEPRINT["variables"]["next_departure"]).render(
        now=lambda: now,
        today_at=lambda text: now.replace(hour=int(text[:2]), minute=int(text[3:]),
                                          second=0, microsecond=0),
        timedelta=timedelta,
    ).strip()
    assert result == expected


def test_automation_is_event_driven_and_has_no_charge_now_or_periodic_soc_trigger():
    assert {t["id"] for t in BLUEPRINT["triggers"]} == {
        "plug", "unplug", "observe", "startup", "deadline"
    }
    assert all(t["trigger"] != "time_pattern" for t in BLUEPRINT["triggers"])
