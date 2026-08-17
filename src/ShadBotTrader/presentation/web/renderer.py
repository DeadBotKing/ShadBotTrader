"""HTML rendering for the dashboard (Phase 19, section 8).

A View only renders. It receives a finished ``DashboardView`` and turns
it into markup — no queries, no calculations, no domain access.

Everything is inlined (CSS, SVG, no scripts, no fonts, no CDN) so the
page renders identically in a sandboxed preview, a saved file, or a
browser with no network.
"""

from __future__ import annotations

import html
from typing import Dict, List, Optional, Sequence

from ShadBotTrader.presentation.commands.commands import (
    CommandDescriptor,
    CommandKind,
    CommandResult,
)
from ShadBotTrader.presentation.viewmodels.models import (
    CandidateView,
    CashPoint,
    DashboardView,
    DecisionView,
    ExecutionView,
    PortfolioView,
    SessionView,
)

_STYLES = """
:root {
  --bg: #0e1117; --panel: #161b22; --border: #262d38;
  --text: #e6edf3; --muted: #8b949e;
  --positive: #3fb950; --negative: #f85149; --warning: #d29922;
  --accent: #58a6ff;
}
* { box-sizing: border-box; }
body {
  margin: 0; padding: 24px;
  background: var(--bg); color: var(--text);
  font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, monospace;
  font-size: 13px; line-height: 1.5;
}
header { margin-bottom: 20px; border-bottom: 1px solid var(--border); padding-bottom: 14px; }
h1 { margin: 0 0 4px; font-size: 18px; letter-spacing: .5px; }
h2 { margin: 0 0 12px; font-size: 13px; text-transform: uppercase;
     letter-spacing: 1px; color: var(--muted); font-weight: 600; }
.sub { color: var(--muted); font-size: 12px; }
.grid { display: grid; gap: 16px; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); }
.panel { background: var(--panel); border: 1px solid var(--border);
         border-radius: 8px; padding: 16px; overflow-x: auto; }
.panel.wide { grid-column: 1 / -1; }
.metrics { display: grid; gap: 12px; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); }
.metric { background: var(--bg); border: 1px solid var(--border);
          border-radius: 6px; padding: 12px; }
.metric .label { color: var(--muted); font-size: 11px; text-transform: uppercase;
                 letter-spacing: .5px; margin-bottom: 6px; }
.metric .value { font-size: 20px; font-weight: 600; }
table { width: 100%; border-collapse: collapse; font-size: 12px; }
th { text-align: left; color: var(--muted); font-weight: 600; padding: 6px 10px 6px 0;
     border-bottom: 1px solid var(--border); text-transform: uppercase;
     font-size: 10px; letter-spacing: .5px; white-space: nowrap; }
td { padding: 6px 10px 6px 0; border-bottom: 1px solid rgba(38,45,56,.5); white-space: nowrap; }
tr:last-child td { border-bottom: none; }
.positive { color: var(--positive); }
.negative { color: var(--negative); }
.warning  { color: var(--warning); }
.neutral  { color: var(--muted); }
.accent   { color: var(--accent); }
.badge { display: inline-block; padding: 1px 8px; border-radius: 10px;
         font-size: 11px; border: 1px solid currentColor; }
.empty { color: var(--muted); font-style: italic; padding: 12px 0; }
.bar-row { display: flex; align-items: center; gap: 10px; margin-bottom: 6px; }
.bar-label { width: 190px; color: var(--muted); font-size: 11px; }
.bar-track { flex: 1; height: 8px; background: var(--bg);
             border-radius: 4px; overflow: hidden; }
.bar-fill { height: 100%; background: var(--negative); }
.bar-value { width: 34px; text-align: right; font-size: 11px; }
footer { margin-top: 22px; padding-top: 12px; border-top: 1px solid var(--border);
         color: var(--muted); font-size: 11px; }
code { background: var(--bg); padding: 1px 5px; border-radius: 3px; font-size: 11px; }
a { color: var(--accent); }
.actions { display: grid; gap: 12px; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); }
.action { background: var(--bg); border: 1px solid var(--border);
          border-radius: 6px; padding: 14px; display: flex; flex-direction: column; }
.action h3 { margin: 0 0 6px; font-size: 13px; }
.action p { margin: 0 0 10px; color: var(--muted); font-size: 11px; flex: 1; }
.action .inputs { display: grid; gap: 6px; margin-bottom: 10px; }
.action label { display: grid; grid-template-columns: 92px 1fr; align-items: center;
                gap: 6px; font-size: 11px; color: var(--muted); }
.action input { background: var(--panel); border: 1px solid var(--border);
                color: var(--text); border-radius: 4px; padding: 5px 7px;
                font-family: inherit; font-size: 11px; width: 100%; }
button { background: var(--accent); color: #04101f; border: 0; border-radius: 5px;
         padding: 8px 12px; font-family: inherit; font-size: 12px; font-weight: 600;
         cursor: pointer; width: 100%; }
button:hover { filter: brightness(1.1); }
button:disabled { background: var(--border); color: var(--muted); cursor: not-allowed; }
.slow { color: var(--warning); font-size: 10px; margin-top: 6px; }
.banner { border-radius: 6px; padding: 12px 14px; margin-bottom: 16px;
          border: 1px solid currentColor; }
.banner .head { font-weight: 600; margin-bottom: 4px; }
.banner pre { margin: 8px 0 0; padding: 8px; background: var(--bg);
              border-radius: 4px; color: var(--text); font-size: 11px;
              white-space: pre-wrap; overflow-x: auto; }
.busy { background: rgba(210,153,34,.12); }
"""


def _e(value: object) -> str:
    """Escape any value for safe HTML output."""
    return html.escape(str(value))


def _table(headers: Sequence[str], rows: Sequence[Sequence[str]], empty: str) -> str:
    if not rows:
        return f'<p class="empty">{_e(empty)}</p>'
    head = "".join(f"<th>{_e(name)}</th>" for name in headers)
    body = "".join("<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>" for row in rows)
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def _metric(label: str, value: str, tone: str = "") -> str:
    css = f' class="value {tone}"' if tone else ' class="value"'
    return (
        f'<div class="metric"><div class="label">{_e(label)}</div>'
        f"<div{css}>{_e(value)}</div></div>"
    )


def _tag(text: str, tone: str) -> str:
    return f'<span class="badge {tone}">{_e(text)}</span>'


# ------------------------------------------------------------------ panels --
def render_portfolio(portfolio: Optional[PortfolioView]) -> str:
    if portfolio is None:
        return (
            '<section class="panel wide"><h2>Portfolio</h2>'
            '<p class="empty">No session recorded yet.</p></section>'
        )

    metrics = "".join(
        [
            _metric("Net cash flow", f"{portfolio.cash} {portfolio.currency}"),
            _metric("Realised PnL", portfolio.realized_pnl, portfolio.realized_tone),
            _metric("Fees", portfolio.total_fees),
            _metric("Net realised", portfolio.net_realized, portfolio.net_tone),
            _metric("Open positions", str(portfolio.open_positions)),
        ]
    )

    rows = [
        [
            _e(position.symbol),
            _tag(position.side, position.side_tone),
            _e(position.quantity),
            _e(position.average_price),
            f'<span class="{position.realized_tone}">{_e(position.realized_pnl)}</span>',
            _e(position.fees),
        ]
        for position in portfolio.positions
    ]

    return f"""<section class="panel wide">
  <h2>Portfolio — session {_e(portfolio.session_id)}</h2>
  <div class="metrics">{metrics}</div>
  <div style="margin-top:16px">
    {_table(
        ["Symbol", "Side", "Quantity", "Avg price", "Realised", "Fees"],
        rows,
        "No positions recorded.",
    )}
  </div>
</section>"""


def render_decisions(decisions: List[DecisionView]) -> str:
    rows = [
        [
            _e(item.symbol),
            _e(item.decision_type),
            _e(item.confidence),
            f'<span class="{item.risk_tone}">{_e(item.risk_verdict)}</span>',
            f'<span class="neutral">{_e(item.rejection)}</span>',
            _e(item.recorded_at),
        ]
        for item in decisions
    ]
    return f"""<section class="panel wide">
  <h2>Decision audit trail</h2>
  {_table(
      ["Symbol", "Decision", "Confidence", "Risk gate", "Rejection", "Recorded"],
      rows,
      "No decisions recorded.",
  )}
</section>"""


def render_executions(executions: List[ExecutionView]) -> str:
    rows = [
        [
            _e(item.symbol),
            _e(item.side),
            f'<span class="{item.status_tone}">{_e(item.status)}</span>',
            _e(item.filled_quantity),
            _e(item.average_price),
            _e(item.recorded_at),
        ]
        for item in executions
    ]
    return f"""<section class="panel wide">
  <h2>Execution history</h2>
  {_table(
      ["Symbol", "Side", "Status", "Filled", "Avg price", "Recorded"],
      rows,
      "No executions recorded.",
  )}
</section>"""


def render_candidates(candidates: List[CandidateView]) -> str:
    rows = [
        [
            f'<span class="{item.status_tone}">{_e(item.status)}</span>',
            f"<code>{_e(item.configuration)}</code>",
            _e(item.in_sample),
            _e(item.out_of_sample),
            _e(item.overfit_gap),
            f'<span class="neutral">{_e(item.rejection)}</span>',
        ]
        for item in candidates
    ]
    note = (
        '<p class="sub" style="margin-top:10px">'
        "Ranking uses the out-of-sample column only. A large gap between "
        "in-sample and out-of-sample is the signature of overfitting.</p>"
    )
    return f"""<section class="panel wide">
  <h2>Learning memory</h2>
  {_table(
      ["Status", "Configuration", "In-sample", "Out-of-sample", "Gap", "Rejection"],
      rows,
      "No optimisation candidates remembered yet.",
  )}
  {note if candidates else ""}
</section>"""


def render_sessions(sessions: List[SessionView]) -> str:
    rows = [
        [
            f'<span class="accent">{_e(item.session_id)}</span>',
            str(item.decisions),
            str(item.approved),
            _e(item.approval_rate),
            _e(item.started),
        ]
        for item in sessions
    ]
    return f"""<section class="panel">
  <h2>Sessions</h2>
  {_table(
      ["Session", "Decisions", "Approved", "Rate", "Started"],
      rows,
      "No sessions recorded.",
  )}
</section>"""


def render_rejections(counts: Dict[str, int]) -> str:
    if not counts:
        return (
            '<section class="panel"><h2>Why trades were refused</h2>'
            '<p class="empty">Nothing was refused.</p></section>'
        )
    peak = max(counts.values())
    bars = "".join(
        f'<div class="bar-row"><div class="bar-label">{_e(reason)}</div>'
        f'<div class="bar-track"><div class="bar-fill" '
        f'style="width:{total / peak * 100:.0f}%"></div></div>'
        f'<div class="bar-value">{total}</div></div>'
        for reason, total in sorted(counts.items(), key=lambda item: -item[1])
    )
    return f'<section class="panel"><h2>Why trades were refused</h2>{bars}</section>'


def render_system(view: DashboardView) -> str:
    system = view.system
    rows = [[_e(name), str(count)] for name, count in sorted(system.populated_tables.items())]
    return f"""<section class="panel">
  <h2>Database</h2>
  <div class="metrics">
    {_metric("Schema", f"v{system.schema_version}")}
    {_metric("Rows", str(system.total_rows))}
  </div>
  <p class="sub" style="margin:12px 0 8px">
    <code>{_e(system.database_path)}</code><br>
    environment {_e(system.environment)} · updated {_e(system.updated_at)}
  </p>
  {_table(["Table", "Rows"], rows, "Database is empty.")}
</section>"""


def render_equity_chart(points: Sequence[CashPoint]) -> str:
    """An inline SVG of realised cash over time.

    Drawn only when there are at least two points — a single dot is not
    a curve, and pretending otherwise would be misleading.
    """
    if len(points) < 2:
        return (
            '<section class="panel wide"><h2>Realised cash flow</h2>'
            '<p class="empty">Not enough recorded transactions to draw a curve '
            "(at least two are needed).</p></section>"
        )

    values = [point.value for point in points]
    lowest, highest = min(values), max(values)
    span = (highest - lowest) or 1.0
    width, height, pad = 820, 200, 24

    coordinates = []
    for index, value in enumerate(values):
        x = pad + index * (width - 2 * pad) / max(len(values) - 1, 1)
        y = height - pad - ((value - lowest) / span) * (height - 2 * pad)
        coordinates.append(f"{x:.1f},{y:.1f}")

    line = " ".join(coordinates)
    area = f"{pad},{height - pad} {line} {width - pad},{height - pad}"
    colour = "#3fb950" if values[-1] >= values[0] else "#f85149"

    return f"""<section class="panel wide">
  <h2>Realised cash flow</h2>
  <svg viewBox="0 0 {width} {height}" width="100%" height="{height}"
       role="img" aria-label="Realised cash flow">
    <polygon points="{area}" fill="{colour}" opacity="0.12"/>
    <polyline points="{line}" fill="none" stroke="{colour}" stroke-width="2"/>
    <line x1="{pad}" y1="{height - pad}" x2="{width - pad}" y2="{height - pad}"
          stroke="#262d38" stroke-width="1"/>
  </svg>
  <p class="sub">{len(values)} transaction(s) ·
     from {values[0]:,.2f} to {values[-1]:,.2f} ·
     range {lowest:,.2f} … {highest:,.2f}</p>
  <p class="sub">Realised movements only: per-bar unrealised marks are not
     stored, so they are not shown rather than estimated.</p>
</section>"""


# ------------------------------------------------------------------ actions --
def render_actions(
    descriptors: Sequence[CommandDescriptor],
    busy: Optional[CommandKind] = None,
    busy_seconds: float = 0.0,
) -> str:
    """The command panel: one form per operation (Phase 19 §3, §12).

    Each form POSTs to /run. The browser sends the user's intent; the
    server turns it into a Command and hands it to the bus. No logic
    runs here — this is markup.
    """
    cards = []
    for descriptor in descriptors:
        inputs = "".join(
            f"<label>{_e(field.label)}"
            f'<input type="{"number" if field.kind == "number" else "text"}" '
            f'name="{_e(field.name)}" value="{_e(field.default)}" '
            f'{"step=any" if field.kind == "number" else ""}></label>'
            for field in descriptor.fields
        )
        disabled = " disabled" if busy is not None else ""
        note = (
            '<div class="slow">takes a while — the page stays responsive</div>'
            if descriptor.slow
            else ""
        )
        cards.append(f"""<form class="action" method="post" action="/run">
  <input type="hidden" name="command" value="{_e(descriptor.action)}">
  <h3>{_e(descriptor.label)}</h3>
  <p>{_e(descriptor.description)}</p>
  {f'<div class="inputs">{inputs}</div>' if inputs else ""}
  <button type="submit"{disabled}>Run</button>
  {note}
</form>""")

    banner = ""
    if busy is not None:
        banner = (
            f'<div class="banner busy warning"><div class="head">'
            f"Running: {_e(busy.value)}</div>"
            f"<div>{busy_seconds:.0f}s elapsed — reload the page to check progress. "
            f"Buttons are disabled until it finishes.</div></div>"
        )

    return f"""<section class="panel wide">
  <h2>Actions</h2>
  {banner}
  <div class="actions">{"".join(cards)}</div>
</section>"""


def render_result(result: Optional[CommandResult]) -> str:
    """Show the outcome of the command that was just dispatched."""
    if result is None:
        return ""
    detail = f"<pre>{_e(result.detail)}</pre>" if result.detail else ""
    lines = f"<pre>{_e(chr(10).join(result.lines))}</pre>" if result.lines else ""
    took = f" · {result.duration_seconds:.1f}s" if result.duration_seconds else ""
    return f"""<div class="banner {result.tone}">
  <div class="head">{_e(result.status.value.upper())}: {_e(result.kind.value)}{took}</div>
  <div>{_e(result.message)}</div>
  {lines}{detail}
</div>"""


def render_history(results: Sequence[CommandResult]) -> str:
    """Recent command outcomes."""
    if not results:
        return ""
    rows = [
        [
            _e(item.kind.value),
            f'<span class="{item.tone}">{_e(item.status.value)}</span>',
            _e(item.message[:70]),
            f"{item.duration_seconds:.1f}s",
        ]
        for item in results
    ]
    return f"""<section class="panel">
  <h2>Recent actions</h2>
  {_table(["Command", "Status", "Result", "Took"], rows, "Nothing run yet.")}
</section>"""


# ------------------------------------------------------------------- page --
def render_dashboard(
    view: DashboardView,
    equity_points: Sequence[CashPoint] = (),
    commands: Sequence[CommandDescriptor] = (),
    result: Optional[CommandResult] = None,
    history: Sequence[CommandResult] = (),
    busy: Optional[CommandKind] = None,
    busy_seconds: float = 0.0,
) -> str:
    """Render the complete dashboard page."""
    session_note = (
        f"session <span class='accent'>{_e(view.portfolio.session_id)}</span>"
        if view.portfolio is not None
        else "no session selected"
    )

    actions = render_actions(commands, busy, busy_seconds) if commands else ""
    outcome = render_result(result)

    if view.is_empty:
        body = actions + outcome + """<section class="panel wide">
  <h2>Nothing recorded yet</h2>
  <p class="empty">Use an action above, or run a script:</p>
  <p><code>python scripts/run_persistence.py --keep --db shadbot.db</code></p>
</section>""" + render_history(history)
    else:
        body = "".join(
            [
                actions,
                outcome,
                render_portfolio(view.portfolio),
                render_equity_chart(equity_points),
                render_decisions(view.decisions),
                render_executions(view.executions),
                render_candidates(view.candidates),
                '<div class="grid">',
                render_history(history),
                render_sessions(view.sessions),
                render_rejections(view.rejection_counts),
                render_system(view),
                "</div>",
            ]
        )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ShadBotTrader — Dashboard</title>
<style>{_STYLES}</style>
</head>
<body>
<header>
  <h1>ShadBotTrader</h1>
  <div class="sub">{session_note} · generated {_e(view.generated_at)}
    · <a class="accent" href="/replay">watch the last backtest replay</a></div>
</header>
{body}
<footer>
  Presentation layer only — this page dispatches commands and displays stored
  state; every calculation happens in the application services.
</footer>
</body>
</html>"""
