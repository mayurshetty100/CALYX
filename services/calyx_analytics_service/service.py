# ==============================================================================
# CALYX ANALYTICS SERVICE: BUSINESS LOGIC SERVICE LAYER
# ==============================================================================
# Concept Explanation for Beginners:
# The Analytics Service processes events and computes aggregates:
# 1. Pipeline Funnel: Tracks conversion drop-offs from application to interview to offer.
# 2. Score Histograms: Groups candidate AI match scores into statistical brackets
#    (e.g., Top Tier 85-100%, Strong 70-84%) so hiring managers can immediately
#    spot talent concentrations.
# ==============================================================================

import json
from datetime import datetime, timezone
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import func
from services.calyx_analytics_service.models import PipelineEvent, JobAnalyticsSummary
from services.calyx_analytics_service.schemas import (
    PipelineEventCreate,
    DashboardOverviewResponse,
    JobDistributionResponse,
    PipelineEventResponse,
)


class AnalyticsService:
    """
    Business logic layer for analytics aggregation and dashboard reporting.
    """

    @classmethod
    def record_pipeline_event(cls, db: Session, req: PipelineEventCreate) -> PipelineEvent:
        """
        Ingests a new lifecycle event and updates materialized summary metrics.
        """
        payload_str = json.dumps(req.metadata) if req.metadata else None
        
        event = PipelineEvent(
            event_type=req.event_type.upper().strip(),
            entity_id=req.entity_id.strip(),
            user_id=req.user_id,
            payload_json=payload_str
        )
        db.add(event)
        db.commit()
        db.refresh(event)

        # If this event contains an AI evaluation score, update job summary metrics
        if req.event_type.upper() == "AGENT_EVALUATION_COMPLETED" and req.metadata:
            score = float(req.metadata.get("score", 0.0))
            job_id = str(req.metadata.get("job_id", req.entity_id))
            cls._update_job_summary(db, job_id=job_id, new_score=score)

        return event

    @classmethod
    def _update_job_summary(cls, db: Session, job_id: str, new_score: float):
        """
        Updates incremental summary metrics for a job opening.
        """
        summary = db.query(JobAnalyticsSummary).filter(JobAnalyticsSummary.job_id == job_id).first()
        if not summary:
            summary = JobAnalyticsSummary(
                job_id=job_id,
                total_applications=1,
                average_score=new_score,
                highest_score=new_score,
                lowest_score=new_score
            )
            db.add(summary)
        else:
            # Incremental average calculation
            prev_total = summary.total_applications
            prev_sum = summary.average_score * prev_total
            new_total = prev_total + 1
            summary.total_applications = new_total
            summary.average_score = round((prev_sum + new_score) / new_total, 1)
            summary.highest_score = max(summary.highest_score, new_score)
            summary.lowest_score = min(summary.lowest_score, new_score)
        
        db.commit()

    @classmethod
    def get_dashboard_overview(cls, db: Session) -> DashboardOverviewResponse:
        """
        Generates high-level executive dashboard statistics across all jobs.
        """
        total_events = db.query(func.count(PipelineEvent.id)).scalar() or 0
        
        # Calculate status funnel counts
        funnel_counts = {
            "applications_submitted": 0,
            "agent_evaluations_completed": 0,
            "interviews_scheduled": 0,
            "offers_extended": 0,
            "candidates_rejected": 0
        }

        event_rows = db.query(PipelineEvent.event_type, func.count(PipelineEvent.id)).group_by(PipelineEvent.event_type).all()
        for ev_type, count in event_rows:
            key = ev_type.lower()
            if key in funnel_counts:
                funnel_counts[key] = count
            elif "SUBMIT" in ev_type:
                funnel_counts["applications_submitted"] += count
            elif "EVAL" in ev_type:
                funnel_counts["agent_evaluations_completed"] += count
            elif "INTERVIEW" in ev_type:
                funnel_counts["interviews_scheduled"] += count
            elif "OFFER" in ev_type:
                funnel_counts["offers_extended"] += count
            elif "REJECT" in ev_type:
                funnel_counts["candidates_rejected"] += count

        # Global average score across all job summaries
        avg_score = db.query(func.avg(JobAnalyticsSummary.average_score)).scalar() or 0.0

        # Fetch recent 5 events for timeline
        recent_events = (
            db.query(PipelineEvent)
            .order_by(PipelineEvent.created_at.desc())
            .limit(5)
            .all()
        )

        return DashboardOverviewResponse(
            total_events_recorded=total_events,
            total_applications_evaluated=funnel_counts["agent_evaluations_completed"],
            average_pipeline_score=round(float(avg_score), 1),
            status_funnel=funnel_counts,
            recent_activity=[PipelineEventResponse.model_validate(e) for e in recent_events]
        )

    @classmethod
    def get_job_distribution(cls, db: Session, job_id: str) -> JobDistributionResponse:
        """
        Computes score histogram brackets for a specific job requisition.
        """
        # Fetch all evaluation events for this job
        events = db.query(PipelineEvent).filter(
            PipelineEvent.event_type == "AGENT_EVALUATION_COMPLETED"
        ).all()

        scores: List[float] = []
        for ev in events:
            if ev.payload_json:
                data = json.loads(ev.payload_json)
                if data.get("job_id") == job_id or ev.entity_id == job_id:
                    if "score" in data:
                        scores.append(float(data["score"]))

        brackets = {
            "top_tier_85_100": 0,
            "strong_70_84": 0,
            "average_50_69": 0,
            "below_50": 0
        }

        for score in scores:
            if score >= 85.0:
                brackets["top_tier_85_100"] += 1
            elif score >= 70.0:
                brackets["strong_70_84"] += 1
            elif score >= 50.0:
                brackets["average_50_69"] += 1
            else:
                brackets["below_50"] += 1

        total = len(scores)
        avg = round(sum(scores) / total, 1) if total > 0 else 0.0
        hi = max(scores) if total > 0 else 0.0
        lo = min(scores) if total > 0 else 0.0

        return JobDistributionResponse(
            job_id=job_id,
            total_applicants=total,
            average_score=avg,
            highest_score=hi,
            lowest_score=lo,
            score_brackets=brackets
        )
