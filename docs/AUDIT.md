# Audit of a teammate's repository

Repository: https://github.com/ChidiebereAgunanne/bikeshare-open (commit COMMIT_ID)
Auditor: .claude/agents/leakage-auditor.md, run through Claude Code with qwen3.5:9b via Ollama (64k context).

## How the audit was run

The first request was dispatched to a general-purpose agent instead of the leakage-auditor; its three-line "all pass" summary is not used here. On the second attempt the leakage-auditor itself ran, but in auto mode its shell commands were silently refused ("auto mode's check had no usable answer"), because auto mode's safety check cannot run through a local Ollama endpoint. It was rerun in manual permission mode, approving read-only commands, the teammate's test suite, and a retrain (python -m src.train); all edits were refused.

## Auditor output (verbatim)

Audit Results

Check 1: Target Leakage — NO ISSUES FOUND

The LEAKAGE_COLS = {"casual", "registered", "cnt"} is properly defined in config.py line 31. The feature_columns() function correctly excludes these:

def feature_columns(df: pd.DataFrame) -> list[str]:
    numeric = df.select_dtypes(include="number").columns
    return [c for c in numeric if c not in FORBIDDEN]

The lag features (cnt_lag_1, cnt_lag_7, cnt_roll_7, cnt_std_7) are properly shifted using .shift(1) before aggregation, and tests verify this:

- test_lags_are_true_calendar_lags verifies lags align with calendar days
- test_lag_is_not_the_target confirms lags differ from target
- test_rolling_mean_excludes_today checks rolling mean excludes current day

Check 2: Temporal Ordering — NO ISSUES FOUND

The temporal split is date-based (not random):
def temporal_split(df: pd.DataFrame):
    train = df[df.dteday <= TRAIN_END]      # <= 2011-12-31
    valid = df[(df.dteday > TRAIN_END) & (df.dteday <= VALID_END)]  # H1 2012
    test = df[df.dteday > VALID_END]        # H2 2012

All models are fit on train data first, then validated/tested:
model.fit(train[cols], train[TARGET])

Check 3: Calendar Gaps — NO ISSUES FOUND

The reindex_to_calendar function properly reindexes to a gap-free calendar:
def reindex_to_calendar(df: pd.DataFrame) -> pd.DataFrame:
    full = pd.date_range(df.dteday.min(), df.dteday.max(), freq="D")
    return df.set_index("dteday").reindex(full).reset_index()

Tests verify this with test_calendar_is_complete_before_lagging.

Check 4: Silent Row Loss — NO ISSUES FOUND

The only row loss is documented and bounded in the contract test. The function explicitly calculates expected losses from lag warmup periods.

Check 5: Unreported Baseline — NO ISSUES FOUND

Both baseline_mean AND baseline_persistence are defined in MODELS and reported alongside every model score:
MODELS = {
    "baseline_mean": DummyRegressor(strategy="mean"),
    "baseline_persistence": PersistenceBaseline("cnt_lag_1"),
    ...
}

---

Summary

All five checks pass. The teammate-repo implements all required safeguards:
- No target leakage (FORBIDDEN columns properly excluded)
- Correct temporal ordering (date-based split, no data leakage across train/val/test)
- Calendar gaps handled by reindex_to_calendar
- Silent row loss is bounded by lag warmup calculation
- Both mean and persistence baselines are reported alongside each model

## My verdict

I agree with the auditor: nothing in this repo changes a reported number. But I didn't want to just trust its "all pass." The auditor runs on the same small model (qwen3.5:9b) that wrote the code, so it can miss the same things. Getting it to run properly also took three tries. The first time, Claude Code used a general-purpose agent instead of the auditor. The second time, auto mode quietly blocked its commands. So I checked the main claims myself.

The leakage checks hold up: feature_columns() drops everything in FORBIDDEN, and their tests (including casual + registered == cnt) all pass. Both baselines are in their committed metrics.json: the mean baseline scores −0.93 on validation and persistence scores 0.45, the same as the starter. When the auditor retrained their models, the numbers came out exactly the same as what they committed, so their results reproduce. Their new feature, cnt_std_7, is built as out[TARGET].shift(1).rolling(7).std(ddof=1), so it shifts by one day before rolling and never sees the current day's count. It's a legitimate feature, not leakage.

One thing I noticed: the auditor's copy of reindex_to_calendar leaves out the .rename_axis("dteday") line, but that line is in their actual file. So the auditor paraphrased the code instead of quoting it. It's a small thing, but it's exactly why I didn't take its report at face value.

Overall: no leakage, a correct time-based split, both baselines reported, and reproducible results. I agree with all five findings, and none of them changes a number.
