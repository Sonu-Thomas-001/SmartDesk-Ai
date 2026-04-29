import atexit
from datetime import datetime, timezone

import structlog
from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask, jsonify, render_template, request

from app.agent import ClassificationAgent
from app.config import settings
from app.decision_engine import DecisionEngine
from app.embedding_engine import EmbeddingEngine
from app.feedback import FeedbackStore
from app.logging_config import setup_logging
from app.models import AssignmentAction, FeedbackRecord, Incident
from app.servicenow_client import ServiceNowClient

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Shared state
# ---------------------------------------------------------------------------
snow_client: ServiceNowClient | None = None
embedding_engine: EmbeddingEngine | None = None
agent: ClassificationAgent | None = None
decision_engine: DecisionEngine | None = None
feedback_store: FeedbackStore | None = None
scheduler: BackgroundScheduler | None = None
last_poll_time: str | None = None

# Stores recent processing results for the dashboard
recent_results: list[dict] = []
# Stores created-but-not-yet-assigned incidents
created_incidents: list[dict] = []
# Track sys_ids already assigned so each ticket is only assigned once
assigned_sys_ids: set[str] = set()
MAX_RECENT = 50


# ---------------------------------------------------------------------------
# Orchestration logic
# ---------------------------------------------------------------------------

def process_incident(incident: Incident) -> dict:
    """Full pipeline: classify → search → decide → assign."""
    global recent_results

    # Prevent double-assignment
    if incident.sys_id in assigned_sys_ids:
        logger.warning("already_assigned", number=incident.number)
        return {"error": "already_assigned", "incident_number": incident.number}

    # 1. Search similar historical incidents
    query = f"{incident.short_description} {incident.description}"
    similar = embedding_engine.search_similar(query, top_k=5)

    # 2. Classify with LLM agent
    classification = agent.classify(incident, similar)

    # 3. Decision engine
    decision = decision_engine.decide(incident, classification, similar)

    # 4. Execute action on ServiceNow
    if decision.action == AssignmentAction.AUTO_ASSIGN:
        snow_client.assign_incident(
            sys_id=incident.sys_id,
            assignment_group=decision.assignment_group,
            assigned_to=decision.assigned_to,
            priority=decision.priority,
        )
        snow_client.add_worklog(incident.sys_id, decision.worklog_entry)
    elif decision.action == AssignmentAction.SUGGEST:
        snow_client.add_worklog(incident.sys_id, decision.worklog_entry)
    else:
        snow_client.add_worklog(incident.sys_id, decision.worklog_entry)

    # 5. Store this incident in the knowledge base
    embedding_engine.store_incident(
        incident_id=incident.number,
        description=query,
        assigned_team=decision.assignment_group,
    )

    # Mark as assigned
    assigned_sys_ids.add(incident.sys_id)

    # Remove from created_incidents list
    created_incidents[:] = [c for c in created_incidents if c["sys_id"] != incident.sys_id]

    result = {
        "incident_number": incident.number,
        "sys_id": incident.sys_id,
        "short_description": incident.short_description,
        "action": decision.action.value,
        "category": classification.category,
        "subcategory": classification.subcategory,
        "severity": classification.severity.value,
        "assigned_team": decision.assignment_group,
        "confidence": classification.confidence_score,
        "summary": classification.summary,
        "similar_count": len(similar),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    recent_results.insert(0, result)
    recent_results = recent_results[:MAX_RECENT]

    logger.info("incident_assigned", number=incident.number, team=decision.assignment_group)
    return result


def poll_new_incidents() -> None:
    """Scheduled job: poll ServiceNow for new incidents."""
    global last_poll_time
    try:
        incidents = snow_client.get_new_incidents(last_check=last_poll_time)
        last_poll_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        for inc in incidents:
            try:
                process_incident(inc)
            except Exception:
                logger.exception("process_incident_error", incident=inc.number)
    except Exception:
        logger.exception("poll_error")


# ---------------------------------------------------------------------------
# Flask app factory
# ---------------------------------------------------------------------------

def create_app() -> Flask:
    global snow_client, embedding_engine, agent, decision_engine, feedback_store, scheduler

    setup_logging(settings.log_level)
    logger.info("starting_smartdesk_ai")

    application = Flask(
        __name__,
        static_folder="../static",
        template_folder="../templates",
    )

    # Initialize services
    snow_client = ServiceNowClient()
    embedding_engine = EmbeddingEngine()
    agent = ClassificationAgent()
    decision_engine = DecisionEngine()
    feedback_store = FeedbackStore()

    # Start background polling scheduler
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        poll_new_incidents,
        "interval",
        seconds=settings.polling_interval_seconds,
        id="incident_poller",
    )
    scheduler.start()
    atexit.register(lambda: scheduler.shutdown(wait=False))
    logger.info("scheduler_started", interval=settings.polling_interval_seconds)

    # ------------------------------------------------------------------
    # Routes
    # ------------------------------------------------------------------

    @application.route("/")
    def dashboard():
        return render_template("dashboard.html")

    @application.route("/api/health")
    def health():
        return jsonify({
            "status": "healthy",
            "knowledge_base_size": embedding_engine.collection_count() if embedding_engine else 0,
            "polling_interval": settings.polling_interval_seconds,
        })

    @application.route("/api/recent")
    def get_recent():
        return jsonify({"results": recent_results, "created": created_incidents})

    @application.route("/api/stats")
    def get_stats():
        accuracy = feedback_store.accuracy_stats() if feedback_store else {}
        return jsonify({
            "knowledge_base_size": embedding_engine.collection_count() if embedding_engine else 0,
            "recent_processed": len(recent_results),
            "accuracy": accuracy,
        })

    @application.route("/api/webhook", methods=["POST"])
    def webhook_receiver():
        """Receive incident data from a ServiceNow Business Rule / webhook."""
        payload = request.get_json(force=True)
        if not payload or "sys_id" not in payload:
            return jsonify({"error": "sys_id is required"}), 422
        incident = Incident(**payload)
        result = process_incident(incident)
        return jsonify({"status": "processed", "result": result})

    @application.route("/api/process", methods=["POST"])
    def manual_process():
        """Manually trigger processing for a specific incident."""
        payload = request.get_json(force=True)
        sys_id = payload.get("sys_id")
        if not sys_id:
            return jsonify({"error": "sys_id is required"}), 422
        incident = snow_client.get_incident(sys_id)
        result = process_incident(incident)
        return jsonify({"status": "processed", "result": result})

    @application.route("/api/feedback", methods=["POST"])
    def submit_feedback():
        """Submit feedback on an AI assignment decision."""
        payload = request.get_json(force=True)
        required = ["incident_sys_id", "original_assignment", "was_correct"]
        missing = [f for f in required if f not in payload]
        if missing:
            return jsonify({"error": f"Missing fields: {missing}"}), 422

        record = FeedbackRecord(**payload)
        feedback_store.record(record)

        # If corrected, update the embedding knowledge base
        if not payload.get("was_correct") and payload.get("corrected_assignment"):
            embedding_engine.store_incident(
                incident_id=f"feedback_{payload['incident_sys_id']}",
                description=f"Corrected assignment for {payload['incident_sys_id']}",
                assigned_team=payload["corrected_assignment"],
                resolution_notes=payload.get("notes", ""),
            )

        return jsonify({"status": "recorded"})

    @application.route("/api/create-incident", methods=["POST"])
    def create_incident_endpoint():
        """Auto-generate a unique dummy incident via LLM and create it in ServiceNow."""
        # LLM generates a unique realistic incident
        structured = agent.generate_incident()

        snow_payload = {
            "short_description": structured.get("short_description", "Generated incident"),
            "description": structured.get("description", ""),
            "category": structured.get("category", ""),
            "urgency": structured.get("urgency", "2"),
            "impact": structured.get("impact", "2"),
        }

        result = snow_client.create_incident(snow_payload)

        # Store in created (unassigned) list
        created_entry = {
            "sys_id": result.get("sys_id"),
            "number": result.get("number"),
            "short_description": snow_payload["short_description"],
            "description": snow_payload["description"],
            "category": structured.get("category", ""),
            "urgency": snow_payload["urgency"],
            "impact": snow_payload["impact"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        created_incidents.insert(0, created_entry)

        logger.info("incident_created", number=result.get("number"))
        return jsonify({"status": "created", **created_entry})

    @application.route("/api/assign-incident", methods=["POST"])
    def assign_incident_endpoint():
        """Trigger agentic classification + assignment for a single created incident."""
        payload = request.get_json(force=True)
        sys_id = payload.get("sys_id")
        if not sys_id:
            return jsonify({"error": "sys_id is required"}), 422

        if sys_id in assigned_sys_ids:
            return jsonify({"error": "Incident already assigned"}), 409

        incident = snow_client.get_incident(sys_id)
        result = process_incident(incident)

        if "error" in result:
            return jsonify(result), 409

        return jsonify({"status": "assigned", "result": result})

    @application.route("/api/poll-now", methods=["POST"])
    def trigger_poll():
        """Manually trigger a poll cycle."""
        poll_new_incidents()
        return jsonify({"status": "poll_complete", "results_count": len(recent_results)})

    return application


app = create_app()
