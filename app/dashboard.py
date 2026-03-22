from datetime import date, datetime
from typing import Dict, List

from app.schemas import (
    DashboardResponse,
    DashboardSummary,
    ProjectInsight,
    ProjectRisk,
    ProjectSummary,
)


def _days_until(deadline: str) -> int:
    deadline_date = datetime.strptime(deadline, "%Y-%m-%d").date()
    return (deadline_date - date.today()).days


def _risk_for_project(project: Dict) -> ProjectInsight:
    risks: List[ProjectRisk] = []
    risk_score = 0

    deadline = project.get("deadline")
    if deadline:
        days_left = _days_until(deadline)
        if days_left < 0:
            risks.append(
                ProjectRisk(
                    label="Overdue",
                    severity="high",
                    reason="The deadline has already passed.",
                )
            )
            risk_score += 4
        elif days_left <= 3:
            risks.append(
                ProjectRisk(
                    label="Deadline soon",
                    severity="high",
                    reason=f"The deadline is in {days_left} day(s).",
                )
            )
            risk_score += 3
        elif days_left <= 7:
            risks.append(
                ProjectRisk(
                    label="Deadline this week",
                    severity="medium",
                    reason=f"The deadline is in {days_left} day(s).",
                )
            )
            risk_score += 2

    hours = float(project.get("hours") or 0)
    budget = float(project.get("budget") or 0)
    expected_hours = max(budget / 100, 1) if budget else 0
    if expected_hours and hours > expected_hours:
        risks.append(
            ProjectRisk(
                label="Budget pressure",
                severity="medium",
                reason=(
                    f"Tracked hours ({hours:.1f}) are above the expected range "
                    f"for a {budget:.0f} EUR project."
                ),
            )
        )
        risk_score += 2

    status = str(project.get("status") or "").lower()
    if status in {"blocked", "stuck"}:
        risks.append(
            ProjectRisk(
                label="Blocked",
                severity="high",
                reason="The project is already marked as blocked.",
            )
        )
        risk_score += 3

    if not risks:
        risks.append(
            ProjectRisk(
                label="Healthy",
                severity="low",
                reason="No obvious deadline, budget, or status risks were detected.",
            )
        )

    suggested_action = (
        "Send a client update and confirm the next milestone."
        if risk_score >= 4
        else "Review the next deliverable and keep momentum."
    )

    summary = ProjectSummary(**project)
    return ProjectInsight(
        project=summary,
        risk_score=risk_score,
        risks=risks,
        suggested_action=suggested_action,
    )


def build_dashboard(projects: List[Dict]) -> DashboardResponse:
    insights = [_risk_for_project(project) for project in projects]
    urgent_projects = [
        insight
        for insight in insights
        if any(risk.severity == "high" for risk in insight.risks)
    ]
    at_risk_projects = [insight for insight in insights if insight.risk_score >= 2]

    summary = DashboardSummary(
        total_projects=len(insights),
        active_projects=sum(
            1 for insight in insights if insight.project.status.lower() == "active"
        ),
        total_budget=sum(insight.project.budget for insight in insights),
        total_hours=sum(insight.project.hours for insight in insights),
        urgent_count=len(urgent_projects),
        at_risk_count=len(at_risk_projects),
    )

    sorted_projects = sorted(
        insights,
        key=lambda insight: (
            -insight.risk_score,
            insight.project.deadline or "9999-12-31",
            insight.project.name.lower(),
        ),
    )

    return DashboardResponse(
        summary=summary,
        urgent_projects=urgent_projects,
        at_risk_projects=at_risk_projects,
        projects=sorted_projects,
    )
