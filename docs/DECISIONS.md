# Decisions

One line per methodological decision: what you chose, why, and what it changed.
Agents append here via the `/new-feature` skill; you append here by hand.

- Exclude `casual`, `registered`: they sum to `cnt` exactly. Leaky model R^2 1.000 -> honest ridge 0.583.
- Exclude `cnt_2d_bfr`: a shipped 2-day lag we cannot test the alignment of. Build our own lags instead.
- Exclude `instant`, `yr`, `days_since_2011`: time indexes let a tree predict a flat constant past 2011 and a linear model extrapolate a trend we have no grounds for.
- Split 2011 / H1 2012 / H2 2012 by date. Test set touched once, after all feature work.
- Report mean and persistence baselines with every score. Persistence (test R^2 0.510, MAE 840) is within 0.07 R^2 of ridge and beats it on MAE; that caveat goes in the report.

- Although claude found the correct number of rows, date range, absent calendar day, and identified casual and registered as reasons for leakage, it didn't output the weather column, didn't flag cnt_2d_bfr, and actually flagged cnt itself.
- Asked to "write" the leakage tests, the agent rewrote the starter's working tests, removed the calendar-lag and rolling-mean checks, and made the forbidden-column test skippable. Reverted to the starter. Decision: never ask the agent to write files that already exist.
- Added cnt_lag_2 (count from 2 calendar days earlier; known at prediction time, built and tested by us unlike cnt_2d_bfr). Validation R² ridge 0.6475 → 0.6453 (−0.002), hgb 0.2185 → 0.2481 (+0.030). Decided to keep it because it doesn't really change ridge and improves hgb marginally.