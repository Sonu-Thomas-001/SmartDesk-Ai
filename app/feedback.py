import json
import os
from datetime import datetime

import structlog

from app.models import FeedbackRecord

logger = structlog.get_logger(__name__)

FEEDBACK_FILE = "feedback_log.jsonl"


class FeedbackStore:
    """Persists feedback records for continuous improvement."""

    def __init__(self, filepath: str = FEEDBACK_FILE) -> None:
        self._filepath = filepath

    def record(self, feedback: FeedbackRecord) -> None:
        """Append a feedback record."""
        with open(self._filepath, "a", encoding="utf-8") as f:
            f.write(feedback.model_dump_json() + "\n")
        logger.info(
            "feedback_recorded",
            incident=feedback.incident_sys_id,
            correct=feedback.was_correct,
        )

    def get_corrections(self, limit: int = 100) -> list[FeedbackRecord]:
        """Retrieve recent incorrect assignments for retraining."""
        records: list[FeedbackRecord] = []
        if not os.path.exists(self._filepath):
            return records
        with open(self._filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                rec = FeedbackRecord(**json.loads(line))
                if not rec.was_correct:
                    records.append(rec)
        return records[-limit:]

    def accuracy_stats(self) -> dict:
        """Compute accuracy statistics."""
        total = correct = 0
        if not os.path.exists(self._filepath):
            return {"total": 0, "correct": 0, "accuracy": 0.0}
        with open(self._filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                rec = FeedbackRecord(**json.loads(line))
                total += 1
                if rec.was_correct:
                    correct += 1
        return {
            "total": total,
            "correct": correct,
            "accuracy": round(correct / total, 4) if total > 0 else 0.0,
        }
