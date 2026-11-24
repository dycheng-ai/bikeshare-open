# Seeded faults

## Feature test written first (cnt_lag_2)

```
    
        >>> monotonic_index = pd.Index(list("abbc"))
        >>> monotonic_index.get_loc("b")
        slice(1, 3, None)
    
        >>> non_monotonic_index = pd.Index(list("abcb"))
        >>> non_monotonic_index.get_loc("b")
        array([False,  True, False,  True])
        """
        casted_key = self._maybe_cast_indexer(key)
        try:
            return self._engine.get_loc(casted_key)
        except KeyError as err:
            if isinstance(casted_key, slice) or (
                isinstance(casted_key, abc.Iterable)
                and any(isinstance(x, slice) for x in casted_key)
            ):
                raise InvalidIndexError(key) from err
>           raise KeyError(key) from err
E           KeyError: 'cnt_lag_2'

.venv/lib/python3.13/site-packages/pandas/core/indexes/base.py:3648: KeyError
=========================== short test summary info ============================
FAILED tests/test_leakage.py::test_cnt_lag_2_on_named_date - KeyError: 'cnt_l...
1 failed, 7 passed in 0.86s
```

## Fault (a): "casual" added to feature_columns()

### Change

```diff
diff --git a/src/features.py b/src/features.py
index 02e93ca..793c0c1 100644
--- a/src/features.py
+++ b/src/features.py
@@ -82,7 +82,7 @@ def build_features(df: pd.DataFrame) -> pd.DataFrame:
 def feature_columns(df: pd.DataFrame) -> list[str]:
     """Numeric columns that are safe to feed the model."""
     numeric = df.select_dtypes(include="number").columns
-    return [c for c in numeric if c not in FORBIDDEN]
+    return [c for c in numeric if c not in FORBIDDEN] + ["casual"]
 
 

 if __name == "__main__":
```

### Red test output

```
.......F.........                                                        [100%]
=================================== FAILURES ===================================
__________________________ test_no_forbidden_features __________________________

feats =         dteday  instant  season  ...  cnt_lag_2 cnt_lag_7   cnt_roll_7
0   2011-01-10     10.0  WINTER  ...      959.0...    1787.0  1530.142857
713 2012-12-31    731.0  WINTER  ...     1341.0     920.0  1531.428571

[714 rows x 29 columns]

    def test_no_forbidden_features(feats):
        """Guards the gate, not the data: feature_columns() excludes FORBIDDEN by
        construction, so this cannot discover a *new* leaky column. What it
        catches is someone editing feature_columns() or FORBIDDEN -- which is
        exactly the fault the Step 7 hook demonstrates."""
        cols = set(feature_columns(feats))
>       assert not (cols & FORBIDDEN), f"forbidden columns in feature set: {cols & FORBIDDEN}"
E       AssertionError: forbidden columns in feature set: {'casual'}
E       assert not ({'atemp', 'casual', 'cnt_lag_1', 'cnt_lag_2', 'cnt_lag_7', 'cnt_roll_7', ...} & {'casual', 'cnt', 'cnt_2d_bfr', 'days_since_2011', 'instant', 'registered', ...})

tests/test_leakage.py:31: AssertionError
=========================== short test summary info ============================
FAILED tests/test_leakage.py::test_no_forbidden_features - AssertionError: fo...
1 failed, 16 passed in 2.01s
```

### Hook stderr (PostToolUse)

```
Leakage tests failed after editing /Users/dylancheng/downloads/bikeshare-open/src/features.py:
feats =         dteday  instant  season  ...  cnt_lag_2 cnt_lag_7   cnt_roll_7
0   2011-01-10     10.0  WINTER  ...      959.0...    1787.0  1530.142857
713 2012-12-31    731.0  WINTER  ...     1341.0     920.0  1531.428571

[714 rows x 29 columns]

    def test_no_forbidden_features(feats):
        """Guards the gate, not the data: feature_columns() excludes FORBIDDEN by
        construction, so this cannot discover a *new* leaky column. What it
        catches is someone editing feature_columns() or FORBIDDEN -- which is
        exactly the fault the Step 7 hook demonstrates."""
        cols = set(feature_columns(feats))
>       assert not (cols & FORBIDDEN), f"forbidden columns in feature set: {cols & FORBIDDEN}"
E       AssertionError: forbidden columns in feature set: {'casual'}
E       assert not ({'atemp', 'casual', 'cnt_lag_1', 'cnt_lag_2', 'cnt_lag_7', 'cnt_roll_7', ...} & {'casual', 'cnt', 'cnt_2d_bfr', 'days_since_2011', 'instant', 'registered', ...})

tests/test_leakage.py:31: AssertionError
=========================== short test summary info ============================
FAILED tests/test_leakage.py::test_no_forbidden_features - AssertionError: fo...
1 failed, 16 passed in 0.25s
exit code: 2
```

**Fixed in 1 turn:** the agent removed the appended "casual" from feature_columns(); make test back to 17 passed.



## Fault (b): cnt_roll_7 includes today (leakage via target)

### Change

```diff
diff --git a/src/features.py b/src/features.py
index 02e93ca..a03a88d 100644
--- a/src/features.py
+++ b/src/features.py
@@ -74,7 +74,7 @@ def build_features(df: pd.DataFrame) -> pd.DataFrame:
     out["cnt_lag_1"] = out[TARGET].shift(1)
     out["cnt_lag_2"] = out[TARGET].shift(2)
     out["cnt_lag_7"] = out[TARGET].shift(LAG_WARMUP)
-    out["cnt_roll_7"] = out[TARGET].shift(1).rolling(LAG_WARMUP).mean()
+    out["cnt_roll_7"] = out[TARGET].rolling(LAG_WARMUP).mean()

     return out.dropna().reset_index(drop=True)
```

### Red test output

```
..........F......                                                        [100%]
=================================== FAILURES ===================================
_______________________ test_rolling_mean_excludes_today _______________________

feats =         dteday  instant  season  ...  cnt_lag_2 cnt_lag_7   cnt_roll_7
0   2011-01-10     10.0  WINTER  ...      959.0...    1787.0  1531.428571
713 2012-12-31    731.0  WINTER  ...     1341.0     920.0  1789.857143

[714 rows x 29 columns]

    def test_rolling_mean_excludes_today(feats):
        """cnt_roll_7 must be the mean of the 7 calendar days *before* today."""
        by_date = feats.set_index("dteday")[TARGET]
        date = feats.dteday.iloc[200]
        window = [date - pd.Timedelta(days=k) for k in range(1, 8)]
        if all(d in by_date.index for d in window):
            expected = sum(by_date[d] for d in window) / 7
>           assert feats.set_index("dteday").cnt_roll_7[date] == pytest.approx(expected)
E           assert np.float64(4389.0) == 4414.857142857143 ± 0.00441486
E             
E             comparison failed
E             Obtained: 4389.0
E             Expected: 4414.857142857143 ± 0.00441486

tests/test_leakage.py:57: AssertionError
=========================== short test summary info ============================
FAILED tests/test_leakage.py::test_rolling_mean_excludes_today - assert np.fl...
1 failed, 16 passed in 2.0s
```

### Hook stderr (PostToolUse)

```
[714 rows x 29 columns]

    def test_rolling_mean_excludes_today(feats):
        """cnt_roll_7 must be the mean of the 7 calendar days *before* today."""
        by_date = feats.set_index("dteday")[TARGET]
        date = feats.dteday.iloc[200]
        window = [date - pd.Timedelta(days=k) for k in range(1, 8)]
        if all(d in by_date.index for d in window):
            expected = sum(by_date[d] for d in window) / 7
>           assert feats.set_index("dteday").cnt_roll_7[date] == pytest.approx(expected)
E           assert np.float64(4389.0) == 4414.857142857143 ± 0.00441486
E             
E             comparison failed
E             Obtained: 4389.0
E             Expected: 4414.857142857143 ± 0.00441486

tests/test_leakage.py:57: AssertionError
==================================== short test summary info =====================================
FAILED tests/test_leakage.py::test_rolling_mean_excludes_today - assert np.fl...
1 failed, 7 passed in 0.61s
```

**Seed complete, waiting for fix.**
## Fault (b): .shift(1) deleted from cnt_roll_7

### Change

```diff
diff --git a/src/features.py b/src/features.py
index 02e93ca..a03a88d 100644
--- a/src/features.py
+++ b/src/features.py
@@ -74,7 +74,7 @@ def build_features(df: pd.DataFrame) -> pd.DataFrame:
     out["cnt_lag_1"] = out[TARGET].shift(1)
     out["cnt_lag_2"] = out[TARGET].shift(2)
     out["cnt_lag_7"] = out[TARGET].shift(LAG_WARMUP)
-    out["cnt_roll_7"] = out[TARGET].shift(1).rolling(LAG_WARMUP).mean()
+    out["cnt_roll_7"] = out[TARGET].rolling(LAG_WARMUP).mean()
 
     return out.dropna().reset_index(drop=True)
 
```

### Red test output

```

feats =         dteday  instant  season  ...  cnt_lag_2 cnt_lag_7   cnt_roll_7
0   2011-01-10     10.0  WINTER  ...      959.0...    1787.0  1531.428571
713 2012-12-31    731.0  WINTER  ...     1341.0     920.0  1789.857143

[714 rows x 29 columns]

    def test_rolling_mean_excludes_today(feats):
        """cnt_roll_7 must be the mean of the 7 calendar days *before* today."""
        by_date = feats.set_index("dteday")[TARGET]
        date = feats.dteday.iloc[200]
        window = [date - pd.Timedelta(days=k) for k in range(1, 8)]
        if all(d in by_date.index for d in window):
            expected = sum(by_date[d] for d in window) / 7
>           assert feats.set_index("dteday").cnt_roll_7[date] == pytest.approx(expected)
E           assert np.float64(4389.0) == 4414.857142857143 ± 0.00441486
E             
E             comparison failed
E             Obtained: 4389.0
E             Expected: 4414.857142857143 ± 0.00441486

tests/test_leakage.py:57: AssertionError
=========================== short test summary info ============================
FAILED tests/test_leakage.py::test_rolling_mean_excludes_today - assert np.fl...
1 failed, 16 passed in 1.87s
```

### Hook stderr (PostToolUse)

```
Leakage tests failed after editing /Users/dylancheng/downloads/bikeshare-open/src/features.py:
[714 rows x 29 columns]

    def test_rolling_mean_excludes_today(feats):
        """cnt_roll_7 must be the mean of the 7 calendar days *before* today."""
        by_date = feats.set_index("dteday")[TARGET]
        date = feats.dteday.iloc[200]
        window = [date - pd.Timedelta(days=k) for k in range(1, 8)]
        if all(d in by_date.index for d in window):
            expected = sum(by_date[d] for d in window) / 7
>           assert feats.set_index("dteday").cnt_roll_7[date] == pytest.approx(expected)
E           assert np.float64(4389.0) == 4414.857142857143 ± 0.00441486
E             
E             comparison failed
E             Obtained: 4389.0
E             Expected: 4414.857142857143 ± 0.00441486

tests/test_leakage.py:57: AssertionError
=========================== short test summary info ============================
FAILED tests/test_leakage.py::test_rolling_mean_excludes_today - assert np.fl...
1 failed, 7 passed in 0.25s
exit code: 2
```

**Fixed in 1 turn:** the agent restored .shift(1) before .rolling on cnt_roll_7; make test back to 17 passed.


## Fault: encode_weather ValueError check deleted (unknown labels → silent NaN)

### Change

```diff
diff --git a/src/features.py b/src/features.py
index 02e93ca..049bf1d 100644
--- a/src/features.py
+++ b/src/features.py
@@ -24,10 +24,6 @@ def encode_weather(series: pd.Series) -> pd.Series:
     days -- the most interesting days in the dataset -- disappear with no
     error and no warning.
     """
-    known = series.dropna()
-    unknown = set(known.unique()) - set(WEATHER_ORDER)
-    if unknown:
-        raise ValueError(f"unmapped weather labels: {sorted(unknown)}")
     return series.map(WEATHER_ORDER).astype(float)
```

### Test output (no failures despite the fault)

```
.................                                                        [100%]
17 passed in 1.85s
```

### Hook stderr (PostToolUse)

*(none - tests pass)*

**Seeded, awaiting fix.**

## Fault (c): raise removed from encode_weather

### Change

```diff
diff --git a/src/features.py b/src/features.py
index 02e93ca..049bf1d 100644
--- a/src/features.py
+++ b/src/features.py
@@ -24,10 +24,6 @@ def encode_weather(series: pd.Series) -> pd.Series:
     days -- the most interesting days in the dataset -- disappear with no
     error and no warning.
     """
-    known = series.dropna()
-    unknown = set(known.unique()) - set(WEATHER_ORDER)
-    if unknown:
-        raise ValueError(f"unmapped weather labels: {sorted(unknown)}")
     return series.map(WEATHER_ORDER).astype(float)
 
 
```

### Test output

```
.................                                                        [100%]
17 passed in 1.54s
```

### Hook output (PostToolUse)

```
exit code: 0
```

**Finding: the suite stayed green.** Every label in today's data (GOOD/MISTY/BAD) is mapped, so no existing test exercises the unknown-label path; the hook exited 0. A future file containing an unmapped label would turn those days into NaN and dropna() would delete them silently. Fixed by adding test_encode_weather_rejects_unknown_labels (below).

### With the new test: red

```
=================================== FAILURES ===================================
__________________ test_encode_weather_rejects_unknown_labels __________________

    def test_encode_weather_rejects_unknown_labels():
        """An unmapped label must fail loudly, never become a silent NaN that a
        downstream dropna() deletes (Step 5, Bug 2)."""
        from src.features import encode_weather
>       with pytest.raises(ValueError, match="unmapped weather labels"):
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E       Failed: DID NOT RAISE ValueError

tests/test_leakage.py:82: Failed
=========================== short test summary info ============================
FAILED tests/test_leakage.py::test_encode_weather_rejects_unknown_labels - Fa...
1 failed, 17 passed in 1.00s
```

### Hook output with the new test

```
>       with pytest.raises(ValueError, match="unmapped weather labels"):
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E       Failed: DID NOT RAISE ValueError

tests/test_leakage.py:82: Failed
=========================== short test summary info ============================
FAILED tests/test_leakage.py::test_encode_weather_rejects_unknown_labels - Fa...
1 failed, 8 passed in 0.25s
exit code: 0
```

Note: the "exit code: 0" above is from tail, not the hook. Run on its own, the hook exits 2 with the new test in place.

**Fixed in 1 turn:** the agent restored the unknown-label check and raise in encode_weather; make test back to 18 passed, including the new test.

## Fault (d): writing into data/raw/ from Bash

### Attempt 1: cp

Asked the agent to run, through its Bash tool: cp /tmp/fake.csv data/raw/bike_daily.csv

~~~
$ cp /tmp/fake.csv data/raw/bike_daily.csv
Not run · permission denied · rule from shared project settings
Reason: Permission to use Bash with command cp /tmp/fake.csv data/raw/bike_daily.csv has been denied.
~~~

**Finding:** the lesson expects the deny rules to bind only the Edit/Write tools, so that a Bash cp walks past them. In Claude Code 2.1.328 the Edit(./data/raw/**) rule also blocked this cp, because the harness checks recognised file-writing Bash commands against path rules. The PostToolUse hook still never ran: it matches Edit|Write only.

### Attempt 2: the same write hidden inside Python

Asked the agent to run, through its Bash tool: python -c "import shutil; shutil.copy('/tmp/fake.csv', 'data/raw/bike_daily.csv')"

The deny rules did not recognise this as a write to data/raw/. Claude Code only showed an ordinary approval prompt, and once approved the raw file was replaced. No hook ran.

~~~
c6124690d86acf2452f1edce6c08143ba110689ed0aaad695bacb4636a1e1ca1  data/raw/bike_daily.csv
     100 data/raw/bike_daily.csv
~~~

### Test output after the overwrite

~~~
ERROR tests/test_contract.py::test_beats_the_mean_baseline - ValueError: raw ...
ERROR tests/test_contract.py::test_every_raw_column_is_classified - ValueErro...
ERROR tests/test_contract.py::test_unclassified_check_can_fail - ValueError: ...
ERROR tests/test_leakage.py::test_leakage_identity_holds - ValueError: raw da...
ERROR tests/test_leakage.py::test_no_forbidden_features - ValueError: raw dat...
ERROR tests/test_leakage.py::test_lags_are_true_calendar_lags - ValueError: r...
ERROR tests/test_leakage.py::test_lag_is_not_the_target - ValueError: raw dat...
ERROR tests/test_leakage.py::test_rolling_mean_excludes_today - ValueError: r...
ERROR tests/test_leakage.py::test_cnt_lag_2_on_named_date - ValueError: raw d...
ERROR tests/test_leakage.py::test_no_missing_values - ValueError: raw data ha...
ERROR tests/test_leakage.py::test_dates_are_sorted_and_unique - ValueError: r...
ERROR tests/test_split.py::test_splits_non_empty - ValueError: raw data has o...
ERROR tests/test_split.py::test_splits_are_ordered_in_time - ValueError: raw ...
ERROR tests/test_split.py::test_no_overlapping_dates - ValueError: raw data h...
2 passed, 16 errors in 1.69s
~~~

Restored with git restore data/raw/bike_daily.csv (hash back to a6bed1577f6e4de5...).

### What catches this, and what was implemented

The PostToolUse hook cannot see this fault: it fires on Edit|Write only, and the write happened through Bash. The deny rules stopped a plain cp but not the same write inside python -c. The load_raw() shape assertion caught this crude overwrite, but only when tests are run, and it would miss a same-shape edit (728 rows with altered values). Options that would catch it: a hash check on the raw CSV (in a test or in make data); a PreToolUse hook on Bash that rejects any command mentioning data/raw/; a Stop hook that runs make test before the agent may finish; or chmod -w data/raw so the filesystem refuses the write. Implemented: test_raw_csv_is_unchanged in tests/test_contract.py, which compares the file's SHA-256 with the committed value and fails on any change, including same-shape edits.

### Hash test on a same-shape edit (one value changed)

~~~
E         + 0c233a343ad2018a1f54cc60fb44480db85e355f905da3af59b013dac803e18a

tests/test_contract.py:91: AssertionError
=========================== short test summary info ============================
FAILED tests/test_contract.py::test_raw_csv_is_unchanged - AssertionError: da...
1 failed, 6 passed in 1.72s
~~~

