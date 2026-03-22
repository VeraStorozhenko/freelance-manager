import { useEffect, useState, useTransition } from "react";

const API_BASE = `${window.location.protocol}//${window.location.hostname}:8000`;

async function fetchJson(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    credentials: "include",
    ...options,
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.detail || "Request failed");
  }
  return data;
}

function StatCard({ label, value, tone = "neutral" }) {
  return (
    <article className={`stat-card stat-card--${tone}`}>
      <p className="eyebrow">{label}</p>
      <strong>{value}</strong>
    </article>
  );
}

function RiskBadge({ severity, label }) {
  return <span className={`risk-badge risk-badge--${severity}`}>{label}</span>;
}

function DemoBanner() {
  return (
    <section className="demo-banner">
      <p className="eyebrow">Demo mode</p>
      <p>
        Notion live data is unavailable, so the app is using seeded workspace data.
        You can still create projects, log hours, save follow-up notes, and run Rescue Mode.
      </p>
    </section>
  );
}

function MCPBanner({ connected, onConnect, onDisconnect }) {
  return (
    <section className="demo-banner demo-banner--mcp">
      <div className="mcp-banner__copy">
        <p className="eyebrow">Notion MCP</p>
        <p>
          {connected
            ? "Official Notion MCP is connected. Copilot can now use live MCP tools from your workspace."
            : "Connect the official Notion MCP server to make the copilot use real MCP tools instead of only local project context."}
        </p>
      </div>
      <button
        type="button"
        className="ghost-button"
        onClick={connected ? onDisconnect : onConnect}
      >
        {connected ? "Disconnect MCP" : "Connect Notion MCP"}
      </button>
    </section>
  );
}

function OnboardingPanel({ onSelectPrompt, onOpenRescue }) {
  const steps = [
    "Open the urgent attention column to see deadline and budget risk.",
    "Click a quick action to generate a daily focus or weekly review.",
    "Run Project Rescue Mode on a risky project to show recovery planning.",
  ];
  const promptExamples = [
    "What needs attention today?",
    "Write my weekly review based on current projects.",
    "Build a rescue plan for my riskiest project.",
  ];

  return (
    <section className="panel panel--walkthrough">
      <div className="panel__heading panel__heading--split">
        <div>
          <p className="eyebrow">Demo walkthrough</p>
          <h2>Quick walkthrough</h2>
        </div>
        <button type="button" className="ghost-button" onClick={onOpenRescue}>
          Open Rescue Mode
        </button>
      </div>
      <ol className="onboarding-list">
        {steps.map((step) => (
          <li key={step}>{step}</li>
        ))}
      </ol>
      <div className="prompt-gallery">
        {promptExamples.map((prompt) => (
          <button
            key={prompt}
            type="button"
            className="prompt-chip"
            onClick={() => onSelectPrompt(prompt)}
          >
            {prompt}
          </button>
        ))}
      </div>
    </section>
  );
}

function QuickActions({ actions, onSelect }) {
  return (
    <div className="quick-actions">
      {actions.map((action) => (
        <button
          key={action.id}
          className="quick-actions__button"
          type="button"
          onClick={() => onSelect(action.prompt)}
        >
          <span>{action.title}</span>
          <small>{action.description}</small>
        </button>
      ))}
    </div>
  );
}

function CreateProjectPanel({ onCreated }) {
  const [form, setForm] = useState({
    client: "",
    budget: "1200",
    deadline: "",
    hours: "0",
  });
  const [message, setMessage] = useState("");
  const [isSaving, startSaving] = useTransition();

  function updateField(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  function handleSubmit(event) {
    event.preventDefault();
    setMessage("");

    startSaving(async () => {
      try {
        await fetchJson("/projects", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            client: form.client,
            budget: Number(form.budget),
            deadline: form.deadline,
            hours: Number(form.hours),
          }),
        });
        setMessage("Project created successfully.");
        setForm({ client: "", budget: "1200", deadline: "", hours: "0" });
        onCreated();
      } catch (error) {
        setMessage(error.message);
      }
    });
  }

  return (
    <section className="panel panel--create">
      <div className="panel__heading">
        <p className="eyebrow">Create project</p>
        <h2>Add a new client engagement</h2>
      </div>
      <form className="create-project-form" onSubmit={handleSubmit}>
        <input
          value={form.client}
          onChange={(event) => updateField("client", event.target.value)}
          placeholder="Client or project name"
          required
        />
        <input
          type="number"
          min="0"
          step="50"
          value={form.budget}
          onChange={(event) => updateField("budget", event.target.value)}
          placeholder="Budget"
          required
        />
        <input
          type="date"
          value={form.deadline}
          onChange={(event) => updateField("deadline", event.target.value)}
          required
        />
        <input
          type="number"
          min="0"
          step="0.25"
          value={form.hours}
          onChange={(event) => updateField("hours", event.target.value)}
          placeholder="Estimated hours"
        />
        <button type="submit" disabled={isSaving}>
          {isSaving ? "Creating..." : "Create project"}
        </button>
      </form>
      {message ? <p className="project-actions__message">{message}</p> : null}
    </section>
  );
}

function RescueModeDrawer({ dashboard, rescuePlan, isOpen, onClose, onRun, isPending }) {
  const selectedProjectId =
    rescuePlan?.project_id || dashboard?.at_risk_projects?.[0]?.project.id || "";

  useEffect(() => {
    if (!isOpen) return undefined;

    function handleKeydown(event) {
      if (event.key === "Escape") {
        onClose();
      }
    }

    window.addEventListener("keydown", handleKeydown);
    return () => window.removeEventListener("keydown", handleKeydown);
  }, [isOpen, onClose]);

  if (!isOpen) {
    return null;
  }

  return (
    <div className="rescue-overlay" onClick={onClose}>
      <aside className="rescue-drawer" onClick={(event) => event.stopPropagation()}>
        <div className="rescue-drawer__header">
          <div>
            <p className="eyebrow">Project Rescue Mode</p>
            <h2>Detect. Explain. Recover.</h2>
          </div>
          <button type="button" className="rescue-drawer__close" onClick={onClose}>
            Close
          </button>
        </div>

        {dashboard?.at_risk_projects?.length ? (
          <select
            className="rescue-panel__select"
            value={selectedProjectId}
            onChange={(event) => onRun(event.target.value)}
          >
            {dashboard.at_risk_projects.map((insight) => (
              <option key={insight.project.id} value={insight.project.id}>
                {insight.project.name}
              </option>
            ))}
          </select>
        ) : null}

        {rescuePlan ? (
          <>
            <p className="rescue-panel__headline">{rescuePlan.headline}</p>
            <p className="review-summary">{rescuePlan.summary}</p>
            <div className="review-grid">
              <article className="review-card">
                <p className="eyebrow">Risks</p>
                <ul>
                  {rescuePlan.risks.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </article>
              <article className="review-card">
                <p className="eyebrow">Internal plan</p>
                <ul>
                  {rescuePlan.internal_plan.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </article>
              <article className="review-card">
                <p className="eyebrow">Immediate action</p>
                <p className="review-summary">{rescuePlan.immediate_action}</p>
                <p className="eyebrow rescue-panel__client-label">Client-safe update</p>
                <p className="review-summary">{rescuePlan.client_update}</p>
              </article>
            </div>
          </>
        ) : (
          <p className="empty-state">No at-risk project available for rescue mode.</p>
        )}

        {selectedProjectId ? (
          <button
            type="button"
            className="ghost-button"
            onClick={() => onRun(selectedProjectId)}
            disabled={isPending}
          >
            {isPending ? "Rebuilding plan..." : "Rebuild rescue plan"}
          </button>
        ) : null}
      </aside>
    </div>
  );
}

function ProjectActionBar({ insight, onProjectUpdated, onOpenRescue }) {
  const [hours, setHours] = useState("1");
  const [draft, setDraft] = useState("");
  const [message, setMessage] = useState("");
  const [isGeneratingDraft, startGeneratingDraft] = useTransition();
  const [isSaving, startSaving] = useTransition();
  const [isLogging, startLogging] = useTransition();

  function generateDraft() {
    setMessage("");
    startGeneratingDraft(async () => {
      try {
        const data = await fetchJson(`/copilot/follow-up/${insight.project.id}`);
        setDraft(data.draft);
      } catch (error) {
        setMessage(error.message);
      }
    });
  }

  function saveDraft() {
    if (!draft.trim()) {
      setMessage("Generate or write a follow-up first.");
      return;
    }

    startSaving(async () => {
      try {
        await fetchJson("/follow-up-note", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            project_id: insight.project.id,
            content: draft,
          }),
        });
        setMessage("Follow-up note saved to Notion.");
        onProjectUpdated();
      } catch (error) {
        setMessage(error.message);
      }
    });
  }

  function logHours() {
    startLogging(async () => {
      try {
        await fetchJson("/log-hours", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            project_id: insight.project.id,
            hours: Number(hours),
          }),
        });
        setMessage("Hours logged successfully.");
        onProjectUpdated();
      } catch (error) {
        setMessage(error.message);
      }
    });
  }

  return (
    <div className="project-actions">
      <div className="project-actions__row">
        <button type="button" className="ghost-button" onClick={generateDraft} disabled={isGeneratingDraft}>
          {isGeneratingDraft ? "Generating..." : "Generate follow-up"}
        </button>
        <button type="button" className="ghost-button" onClick={() => onOpenRescue(insight.project.id)}>
          Open rescue
        </button>
        <button type="button" className="ghost-button" onClick={saveDraft} disabled={isSaving}>
          {isSaving ? "Saving..." : "Save note"}
        </button>
      </div>
      <textarea
        className="project-actions__draft"
        value={draft}
        onChange={(event) => setDraft(event.target.value)}
        placeholder="Follow-up draft will appear here"
        rows={5}
      />
      <div className="project-actions__row">
        <input
          className="project-actions__hours"
          type="number"
          min="0.25"
          step="0.25"
          value={hours}
          onChange={(event) => setHours(event.target.value)}
        />
        <button type="button" className="ghost-button" onClick={logHours} disabled={isLogging}>
          {isLogging ? "Logging..." : "Log hours"}
        </button>
      </div>
      {message ? <p className="project-actions__message">{message}</p> : null}
    </div>
  );
}

function ProjectCard({ insight, onProjectUpdated, onOpenRescue }) {
  const { project, risks, suggested_action: suggestedAction } = insight;

  return (
    <article className="project-card">
      <div className="project-card__header">
        <div>
          <p className="eyebrow">{project.client}</p>
          <h3>{project.name}</h3>
        </div>
        <p className="project-card__score">Risk {insight.risk_score}</p>
      </div>
      <div className="project-card__meta">
        <span>Budget EUR {project.budget}</span>
        <span>{project.hours}h logged</span>
        <span>Deadline {project.deadline || "Not set"}</span>
      </div>
      <div className="project-card__risks">
        {risks.map((risk) => (
          <RiskBadge
            key={`${project.id}-${risk.label}`}
            severity={risk.severity}
            label={risk.label}
          />
        ))}
      </div>
      <p className="project-card__action">{suggestedAction}</p>
      <ProjectActionBar
        insight={insight}
        onProjectUpdated={onProjectUpdated}
        onOpenRescue={onOpenRescue}
      />
    </article>
  );
}

function WeeklyReviewPanel({ review, onRefresh, isRefreshing }) {
  const [exportMessage, setExportMessage] = useState("");

  async function exportReview() {
    const text = [
      review.title,
      "",
      review.summary,
      "",
      `Wins: ${review.wins.join("; ")}`,
      `Risks: ${review.risks.join("; ")}`,
      `Next steps: ${review.next_steps.join("; ")}`,
    ].join("\n");

    try {
      await navigator.clipboard.writeText(text);
      setExportMessage("Weekly review copied to clipboard.");
    } catch (error) {
      setExportMessage("Clipboard access failed. Copy the review manually.");
    }
  }

  return (
    <section className="panel">
      <div className="panel__heading panel__heading--split">
        <div>
          <p className="eyebrow">Weekly review</p>
          <h2>{review.title}</h2>
        </div>
        <div className="button-cluster">
          <button type="button" className="ghost-button" onClick={exportReview}>
            Export review
          </button>
          <button type="button" className="ghost-button" onClick={onRefresh} disabled={isRefreshing}>
            {isRefreshing ? "Refreshing..." : "Refresh review"}
          </button>
        </div>
      </div>
      <p className="review-summary">{review.summary}</p>
      <div className="review-grid">
        <article className="review-card">
          <p className="eyebrow">Wins</p>
          <ul>
            {review.wins.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </article>
        <article className="review-card">
          <p className="eyebrow">Risks</p>
          <ul>
            {review.risks.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </article>
        <article className="review-card">
          <p className="eyebrow">Next steps</p>
          <ul>
            {review.next_steps.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </article>
      </div>
      {exportMessage ? <p className="project-actions__message">{exportMessage}</p> : null}
    </section>
  );
}

function CopilotPanel({ actions, onResponse, initialPrompt, onPromptChange }) {
  const [message, setMessage] = useState("What needs attention today?");
  const [response, setResponse] = useState("");
  const [error, setError] = useState("");
  const [isPending, startTransition] = useTransition();

  useEffect(() => {
    setMessage(initialPrompt);
  }, [initialPrompt]);

  function submitPrompt(prompt = message) {
    setError("");
    setMessage(prompt);
    onPromptChange(prompt);

    startTransition(async () => {
      try {
        const data = await fetchJson("/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message: prompt }),
        });
        setResponse(data.response);
        onResponse(data.response);
      } catch (err) {
        setError(err.message);
      }
    });
  }

  function handleSubmit(event) {
    event.preventDefault();
    submitPrompt(message);
  }

  return (
    <section className="copilot-panel">
      <div className="copilot-panel__intro">
        <p className="eyebrow">Copilot</p>
        <h2>Ask for priorities, reviews, and client follow-ups</h2>
        <p>
          Start with a quick action, then refine the prompt in your own words.
          in your own words.
        </p>
      </div>
      <QuickActions actions={actions} onSelect={submitPrompt} />
      <form className="copilot-form" onSubmit={handleSubmit}>
        <textarea
          value={message}
          onChange={(event) => {
            setMessage(event.target.value);
            onPromptChange(event.target.value);
          }}
          rows={4}
        />
        <button type="submit" disabled={isPending}>
          {isPending ? "Thinking..." : "Ask Copilot"}
        </button>
      </form>
      {response ? <pre className="copilot-response">{response}</pre> : null}
      {error ? <p className="copilot-error">{error}</p> : null}
    </section>
  );
}

export default function App() {
  const [dashboard, setDashboard] = useState(null);
  const [actions, setActions] = useState([]);
  const [review, setReview] = useState(null);
  const [rescuePlan, setRescuePlan] = useState(null);
  const [isRescueOpen, setIsRescueOpen] = useState(false);
  const [appConfig, setAppConfig] = useState({ demo_mode: false });
  const [lastCopilotReply, setLastCopilotReply] = useState("");
  const [selectedPrompt, setSelectedPrompt] = useState("What needs attention today?");
  const [error, setError] = useState("");
  const [isRefreshingReview, startReviewRefresh] = useTransition();
  const [isLoadingRescue, startRescueTransition] = useTransition();

  async function loadDashboard() {
    const data = await fetchJson("/dashboard");
    setDashboard(data);
    return data;
  }

  async function loadWeeklyReview() {
    const data = await fetchJson("/copilot/weekly-review");
    setReview(data);
  }

  async function openRescue(projectId) {
    const targetProjectId = projectId || dashboard?.at_risk_projects?.[0]?.project.id;
    if (!targetProjectId) return;
    setIsRescueOpen(true);

    startRescueTransition(async () => {
      try {
        const data = await fetchJson(`/copilot/rescue/${targetProjectId}`);
        setRescuePlan(data);
      } catch (err) {
        setError(err.message);
      }
    });
  }

  async function refreshAll() {
    const [configData, dashboardData, actionData, reviewData] = await Promise.all([
      fetchJson("/app-config"),
      fetchJson("/dashboard"),
      fetchJson("/copilot/actions"),
      fetchJson("/copilot/weekly-review"),
    ]);
    setAppConfig(configData);
    setDashboard(dashboardData);
    setActions(actionData);
    setReview(reviewData);
  }

  function connectMCP() {
    window.location.href = `${API_BASE}/mcp/connect`;
  }

  async function disconnectMCP() {
    try {
      await fetchJson("/mcp/disconnect", { method: "POST" });
      await refreshAll();
    } catch (err) {
      setError(err.message);
    }
  }

  useEffect(() => {
    let ignore = false;

    async function loadPage() {
      try {
        const [configData, dashboardData, actionData, reviewData] = await Promise.all([
          fetchJson("/app-config"),
          fetchJson("/dashboard"),
          fetchJson("/copilot/actions"),
          fetchJson("/copilot/weekly-review"),
        ]);

        if (!ignore) {
          setAppConfig(configData);
          setDashboard(dashboardData);
          setActions(actionData);
          setReview(reviewData);
        }
      } catch (err) {
        if (!ignore) {
          setError(err.message);
        }
      }
    }

    loadPage();
    return () => {
      ignore = true;
    };
  }, []);

  function refreshReview() {
    startReviewRefresh(async () => {
      try {
        await Promise.all([loadDashboard(), loadWeeklyReview()]);
      } catch (err) {
        setError(err.message);
      }
    });
  }

  if (error) {
    return (
      <main className="app-shell">
        <section className="hero">
          <p className="eyebrow">Freelance OS</p>
          <h1>Dashboard is unavailable</h1>
          <p>{error}</p>
        </section>
      </main>
    );
  }

  if (!dashboard || !review) {
    return (
      <main className="app-shell">
        <section className="hero">
          <p className="eyebrow">Freelance OS</p>
          <h1>Loading workspace signal...</h1>
        </section>
      </main>
    );
  }

  return (
    <>
      <main className="app-shell">
        {appConfig.demo_mode ? <DemoBanner /> : null}
        <MCPBanner
          connected={appConfig.mcp_connected}
          onConnect={connectMCP}
          onDisconnect={disconnectMCP}
        />

        <section className="hero">
          <div>
            <p className="eyebrow">Freelance OS Copilot</p>
            <h1>Run your freelance work like an operating system.</h1>
            <p className="hero__body">
              Read deadlines, surface risk, and turn your Notion workspace into a
              daily command center for delivery.
            </p>
            {lastCopilotReply ? (
              <div className="hero__inline-note">
                <p className="eyebrow">Copilot output</p>
                <p>{lastCopilotReply}</p>
              </div>
            ) : null}
          </div>
          <div className="hero__stats">
            <StatCard label="Urgent projects" value={dashboard.summary.urgent_count} tone="alert" />
            <StatCard label="At risk" value={dashboard.summary.at_risk_count} tone="warning" />
            <StatCard label="Hours logged" value={dashboard.summary.total_hours} tone="neutral" />
            <StatCard label="Budget tracked" value={`EUR ${dashboard.summary.total_budget}`} tone="success" />
          </div>
        </section>

        <OnboardingPanel
          onSelectPrompt={setSelectedPrompt}
          onOpenRescue={() => openRescue()}
        />

        <section className="section-grid">
          <section className="panel">
            <div className="panel__heading">
              <p className="eyebrow">Today</p>
              <h2>Urgent attention</h2>
            </div>
            <div className="project-list">
              {dashboard.urgent_projects.length ? (
                dashboard.urgent_projects.map((insight) => (
                  <ProjectCard
                    key={insight.project.id}
                    insight={insight}
                    onProjectUpdated={refreshAll}
                    onOpenRescue={openRescue}
                  />
                ))
              ) : (
                <p className="empty-state">No urgent projects right now.</p>
              )}
            </div>
          </section>

          <CopilotPanel
            actions={actions}
            onResponse={setLastCopilotReply}
            initialPrompt={selectedPrompt}
            onPromptChange={setSelectedPrompt}
          />
        </section>

        <section className="section-grid">
          <CreateProjectPanel onCreated={refreshAll} />
          <WeeklyReviewPanel
            review={review}
            onRefresh={refreshReview}
            isRefreshing={isRefreshingReview}
          />
        </section>

        <section className="panel panel--full">
          <div className="panel__heading panel__heading--split">
            <div>
              <p className="eyebrow">Portfolio</p>
              <h2>Project health overview</h2>
            </div>
            <button type="button" className="ghost-button" onClick={refreshAll}>
              Refresh workspace
            </button>
          </div>
          <div className="project-list project-list--grid">
            {dashboard.projects.map((insight) => (
              <ProjectCard
                key={insight.project.id}
                insight={insight}
                onProjectUpdated={refreshAll}
                onOpenRescue={openRescue}
              />
            ))}
          </div>
        </section>
      </main>

      <RescueModeDrawer
        dashboard={dashboard}
        rescuePlan={rescuePlan}
        isOpen={isRescueOpen}
        onClose={() => setIsRescueOpen(false)}
        onRun={openRescue}
        isPending={isLoadingRescue}
      />
    </>
  );
}
