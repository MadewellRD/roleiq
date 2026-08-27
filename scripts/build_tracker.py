"""Regenerates docs/engineering-spec/tracker.html from tracker.json.

Run from the repo root: .venv\\Scripts\\python.exe scripts\\build_tracker.py

Then republish the artifact at that same path (Artifact tool, same
file_path) to update the pinned RoleIQ Go-Live Tracker in place --
tracker.json is the state, this HTML is only a generated view of it.
Per the go-live protocol's update cadence: after every merged PR, no
exceptions.
"""

import json
import os

_here = os.path.dirname(os.path.abspath(__file__))
_repo_root = os.path.dirname(_here)

with open(os.path.join(_repo_root, 'docs', 'engineering-spec', 'tracker.json')) as f:
    data = json.load(f)

tracker_json = json.dumps(data)

html_template = r'''<title>RoleIQ Go-Live Tracker</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<style>
  :root {
    --bg: #F4F6F8;
    --surface: #FFFFFF;
    --surface-2: #EAEEF1;
    --ink: #1B2430;
    --ink-soft: #4C5866;
    --ink-faint: #7C8695;
    --border: #DCE2E7;
    --accent: #B87A1F;
    --accent-soft: #F3E3CC;
    --teal: #2F6F6B;
    --teal-soft: #DCEBEA;
    --done: #3A7D44;
    --done-soft: #DEEDDF;
    --progress: #B87A1F;
    --progress-soft: #F3E3CC;
    --blocked: #C1473B;
    --blocked-soft: #F7DFDC;
    --todo: #7C8695;
    --todo-soft: #E7EAED;
    --shadow: 0 1px 2px rgba(27,36,48,0.06), 0 4px 12px rgba(27,36,48,0.05);
  }
  @media (prefers-color-scheme: dark) {
    :root:not([data-theme="light"]) {
      --bg: #10151C;
      --surface: #171E27;
      --surface-2: #1E2732;
      --ink: #E8EAED;
      --ink-soft: #AEB8C2;
      --ink-faint: #7E8894;
      --border: #2A333E;
      --accent: #E0A94A;
      --accent-soft: #3A2E17;
      --teal: #5CB3AC;
      --teal-soft: #16302E;
      --done: #6FBF77;
      --done-soft: #17301C;
      --progress: #E0A94A;
      --progress-soft: #3A2E17;
      --blocked: #E17A6E;
      --blocked-soft: #3A2019;
      --todo: #8B95A1;
      --todo-soft: #232B34;
      --shadow: 0 1px 2px rgba(0,0,0,0.3), 0 4px 16px rgba(0,0,0,0.25);
    }
  }
  :root[data-theme="dark"] {
    --bg: #10151C;
    --surface: #171E27;
    --surface-2: #1E2732;
    --ink: #E8EAED;
    --ink-soft: #AEB8C2;
    --ink-faint: #7E8894;
    --border: #2A333E;
    --accent: #E0A94A;
    --accent-soft: #3A2E17;
    --teal: #5CB3AC;
    --teal-soft: #16302E;
    --done: #6FBF77;
    --done-soft: #17301C;
    --progress: #E0A94A;
    --progress-soft: #3A2E17;
    --blocked: #E17A6E;
    --blocked-soft: #3A2019;
    --todo: #8B95A1;
    --todo-soft: #232B34;
    --shadow: 0 1px 2px rgba(0,0,0,0.3), 0 4px 16px rgba(0,0,0,0.25);
  }

  * { box-sizing: border-box; }
  html, body { margin: 0; padding: 0; }
  body {
    background: var(--bg);
    color: var(--ink);
    font-family: 'IBM Plex Sans', system-ui, sans-serif;
    font-size: 15px;
    line-height: 1.5;
    -webkit-font-smoothing: antialiased;
  }
  .mono { font-family: 'IBM Plex Mono', ui-monospace, monospace; font-variant-numeric: tabular-nums; }

  .wrap { max-width: 1120px; margin: 0 auto; padding: 40px 24px 80px; }

  header.top {
    display: flex; align-items: baseline; justify-content: space-between;
    gap: 16px; flex-wrap: wrap; margin-bottom: 6px;
  }
  header.top h1 {
    font-size: 28px; font-weight: 700; margin: 0; letter-spacing: -0.01em;
    text-wrap: balance;
  }
  header.top .proj-tag {
    font-family: 'IBM Plex Mono', monospace; font-size: 12px; color: var(--ink-faint);
    text-transform: uppercase; letter-spacing: 0.08em;
  }
  .subhead { color: var(--ink-soft); font-size: 14px; margin: 4px 0 32px; }
  .subhead .mono { color: var(--ink-faint); }

  /* summary bar */
  .summary {
    display: grid; grid-template-columns: 1.2fr 2fr; gap: 20px;
    background: var(--surface); border: 1px solid var(--border); border-radius: 14px;
    padding: 24px; box-shadow: var(--shadow); margin-bottom: 28px;
  }
  @media (max-width: 720px) { .summary { grid-template-columns: 1fr; } }
  .summary-stat { display: flex; flex-direction: column; justify-content: center; }
  .summary-stat .num { font-family: 'IBM Plex Mono', monospace; font-size: 44px; font-weight: 600; line-height: 1; }
  .summary-stat .num small { font-size: 20px; color: var(--ink-faint); font-weight: 500; }
  .summary-stat .label { color: var(--ink-soft); font-size: 13px; margin-top: 8px; text-transform: uppercase; letter-spacing: 0.06em; }
  .overall-bar-track { height: 10px; border-radius: 6px; background: var(--surface-2); overflow: hidden; margin-top: 14px; }
  .overall-bar-fill { height: 100%; background: linear-gradient(90deg, var(--accent), var(--teal)); border-radius: 6px; transition: width .3s ease; }
  .legend { display: flex; gap: 18px; flex-wrap: wrap; margin-top: 16px; }
  .legend-item { display: flex; align-items: center; gap: 6px; font-size: 12px; color: var(--ink-soft); }
  .dot { width: 9px; height: 9px; border-radius: 50%; display: inline-block; }

  .status-breakdown { display: flex; flex-direction: column; justify-content: center; gap: 10px; }
  .status-row { display: grid; grid-template-columns: 90px 1fr 34px; align-items: center; gap: 10px; }
  .status-row .swatch-label { font-size: 12.5px; color: var(--ink-soft); text-transform: uppercase; letter-spacing: 0.04em; }
  .status-row .bar-track { height: 8px; border-radius: 5px; background: var(--surface-2); overflow: hidden; }
  .status-row .bar-fill { height: 100%; border-radius: 5px; }
  .status-row .count { font-family: 'IBM Plex Mono', monospace; font-size: 12.5px; text-align: right; color: var(--ink-faint); }

  /* milestone strip */
  .section-label {
    font-size: 12px; text-transform: uppercase; letter-spacing: 0.09em; color: var(--ink-faint);
    margin: 32px 0 12px; font-weight: 600;
  }
  .milestones { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-bottom: 8px; }
  @media (max-width: 860px) { .milestones { grid-template-columns: repeat(2, 1fr); } }
  .m-card {
    background: var(--surface); border: 1px solid var(--border); border-radius: 10px;
    padding: 12px 14px; cursor: pointer; transition: border-color .15s ease, transform .1s ease;
    text-align: left; font: inherit; color: inherit;
  }
  .m-card:hover { border-color: var(--accent); }
  .m-card.active { border-color: var(--accent); box-shadow: 0 0 0 1px var(--accent); }
  .m-card .m-sprint { font-family: 'IBM Plex Mono', monospace; font-size: 10.5px; color: var(--ink-faint); text-transform: uppercase; letter-spacing: 0.06em; }
  .m-card .m-name { font-size: 13px; font-weight: 600; margin: 3px 0 8px; line-height: 1.25; min-height: 33px; }
  .m-card .m-bar-track { height: 6px; border-radius: 4px; background: var(--surface-2); overflow: hidden; }
  .m-card .m-bar-fill { height: 100%; border-radius: 4px; background: var(--teal); }
  .m-card .m-count { font-family: 'IBM Plex Mono', monospace; font-size: 10.5px; color: var(--ink-faint); margin-top: 6px; }

  /* filter row */
  .filter-row { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin: 28px 0 10px; flex-wrap: wrap; }
  .filter-row .showing { font-size: 13px; color: var(--ink-soft); }
  .filter-row .showing .mono { color: var(--accent); font-weight: 600; }
  .clear-filter { font-size: 12.5px; color: var(--teal); background: none; border: none; cursor: pointer; font-family: inherit; padding: 0; text-decoration: underline; text-underline-offset: 2px; }
  .clear-filter[hidden] { display: none; }

  /* backlog */
  .backlog { display: flex; flex-direction: column; gap: 8px; }
  .gl-row {
    display: grid; grid-template-columns: 76px 1fr 108px 100px; align-items: center; gap: 14px;
    background: var(--surface); border: 1px solid var(--border); border-left: 3px solid var(--border);
    border-radius: 8px; padding: 12px 14px;
  }
  .gl-row.sev-blocked, .gl-row[data-status="blocked"] { border-left-color: var(--blocked); }
  .gl-row[data-status="in_progress"] { border-left-color: var(--progress); }
  .gl-row[data-status="done"] { border-left-color: var(--done); }
  .gl-row[data-status="todo"] { border-left-color: var(--todo); }
  .gl-id { font-family: 'IBM Plex Mono', monospace; font-size: 13px; color: var(--ink-faint); font-weight: 600; }
  .gl-main .gl-title { font-size: 14px; font-weight: 500; }
  .gl-main .gl-meta { font-size: 12px; color: var(--ink-faint); margin-top: 3px; }
  .gl-main .gl-meta .src { font-family: 'IBM Plex Mono', monospace; }
  .chip {
    display: inline-flex; align-items: center; justify-content: center; gap: 5px;
    font-size: 11.5px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.03em;
    padding: 4px 10px; border-radius: 100px; white-space: nowrap;
  }
  .chip.todo { background: var(--todo-soft); color: var(--todo); }
  .chip.in_progress { background: var(--progress-soft); color: var(--progress); }
  .chip.blocked { background: var(--blocked-soft); color: var(--blocked); }
  .chip.done { background: var(--done-soft); color: var(--done); }
  .gl-milestone { font-family: 'IBM Plex Mono', monospace; font-size: 12px; color: var(--ink-soft); text-align: right; }

  @media (max-width: 640px) {
    .gl-row { grid-template-columns: 1fr; gap: 6px; }
    .gl-milestone { text-align: left; }
  }

  /* commit feed */
  .feed { display: flex; flex-direction: column; border: 1px solid var(--border); border-radius: 10px; overflow: hidden; background: var(--surface); }
  .feed-row { display: grid; grid-template-columns: 84px 1fr 150px; gap: 14px; padding: 11px 16px; align-items: center; }
  .feed-row + .feed-row { border-top: 1px solid var(--border); }
  .feed-sha { font-family: 'IBM Plex Mono', monospace; font-size: 12.5px; color: var(--teal); }
  .feed-msg { font-size: 13.5px; }
  .feed-date { font-family: 'IBM Plex Mono', monospace; font-size: 11.5px; color: var(--ink-faint); text-align: right; }

  footer.note {
    margin-top: 40px; padding-top: 20px; border-top: 1px solid var(--border);
    font-size: 12.5px; color: var(--ink-faint); line-height: 1.6;
  }
  footer.note .mono { color: var(--ink-soft); }
</style>

<div class="wrap">
  <header class="top">
    <h1>RoleIQ Go-Live Tracker</h1>
    <span class="proj-tag mono" id="generatedAt"></span>
  </header>
  <p class="subhead">Reads from <span class="mono">docs/engineering-spec/tracker.json</span> &middot; republished after every merged PR, per the go-live protocol's update cadence &mdash; not a live connector fetch (none was available to wire up in this environment).</p>

  <div class="summary">
    <div class="summary-stat">
      <div class="num" id="overallNum">0<small>/0</small></div>
      <div class="label">GL items complete</div>
      <div class="overall-bar-track"><div class="overall-bar-fill" id="overallBar" style="width:0%"></div></div>
      <div class="legend">
        <span class="legend-item"><span class="dot" style="background:var(--done)"></span>Done</span>
        <span class="legend-item"><span class="dot" style="background:var(--progress)"></span>In progress</span>
        <span class="legend-item"><span class="dot" style="background:var(--blocked)"></span>Blocked</span>
        <span class="legend-item"><span class="dot" style="background:var(--todo)"></span>Todo</span>
      </div>
    </div>
    <div class="status-breakdown" id="statusBreakdown"></div>
  </div>

  <div class="section-label">Milestones &mdash; click to filter</div>
  <div class="milestones" id="milestones"></div>

  <div class="filter-row">
    <span class="showing" id="showingLabel"></span>
    <button class="clear-filter" id="clearFilter" hidden>Show all milestones</button>
  </div>
  <div class="backlog" id="backlog"></div>

  <div class="section-label">Commits &mdash; most recent first</div>
  <div class="feed" id="feed"></div>

  <footer class="note">
    Source of truth: <span class="mono">docs/engineering-spec/tracker.json</span> in <span class="mono">github.com/MadewellRD/roleiq</span>. Status discipline: a task is <span class="mono">done</span> only when its acceptance gate passed, not when the code compiles &mdash; see each item's acceptance text. GL ids are permanent once assigned; never renumbered.
  </footer>
</div>

<script>
  const DATA = __TRACKER_JSON__;

  const STATUS_LABEL = { todo: 'Todo', in_progress: 'In progress', blocked: 'Blocked', done: 'Done' };
  const STATUS_ORDER = ['done', 'in_progress', 'blocked', 'todo'];

  document.getElementById('generatedAt').textContent =
    'generated ' + DATA.generated_at.replace('T', ' ').replace('Z', ' UTC');

  // ---- summary ----
  const total = DATA.tasks.length;
  const counts = { done: 0, in_progress: 0, blocked: 0, todo: 0 };
  DATA.tasks.forEach(t => counts[t.status]++);

  document.getElementById('overallNum').innerHTML = counts.done + '<small>/' + total + '</small>';
  document.getElementById('overallBar').style.width = (total ? (counts.done / total * 100) : 0) + '%';

  const STATUS_COLOR_VAR = { done: '--done', in_progress: '--progress', blocked: '--blocked', todo: '--todo' };
  const breakdown = document.getElementById('statusBreakdown');
  STATUS_ORDER.forEach(s => {
    const pct = total ? (counts[s] / total * 100) : 0;
    const row = document.createElement('div');
    row.className = 'status-row';
    row.innerHTML =
      '<span class="swatch-label">' + STATUS_LABEL[s] + '</span>' +
      '<span class="bar-track"><span class="bar-fill" style="width:' + pct + '%;background:var(' + STATUS_COLOR_VAR[s] + ')"></span></span>' +
      '<span class="count mono">' + counts[s] + '</span>';
    breakdown.appendChild(row);
  });

  // ---- milestones ----
  let activeMilestone = null;
  const milestonesEl = document.getElementById('milestones');
  const backlogEl = document.getElementById('backlog');
  const showingLabel = document.getElementById('showingLabel');
  const clearFilterBtn = document.getElementById('clearFilter');

  function tasksFor(mid) { return DATA.tasks.filter(t => t.milestone === mid); }

  function renderMilestones() {
    milestonesEl.innerHTML = '';
    DATA.milestones.forEach(m => {
      const mTasks = tasksFor(m.id);
      const mDone = mTasks.filter(t => t.status === 'done').length;
      const pct = mTasks.length ? (mDone / mTasks.length * 100) : 0;
      const card = document.createElement('button');
      card.className = 'm-card' + (activeMilestone === m.id ? ' active' : '');
      card.innerHTML =
        '<div class="m-sprint">Sprint ' + m.sprint + ' &middot; ' + m.id + '</div>' +
        '<div class="m-name">' + m.name + '</div>' +
        '<div class="m-bar-track"><div class="m-bar-fill" style="width:' + pct + '%"></div></div>' +
        '<div class="m-count mono">' + mDone + ' / ' + mTasks.length + '</div>';
      card.addEventListener('click', () => {
        activeMilestone = (activeMilestone === m.id) ? null : m.id;
        renderMilestones();
        renderBacklog();
      });
      milestonesEl.appendChild(card);
    });
  }

  function renderBacklog() {
    const list = activeMilestone ? tasksFor(activeMilestone) : DATA.tasks.slice();
    list.sort((a, b) => {
      const ma = DATA.milestones.find(m => m.id === a.milestone);
      const mb = DATA.milestones.find(m => m.id === b.milestone);
      if (ma.sprint !== mb.sprint) return ma.sprint - mb.sprint;
      return a.id.localeCompare(b.id);
    });
    backlogEl.innerHTML = '';
    list.forEach(t => {
      const row = document.createElement('div');
      row.className = 'gl-row';
      row.dataset.status = t.status;
      const depText = t.depends_on && t.depends_on.length ? ' &middot; depends on ' + t.depends_on.join(', ') : '';
      row.innerHTML =
        '<span class="gl-id">' + t.id + '</span>' +
        '<div class="gl-main"><div class="gl-title">' + t.title + '</div>' +
        '<div class="gl-meta"><span class="src">' + t.source + '</span>' + depText + '</div></div>' +
        '<span class="chip ' + t.status + '">' + STATUS_LABEL[t.status] + '</span>' +
        '<span class="gl-milestone">' + t.milestone + '</span>';
      backlogEl.appendChild(row);
    });
    showingLabel.innerHTML = 'Showing <span class="mono">' + list.length + '</span> of <span class="mono">' + total + '</span> items' +
      (activeMilestone ? ' in <span class="mono">' + activeMilestone + '</span>' : '');
    clearFilterBtn.hidden = !activeMilestone;
  }

  clearFilterBtn.addEventListener('click', () => {
    activeMilestone = null;
    renderMilestones();
    renderBacklog();
  });

  renderMilestones();
  renderBacklog();

  // ---- commit feed ----
  const feedEl = document.getElementById('feed');
  const commits = DATA.commits.slice().sort((a, b) => new Date(b.date) - new Date(a.date));
  commits.forEach(c => {
    const row = document.createElement('div');
    row.className = 'feed-row';
    const d = new Date(c.date);
    const dateStr = isNaN(d) ? c.date : d.toISOString().slice(0, 16).replace('T', ' ');
    row.innerHTML =
      '<span class="feed-sha mono">' + c.sha + '</span>' +
      '<span class="feed-msg">' + c.message + '</span>' +
      '<span class="feed-date">' + dateStr + ' UTC</span>';
    feedEl.appendChild(row);
  });
</script>
'''

html = html_template.replace('__TRACKER_JSON__', tracker_json)

out_path = os.path.join(_repo_root, 'docs', 'engineering-spec', 'tracker.html')
with open(out_path, 'w', encoding='utf-8') as f:
    f.write(html)

print("Written", len(html), "bytes to", out_path)
