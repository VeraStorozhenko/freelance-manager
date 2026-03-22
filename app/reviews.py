from typing import List

from app.dashboard import build_dashboard
from app.schemas import QuickAction, RescuePlanResponse, ReviewResponse


def default_quick_actions() -> List[QuickAction]:
    return [
        QuickAction(
            id="today-focus",
            title="Today focus",
            prompt="What needs attention today?",
            description="Get the most urgent priorities and the next action for each.",
        ),
        QuickAction(
            id="weekly-review",
            title="Weekly review",
            prompt="Write my weekly review based on current projects.",
            description="Summarize wins, risks, and next steps for the week.",
        ),
        QuickAction(
            id="client-follow-up",
            title="Client follow-up",
            prompt="Draft a professional follow-up for the most urgent client project.",
            description="Generate a short client-facing update for the riskiest project.",
        ),
        QuickAction(
            id="project-rescue",
            title="Project rescue",
            prompt="Build a rescue plan for my riskiest project.",
            description="Explain the risk, the recovery steps, and the client-safe update.",
        ),
    ]


def build_weekly_review(projects: list[dict]) -> ReviewResponse:
    dashboard = build_dashboard(projects)
    healthy_projects = [
        insight.project.name
        for insight in dashboard.projects
        if insight.risk_score == 0
    ]
    wins = healthy_projects[:3] or ["No project is fully healthy yet, but the portfolio is active."]

    risky_projects = dashboard.at_risk_projects[:3]
    risks = [
        f"{insight.project.name}: {insight.risks[0].reason}"
        for insight in risky_projects
    ] or ["No critical delivery risks detected this week."]

    next_steps = [
        insight.suggested_action for insight in dashboard.projects[:3]
    ] or ["Review priorities and capture the next milestone in Notion."]

    summary = (
        f"You are tracking {dashboard.summary.total_projects} projects, with "
        f"{dashboard.summary.urgent_count} urgent and "
        f"{dashboard.summary.at_risk_count} at-risk project(s)."
    )

    return ReviewResponse(
        title="Weekly Portfolio Review",
        summary=summary,
        wins=wins,
        risks=risks,
        next_steps=next_steps,
    )


def build_rescue_plan(projects: list[dict], project_id: str) -> RescuePlanResponse:
    dashboard = build_dashboard(projects)
    insight = next(
        (item for item in dashboard.projects if item.project.id == project_id),
        None,
    )
    if not insight:
        raise ValueError("Project not found")

    project = insight.project
    top_risks = [risk.reason for risk in insight.risks if risk.label != "Healthy"] or [
        "No critical risk is active, but the project can still benefit from tighter execution."
    ]

    internal_plan = [
        f"Reconfirm the next deliverable for {project.name} and reduce scope drift.",
        "Create a short checkpoint note in Notion with the current blocker or pressure point.",
        "Send a proactive update before the client has to ask for status.",
    ]
    if insight.risk_score >= 4:
        internal_plan.insert(
            0,
            "Re-sequence work for the next 24 hours so the risky milestone moves first.",
        )

    client_update = (
        f"Hi {project.client}, I reviewed {project.name} and identified the main delivery risk: "
        f"{top_risks[0]} I am already adjusting the plan so the next milestone stays clear and "
        "I will send a concrete progress update after the next work block."
    )

    headline = (
        "Project Rescue Mode: immediate intervention recommended"
        if insight.risk_score >= 4
        else "Project Rescue Mode: tighten execution now"
    )
    summary = (
        f"{project.name} has a risk score of {insight.risk_score}. "
        f"The key issue is: {top_risks[0]}"
    )

    return RescuePlanResponse(
        project_id=project.id,
        project_name=project.name,
        headline=headline,
        summary=summary,
        risks=top_risks,
        internal_plan=internal_plan,
        client_update=client_update,
        immediate_action=insight.suggested_action,
    )
