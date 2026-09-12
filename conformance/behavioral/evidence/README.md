# Behavioral evidence provenance

No conclusive live profile-evaluation aggregate is currently committed. The former
`2026-08-02-01KYW5XK.json` aggregate was removed because its declared live model and
endpoint did not match its mock raw reports. It is not acceptance evidence.

The historical JSON files in this directory are diagnostic records, including
mock and deliberately failing controls. Their filenames and reported endpoints
do not establish live provenance; inspect their embedded `baseUrl` and `model`.
They must never be promoted or combined into a live aggregate by attribution alone.

A future manually dispatched evaluation uploads every diagnostic run. Only a run
with healthy discriminating controls and zero endpoint errors is eligible for
committed aggregate publication. Model noncompliance can still be conclusive.
No paid evaluation was performed during the integration repair.
