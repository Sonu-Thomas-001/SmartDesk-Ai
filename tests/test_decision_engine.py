"""Unit tests for the decision engine."""

import pytest

from app.decision_engine import DecisionEngine, FALLBACK_QUEUE
from app.models import (
    AssignmentAction,
    ClassificationResult,
    Incident,
    Severity,
    SimilarIncident,
)


@pytest.fixture
def engine():
    return DecisionEngine(auto_threshold=0.8, suggest_threshold=0.5)


@pytest.fixture
def sample_incident():
    return Incident(
        sys_id="abc123",
        number="INC0001234",
        short_description="Cannot connect to VPN",
        description="User reports VPN connection failures since morning",
        category="Network",
        state="1",
    )


def _make_classification(team: str, confidence: float, severity: Severity = Severity.HIGH):
    return ClassificationResult(
        category="Network Issue",
        subcategory="VPN",
        severity=severity,
        assigned_team=team,
        confidence_score=confidence,
        summary="VPN connectivity failure",
    )


def _make_similar(team: str, score: float):
    return SimilarIncident(
        id="INC000999",
        description="VPN issue",
        assigned_team=team,
        resolution_notes="Restarted VPN gateway",
        similarity_score=score,
    )


class TestDecisionEngine:
    def test_high_confidence_auto_assigns(self, engine, sample_incident):
        classification = _make_classification("Network Team", 0.92)
        result = engine.decide(sample_incident, classification, [])
        assert result.action == AssignmentAction.AUTO_ASSIGN
        assert result.assignment_group == "Network Team"

    def test_medium_confidence_suggests(self, engine, sample_incident):
        classification = _make_classification("Network Team", 0.65)
        result = engine.decide(sample_incident, classification, [])
        assert result.action == AssignmentAction.SUGGEST
        assert result.assignment_group == "Network Team"

    def test_low_confidence_fallback(self, engine, sample_incident):
        classification = _make_classification("Network Team", 0.3)
        result = engine.decide(sample_incident, classification, [])
        assert result.action == AssignmentAction.FALLBACK
        assert result.assignment_group == FALLBACK_QUEUE

    def test_team_mismatch_reduces_to_suggest(self, engine, sample_incident):
        classification = _make_classification("App Support", 0.82)
        similar = [
            _make_similar("Network Team", 0.85),
            _make_similar("Network Team", 0.80),
            _make_similar("Network Team", 0.75),
        ]
        result = engine.decide(sample_incident, classification, similar)
        # Historical data overrides LLM when LLM confidence < 0.9
        assert result.action == AssignmentAction.SUGGEST
        assert result.assignment_group == "Network Team"

    def test_high_confidence_ignores_mismatch(self, engine, sample_incident):
        classification = _make_classification("App Support", 0.95)
        similar = [
            _make_similar("Network Team", 0.85),
            _make_similar("Network Team", 0.80),
        ]
        result = engine.decide(sample_incident, classification, similar)
        # Very high confidence → LLM wins
        assert result.action == AssignmentAction.AUTO_ASSIGN

    def test_severity_maps_to_priority(self, engine, sample_incident):
        classification = _make_classification("Security Team", 0.9, Severity.CRITICAL)
        result = engine.decide(sample_incident, classification, [])
        assert result.priority == "1"

    def test_worklog_contains_key_info(self, engine, sample_incident):
        classification = _make_classification("Network Team", 0.88)
        result = engine.decide(sample_incident, classification, [])
        assert "Network Issue" in result.worklog_entry
        assert "88%" in result.worklog_entry
        assert "Auto-assigned" in result.worklog_entry
