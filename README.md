# TibberHA

Experimental Home Assistant custom integration backed by
[TibberLib](https://github.com/twids/TibberLib).

## Current state: read-only discovery

Config flow signs into the Tibber app API, lists account vehicles and reads the
selected vehicle's server-provided settings. A diagnostic sensor shows setting
keys and departure times. It does not change SoC, departure times or charging.
Neither live authentication nor HA runtime loading has been verified yet.

Install as a HACS custom repository (Integration), restart HA, then add
**TibberHA (experimental)** through Devices & services. Enter credentials only
in HA, never in a GitHub issue or chat. The library is pinned to a Git commit;
network access to GitHub/PyPI is needed for dependency installation.

## Intended split

* TibberLib: app API transport, authentication, reads and verified writes.
* TibberHA: config flow, account/vehicle selection, health and HA actions.
* HA automation: existing Renault sensors, home/connection checks, next weekday
  06:00 and one-shot SoC policy. Tibber owns all price scheduling.

At plug-in below 40%, report `real_soc + 60` once and set the next weekday
departure at 06:00. At the first 40% crossing, remove that departure and report
real SoC once. At plug-in at/above 40%, report real SoC and remove the managed
departure. No periodic SoC writes. Existing Renault and Easee entities are reused.

The exact departure write/clear representation is not yet verified, so charging
automation and those actions are not shipped as if operational. Existing 80%
stop automation must be reviewed before enabling the final policy.
