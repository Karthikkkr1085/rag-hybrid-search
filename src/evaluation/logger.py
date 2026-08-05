import csv
import os
from datetime import datetime


class EvaluationLogger:
    """
    Logs evaluation metrics to a CSV file.
    """

    def __init__(self):
        os.makedirs("logs", exist_ok=True)
        self.file_path = "logs/evaluation.csv"

    def log(self, metrics: dict):
        file_exists = os.path.exists(self.file_path)

        with open(self.file_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)

            if not file_exists:
                writer.writerow(["timestamp", *metrics.keys()])

            writer.writerow(
                [datetime.now().strftime("%Y-%m-%d %H:%M:%S"), *metrics.values()]
            )
