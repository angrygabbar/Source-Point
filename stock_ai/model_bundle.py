"""Small joblib-safe wrapper for calibrated binary probabilities."""

import numpy as np
from prediction_features import FEATURE_COLUMNS


class CalibratedProbabilityModel:
    def __init__(self, estimator, calibrator, buy_threshold=0.60,
                 strong_buy_threshold=0.75, feature_columns=None,
                 validation_metrics=None, trained_through=None,
                 model_version="stock-ai-v3"):
        self.estimator = estimator
        self.calibrator = calibrator
        self.buy_threshold = float(buy_threshold)
        self.strong_buy_threshold = float(strong_buy_threshold)
        self.feature_columns = list(feature_columns or FEATURE_COLUMNS)
        self.validation_metrics = dict(validation_metrics or {})
        self.trained_through = trained_through
        self.model_version = str(model_version)
        self.classes_ = np.asarray([0, 1])

    def predict_proba(self, features):
        raw = self.estimator.predict_proba(features)
        classes = list(self.estimator.classes_)
        positive_index = classes.index(1)
        positive = raw[:, positive_index].reshape(-1, 1)
        calibrated = self.calibrator.predict_proba(positive)[:, 1]
        calibrated = np.clip(calibrated, 0.0, 1.0)
        return np.column_stack((1.0 - calibrated, calibrated))

    def predict(self, features):
        return (self.predict_proba(features)[:, 1] >= 0.5).astype(int)

    @property
    def feature_names_in_(self):
        return getattr(self.estimator, "feature_names_in_", None)
