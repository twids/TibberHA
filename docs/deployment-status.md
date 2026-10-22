# Deployment status — 2026-10-22

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
