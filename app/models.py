from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class Severity(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"


class AssignmentAction(str, Enum):
    AUTO_ASSIGN = "auto_assign"
    SUGGEST = "suggest"
    FALLBACK = "fallback"


class Incident(BaseModel):
    sys_id: str
    number: str
    short_description: str
    description: str = ""
    category: str = ""
    caller_id: str = ""
    department: str = ""
    state: str = ""
    priority: str = ""
    sys_created_on: str = ""


class ClassificationResult(BaseModel):
    category: str
    subcategory: str
    severity: Severity
    assigned_team: str
    confidence_score: float = Field(ge=0.0, le=1.0)
    summary: str


class SimilarIncident(BaseModel):
    id: str
    description: str
    assigned_team: str
    resolution_notes: str
    similarity_score: float


class DecisionResult(BaseModel):
    action: AssignmentAction
    classification: ClassificationResult
    similar_incidents: list[SimilarIncident]
    assignment_group: str
    assigned_to: Optional[str] = None
    priority: str
    worklog_entry: str


class FeedbackRecord(BaseModel):
    incident_sys_id: str
    original_assignment: str
    corrected_assignment: Optional[str] = None
    was_correct: bool
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    notes: str = ""
