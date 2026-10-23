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
* Existing 80% automation remains enabled. Reliable Tibber-side pause/resume
  has not been identified; the minimum policy does not replace that function.
* Offline integration tests: 15 passing. Full isolated HA engine test script
  is provided but NOT executed: local Docker daemon is unavailable.

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
