# TibberHA

Experimental Home Assistant custom integration backed by
[TibberLib](https://github.com/twids/TibberLib).

## Current state: explicit actions and event-driven blueprint

Config flow signs into the Tibber app API, lists account vehicles/homes and reads
the selected vehicle's server-provided settings. Login, vehicle discovery and
snapshot reads have been verified in real HA with the user's offline Zoe.
Setup itself never changes charging settings.

Actions: `inspect_settings`, `set_vehicle_soc`, `set_departure_time` and
`clear_departure_times`. Write actions read back the result and report failure
if it does not match. An error can mean a write already happened; do not blindly
retry. Time keys and encoding are supported by authenticated reads and APK code.
All three write actions have passed live read-back verification: setting a weekday
06:00 departure, clearing it, and reporting the actual 99% SoC.

Install as a HACS custom repository (Integration), restart HA, then add
**TibberHA (experimental)** through Devices & services. Enter credentials only
in HA, never in a GitHub issue or chat. The library is pinned to a Git commit;
network access to GitHub/PyPI is needed for dependency installation.

## Responsibility split

* TibberLib: app API transport, authentication, reads and verified writes.
* TibberHA: config flow, account/vehicle selection, health and HA actions.
* HA automation: existing Renault sensors, home/connection checks, next weekday
  06:00 and one-shot SoC policy. Tibber owns all price scheduling.

At plug-in below 40%, report `real_soc + 60` once and set the next weekday
departure at 06:00. At the first 40% crossing, remove that departure and report
real SoC once. At plug-in at/above 40%, report real SoC and remove the managed
departure. No periodic SoC writes. Existing Renault and Easee entities are reused.

The blueprint is in `blueprints/automation/zoe_weekday_minimum.yaml`. It uses one
`input_text` helper (max 255 characters) to persist session state. It does not
start a new session merely because HA restarted. Interrupted/failed writes require
review instead of automatic resubmission. An overdue minimum produces a notice,
not HA price control or a charge-now override.

Blueprint validation, action read-back unit tests and actual HA transition tests
are separate checks. The blueprint and session helper are installed in live HA.
Physical plug-in/40% transitions and morning outcomes
are not yet verified. Review the older 80% stop automation before relying on this
policy. Weekdays currently mean Monday-Friday, without public-holiday exclusions.

## Tests

`python -m pip install -r requirements-test.txt`

`python -m pytest -q tests`

Offline tests cover structured read-back and the actual blueprint's date template,
including Friday/weekend selection and both Stockholm DST changes. They do not
prove cloud charging behavior.
