"""Exercise 4: can a differenced target let gradient boosting handle the growth trend?

Trains each model on cnt - cnt_lag_1 (the day-to-day change) and adds cnt_lag_1
back to its predictions. Prints VALIDATION scores only unless --test is passed.
Does not touch reports/metrics.json.
"""
import sys

from sklearn.base import clone
from sklearn.metrics import mean_absolute_error, r2_score

from src.config import TARGET
from src.features import build_features, feature_columns
from src.ingest import load_raw
from src.train import MODELS, temporal_split

feats = build_features(load_raw())
cols = feature_columns(feats)
train, valid, test = temporal_split(feats)
evaluate_on = test if "--test" in sys.argv else valid
label = "TEST" if "--test" in sys.argv else "valid"

for name in ["ridge", "hgb"]:
    for mode in ["none", "diff"]:
        model = clone(MODELS[name])
        offset_train = train["cnt_lag_1"] if mode == "diff" else 0
        offset_eval = evaluate_on["cnt_lag_1"] if mode == "diff" else 0
        model.fit(train[cols], train[TARGET] - offset_train)
        pred = model.predict(evaluate_on[cols]) + offset_eval
        r2 = r2_score(evaluate_on[TARGET], pred)
        mae = mean_absolute_error(evaluate_on[TARGET], pred)
        print(f"{name:6s} target={mode:4s}  {label} R2 {r2:7.4f}  MAE {mae:7.1f}")
