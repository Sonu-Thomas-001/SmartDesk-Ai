import structlog

from app.config import settings
from app.models import (
    AssignmentAction,
    ClassificationResult,
    DecisionResult,
    Incident,
    SimilarIncident,
)

logger = structlog.get_logger(__name__)

# Severity → ServiceNow priority mapping
SEVERITY_PRIORITY_MAP = {
    "Critical": "1",
    "High": "2",
    "Medium": "3",
    "Low": "4",
}

FALLBACK_QUEUE = "Service Desk"


class DecisionEngine:
    """Determines assignment action based on confidence thresholds."""

    def __init__(
        self,
        auto_threshold: float | None = None,
        suggest_threshold: float | None = None,
    ) -> None:
        self.auto_threshold = auto_threshold or settings.auto_assign_threshold
        self.suggest_threshold = suggest_threshold or settings.suggest_threshold

    def decide(
        self,
        incident: Incident,
        classification: ClassificationResult,
        similar_incidents: list[SimilarIncident],
    ) -> DecisionResult:
        score = classification.confidence_score

        # Determine action
        if score >= self.auto_threshold:
            action = AssignmentAction.AUTO_ASSIGN
            assignment_group = classification.assigned_team
        elif score >= self.suggest_threshold:
            action = AssignmentAction.SUGGEST
            assignment_group = classification.assigned_team
        else:
            action = AssignmentAction.FALLBACK
            assignment_group = FALLBACK_QUEUE

        # Cross-validate with similar incidents when available
        if similar_incidents and action != AssignmentAction.FALLBACK:
            top_teams = [si.assigned_team for si in similar_incidents[:3] if si.similarity_score > 0.7]
            if top_teams:
                from collections import Counter
                most_common_team = Counter(top_teams).most_common(1)[0][0]
                if most_common_team != classification.assigned_team:
                    # Reduce confidence when LLM and historical data disagree
                    logger.warning(
                        "team_mismatch",
                        llm_team=classification.assigned_team,
                        historical_team=most_common_team,
                    )
                    if score < 0.9:
                        action = AssignmentAction.SUGGEST
                        assignment_group = most_common_team

        priority = SEVERITY_PRIORITY_MAP.get(classification.severity.value, "3")
        worklog = self._build_worklog(classification, similar_incidents, action)

        result = DecisionResult(
            action=action,
            classification=classification,
            similar_incidents=similar_incidents,
            assignment_group=assignment_group,
            priority=priority,
            worklog_entry=worklog,
        )

        logger.info(
            "decision_made",
            incident=incident.number,
            action=action.value,
            team=assignment_group,
            confidence=score,
        )
        return result

    @staticmethod
    def _build_worklog(
        classification: ClassificationResult,
        similar_incidents: list[SimilarIncident],
        action: AssignmentAction,
    ) -> str:
        lines = [
            "═══ SmartDesk AI Analysis ═══",
            "",
            f"Category: {classification.category}",
            f"Subcategory: {classification.subcategory}",
            f"Severity: {classification.severity.value}",
            f"Confidence Score: {classification.confidence_score:.0%}",
            "",
            f"Summary: {classification.summary}",
            "",
            "Action Taken:",
        ]

        if action == AssignmentAction.AUTO_ASSIGN:
            lines.append(
                f"  → Auto-assigned to {classification.assigned_team} "
                f"(confidence ≥ {classification.confidence_score:.0%})"
            )
        elif action == AssignmentAction.SUGGEST:
            lines.append(
                f"  → Suggested assignment: {classification.assigned_team} "
                f"(requires approval)"
            )
        else:
            lines.append("  → Routed to fallback queue (low confidence)")

        if similar_incidents:
            lines.append("")
            lines.append("Similar Historical Incidents:")
            for si in similar_incidents[:3]:
                lines.append(
                    f"  • [{si.similarity_score:.0%}] {si.id} — Team: {si.assigned_team}"
                )

        return "\n".join(lines)
