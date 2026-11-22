"""Child-process entry point for memory-isolated model training."""

import json

from train_model import train_global_model


class _StdoutLogger:
    def log(self, message):
        print(message, flush=True)


result = train_global_model(logger=_StdoutLogger())
print("TRAINING_RESULT=" + json.dumps(result, allow_nan=True, default=str), flush=True)
