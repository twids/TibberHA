# Deployment status — 2026-10-22

## Update — 2026-10-23

* Version 0.2.0 (commit `6658a0e`) is installed through HACS and HA Core restarted.
* User completed login and selected Renault. Authenticated reads work.
* Setting Friday 06:00 and clearing it passed structured live read-back.
* Reporting actual Renault SoC 99% passed live read-back (`verified: true`).
* Smart charging was read as enabled; all departure times were empty.
* Imported `twids/zoe_weekday_minimum.yaml` and created/enabled **Zoe – Tibber
  minst 40 procent vardag 06**, config ID `1792723425772`.
* Inputs: `sensor.batteri`, `binary_sensor.kontakt`, `device_tracker.plats`,
  `sensor.tibberha_renault_settings`, `input_text.zoe_tibber_session` (max 255).
* A manual run with idle state performed no writes. A deliberate one-time
  initialization of the already connected 99% car cleared departures, reported
  real SoC, and reached `{"deadline": null, "phase": "complete"}`. The live
  trace confirms service responses propagate through the blueprint's branches.
* Existing 80% automation was subsequently verified **disabled** in HA's
  automation editor. The earlier report that it remained enabled was incorrect.
  Reliable Tibber-side pause/resume
  has not been identified; the minimum policy does not replace that function.
* Offline integration tests: 15 passing; library tests: 24 passing.
* Isolated actual HA 2026.10.2 engine test passed in GitHub Actions run
  [39921065027](https://github.com/twids/TibberHA/actions/runs/39921065027).
  Network was disabled, Tibber services simulated. Verified plug-in below 40,
  no repeated SoC writes below threshold, clearing/reporting once at 40,
  plug-in above 40, unavailable-to-on not creating a session, and schedule
  failure preventing SoC writes and automatic retries. Startup with idle state
  also performed no writes. This is engine evidence, not a physical charging test.

Still required: physical plug-in below 40%, threshold crossing at 40%, restart
recovery/failure scenarios and an observed weekday morning outcome. Read-back
does not guarantee Tibber's charging plan or Grid Rewards participation.

The older deployment notes below are retained as history, not current status.

Verified in the authenticated Home Assistant UI:

* HACS custom repository `twids/TibberHA` was added.
* Commit `6ec1da0` was downloaded to `/config/custom_components/tibber_ha`.
* HACS created a restart repair specifically for this component.
* HA Core was restarted through that repair. The UI returned successfully.
* Add integration finds **TibberHA (experimental)**.
* Its config flow loads and displays the read-only app account login form.

The form is left open for the user. No Tibber credentials have been entered by
the agent and no authenticated Tibber account reads or writes are verified yet.
No charging automation was changed. The final departure/SoC workflow remains
incomplete pending live API evidence and transition/outcome tests.

Library unit/protocol tests: 17 passing. Integration syntax compiles; successful
config-flow loading in real HA proves imports and dependency resolution, not
successful login, coordinator setup or the final charging policy.

Shared infrastructure documentation update was attempted but rejected by the
local filesystem (bad file descriptor). The existing document remained readable
and its original contents were verified intact. These deployment facts are
preserved here for later synchronization.

## Recovery fix — 2026-10-23

The recorded incident was not caused by late home location. CSV history (UTC
converted to Europe/Stockholm) showed TibberHA unavailable at 16:30:23,
SoC 84% at 16:35:28, home at 16:35:31, plug-in at 16:41:29 and TibberHA
connected again at 16:45:24. The helper stayed idle through that interval.
HA logged `Error fetching tibber_ha data: Vehicle discovery failed`.
Similar unavailable intervals lasted until the next 15-minute poll. Token
expiry is a hypothesis; the old library suppressed the underlying cause.

Version 0.2.1 changes the coordinator to renew authentication after two hours
and retry a failed read once with fresh authentication. It never retries a
mutation automatically. The blueprint records awaiting_input if TibberHA,
SoC or home confirmation is missing at plug-in and observes TibberHA recovery.
A completed session does not write again on ordinary settings polls.

Validation: 16 offline tests pass. The isolated HA 2026.10.2 engine passed all
eight scenarios, including unavailable-at-plug-in/recovery exactly once and
late home confirmation. Services were simulated and network disabled.
Production files were backed up locally under ignored work/live-backup-20261023
and updated through Studio Code Server. Configuration validation passed.
The library dependency remains pinned to 519a9e8; improved library diagnostics
are a separate unpublished change and are not installed by this HA hotfix.
GitHub connector write access returned HTTP 403; remote publication is pending.
