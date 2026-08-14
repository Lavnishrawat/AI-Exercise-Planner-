/**
 * progress.js – Progress page logic.
 * Loads overall progress stats and per-day breakdown from the API.
 */

'use strict';

/* --------------------------------------------------------------------------
   DOM refs
   -------------------------------------------------------------------------- */
const overallDiv    = document.getElementById('overallProgressContent');
const breakdownBody = document.getElementById('breakdownTableBody');
const btnRefresh    = document.getElementById('btnRefreshProgress');
const btnReset      = document.getElementById('btnResetProgress');

/* --------------------------------------------------------------------------
   Load progress
   -------------------------------------------------------------------------- */
async function loadProgress() {
  overallDiv.innerHTML    = '<div class="spinner-wrap"><div class="spinner"></div></div>';
  breakdownBody.innerHTML = '<tr><td colspan="6" class="text-center text-muted py-6">Loading…</td></tr>';

  try {
    const data = await api('/api/progress');
    renderOverall(data.overall);
    renderBreakdown(data.breakdown);
  } catch (err) {
    overallDiv.innerHTML = `<div class="banner banner--danger">Failed to load progress: ${esc(err.message)}</div>`;
  }
}

/* --------------------------------------------------------------------------
   Render overall stats
   -------------------------------------------------------------------------- */
function renderOverall(p) {
  const pct = p.percentage || 0;
  overallDiv.innerHTML = `
    <div class="overall-stats">
      <div class="overall-stat">
        <div class="overall-stat-val" style="color:var(--color-accent)">${p.total}</div>
        <div class="overall-stat-lbl">Total Planned</div>
      </div>
      <div class="overall-stat">
        <div class="overall-stat-val" style="color:var(--color-success)">${p.completed}</div>
        <div class="overall-stat-lbl">Completed</div>
      </div>
      <div class="overall-stat">
        <div class="overall-stat-val" style="color:var(--color-warning)">${p.remaining}</div>
        <div class="overall-stat-lbl">Remaining</div>
      </div>
      <div class="overall-stat">
        <div class="overall-stat-val" style="color:var(--color-purple)">${pct.toFixed(1)}%</div>
        <div class="overall-stat-lbl">Completion Rate</div>
      </div>
    </div>
    <div class="progress-row mb-2">
      <span class="progress-label">${p.completed} / ${p.total} exercises completed</span>
      <span class="progress-pct">${pct.toFixed(1)}%</span>
    </div>
    <div class="big-progress-bar">
      <div class="big-progress-fill" style="width:${pct}%"></div>
    </div>
    <p class="text-muted text-sm mt-3">
      Total planned duration: <strong>${formatDuration(p.total_duration_min)}</strong> &nbsp;·&nbsp;
      Completed: <strong>${formatDuration(p.completed_duration_min)}</strong>
    </p>`;
}

/* --------------------------------------------------------------------------
   Render per-day breakdown table
   -------------------------------------------------------------------------- */
function renderBreakdown(breakdown) {
  breakdownBody.innerHTML = '';
  if (!breakdown || !breakdown.length) {
    breakdownBody.innerHTML = '<tr><td colspan="6" class="text-center text-muted py-6">No data available.</td></tr>';
    return;
  }

  breakdown.forEach(d => {
    const pct = d.percentage || 0;
    let rowClass = '';
    if (d.total > 0 && d.completed === d.total) rowClass = 'text-success';
    else if (d.completed > 0) rowClass = 'text-warning';

    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td class="${rowClass}" style="font-weight:600">${esc(d.day)}</td>
      <td class="text-center">${d.total}</td>
      <td class="text-center">${d.completed}</td>
      <td class="text-center">${d.remaining}</td>
      <td>
        <div style="display:flex;align-items:center;gap:8px">
          <div class="breakdown-bar-wrap">
            <div class="breakdown-bar">
              <div class="breakdown-bar-fill" style="width:${pct}%;background:${pct===100 ? 'var(--color-success)' : 'var(--color-accent)'}"></div>
            </div>
          </div>
          <span class="text-sm">${pct.toFixed(0)}%</span>
        </div>
      </td>
      <td class="text-muted text-sm">${esc(formatDuration(d.total_duration_min))}</td>`;
    breakdownBody.appendChild(tr);
  });
}

/* --------------------------------------------------------------------------
   Reset all completions
   -------------------------------------------------------------------------- */
btnReset.addEventListener('click', async () => {
  if (!confirm('Mark all exercises across the whole week as not completed?')) return;
  try {
    await api('/api/planner/reset', { method: 'POST' });
    showToast('All completions reset.', 'success');
    loadProgress();
  } catch (err) {
    showToast(err.message || 'Failed to reset.', 'error');
  }
});

/* --------------------------------------------------------------------------
   Wire refresh button
   -------------------------------------------------------------------------- */
btnRefresh.addEventListener('click', loadProgress);

/* --------------------------------------------------------------------------
   Init
   -------------------------------------------------------------------------- */
loadProgress();
