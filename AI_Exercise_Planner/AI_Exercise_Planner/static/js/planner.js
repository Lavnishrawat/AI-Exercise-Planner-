/**
 * planner.js – Weekly Planner page logic.
 * Handles: day tabs, load entries per day, add/remove/toggle entries.
 */

'use strict';

const DAYS = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday'];
let _currentDay   = 'Monday';
let _allExercises = [];
let _dayEntries   = [];

/* --------------------------------------------------------------------------
   DOM refs
   -------------------------------------------------------------------------- */
const dayPanelTitle  = document.getElementById('dayPanelTitle');
const planTableBody  = document.getElementById('planTableBody');
const planEmptyState = document.getElementById('planEmptyState');
const daySummary     = document.getElementById('daySummary');

const planModal      = document.getElementById('planModal');
const planModalTitle = document.getElementById('planModalTitle');
const planModalClose = document.getElementById('planModalClose');
const planExSelect   = document.getElementById('planExerciseSelect');
const planSets       = document.getElementById('planSets');
const planReps       = document.getElementById('planReps');
const planDuration   = document.getElementById('planDuration');
const planNotes      = document.getElementById('planNotes');
const planSaveBtn    = document.getElementById('planSaveBtn');
const planCancelBtn  = document.getElementById('planCancelBtn');

/* --------------------------------------------------------------------------
   Load badge counts for all days
   -------------------------------------------------------------------------- */
async function loadAllBadges() {
  try {
    const data = await api('/api/planner');
    DAYS.forEach(day => {
      const badge = document.getElementById(`badge-${day}`);
      if (badge) {
        const entries = data.weekly_plan[day] || [];
        badge.textContent = entries.length;
      }
    });
  } catch (_) { /* silently ignore */ }
}

/* --------------------------------------------------------------------------
   Load a single day
   -------------------------------------------------------------------------- */
async function loadDay(day) {
  _currentDay = day;
  dayPanelTitle.textContent = day;
  planTableBody.innerHTML = '<tr><td colspan="7" class="text-center text-muted py-6"><div class="spinner-wrap"><div class="spinner"></div></div></td></tr>';
  planEmptyState.classList.add('hidden');

  try {
    const data = await api(`/api/planner/${day}`);
    _dayEntries = data.entries || [];
    renderDayTable(_dayEntries);
  } catch (err) {
    planTableBody.innerHTML = `<tr><td colspan="7" class="text-center text-danger py-6">${esc(err.message)}</td></tr>`;
  }
}

function renderDayTable(entries) {
  planTableBody.innerHTML = '';

  if (!entries.length) {
    planEmptyState.classList.remove('hidden');
    daySummary.textContent = `${_currentDay}: 0 exercises planned.`;
    return;
  }
  planEmptyState.classList.add('hidden');

  entries.forEach(e => {
    const dur   = e.duration > 0 ? `${e.duration} min` : '—';
    const sets  = e.sets > 0 ? e.sets : '—';
    const reps  = e.reps > 0 ? e.reps : '—';
    const done  = e.completed;
    const tr = document.createElement('tr');
    tr.dataset.entryId = e.entry_id;
    if (done) tr.classList.add('row-done');
    tr.innerHTML = `
      <td>
        <button class="btn btn-ghost btn-sm btn-toggle" data-entry="${esc(e.entry_id)}" title="Toggle completed">
          ${done ? '✅' : '⬜'}
        </button>
      </td>
      <td class="exercise-name">${esc(e.exercise_name)}</td>
      <td class="text-center">${sets}</td>
      <td class="text-center">${reps}</td>
      <td class="text-center">${dur}</td>
      <td class="text-sm text-muted">${esc(e.notes || '')}</td>
      <td class="text-right">
        <button class="btn btn-danger btn-sm btn-remove-entry" data-entry="${esc(e.entry_id)}">🗑️</button>
      </td>`;
    planTableBody.appendChild(tr);
  });

  const total     = entries.length;
  const completed = entries.filter(e => e.completed).length;
  daySummary.textContent = `${_currentDay}: ${total} exercise(s) — ${completed} completed`;
}

/* --------------------------------------------------------------------------
   Table delegation
   -------------------------------------------------------------------------- */
planTableBody.addEventListener('click', async e => {
  const toggleBtn = e.target.closest('.btn-toggle');
  const removeBtn = e.target.closest('.btn-remove-entry');

  if (toggleBtn) {
    const entryId = toggleBtn.dataset.entry;
    try {
      const res = await api(`/api/planner/${_currentDay}/${entryId}/toggle`, { method: 'POST' });
      const entry = _dayEntries.find(en => en.entry_id === entryId);
      if (entry) entry.completed = res.completed;
      renderDayTable(_dayEntries);
      loadAllBadges();
    } catch (err) {
      showToast(err.message || 'Failed to toggle.', 'error');
    }
  }

  if (removeBtn) {
    const entryId = removeBtn.dataset.entry;
    const entry = _dayEntries.find(en => en.entry_id === entryId);
    const name = entry ? entry.exercise_name : entryId;
    if (!confirm(`Remove "${name}" from ${_currentDay}?`)) return;
    try {
      await api(`/api/planner/${_currentDay}/${entryId}`, { method: 'DELETE' });
      _dayEntries = _dayEntries.filter(en => en.entry_id !== entryId);
      renderDayTable(_dayEntries);
      loadAllBadges();
      showToast('Entry removed.', 'success');
    } catch (err) {
      showToast(err.message || 'Failed to remove.', 'error');
    }
  }
});

/* --------------------------------------------------------------------------
   Add to Plan modal
   -------------------------------------------------------------------------- */
async function loadExercisesForSelect() {
  try {
    const data = await api('/api/exercises');
    const exercises = data.exercises || [];
    _allExercises = exercises;
    planExSelect.innerHTML = '<option value="">— Select an exercise —</option>';
    exercises.forEach(ex => {
      const opt = document.createElement('option');
      opt.value = ex.id;
      opt.textContent = ex.name;
      opt.dataset.sets     = ex.sets;
      opt.dataset.reps     = ex.reps;
      opt.dataset.duration = ex.duration;
      planExSelect.appendChild(opt);
    });
  } catch (err) {
    showToast('Could not load exercises: ' + err.message, 'error');
  }
}

planExSelect.addEventListener('change', () => {
  const opt = planExSelect.selectedOptions[0];
  if (opt && opt.dataset.sets !== undefined) {
    planSets.value     = opt.dataset.sets;
    planReps.value     = opt.dataset.reps;
    planDuration.value = opt.dataset.duration;
  }
});

function openAddToPlanModal() {
  planModalTitle.textContent = `Add Exercise to ${_currentDay}`;
  planExSelect.value = '';
  planSets.value = '3';
  planReps.value = '10';
  planDuration.value = '0';
  planNotes.value = '';
  openModal(planModal);
}

async function saveEntryToPlan() {
  const exId = planExSelect.value;
  if (!exId) {
    showToast('Please select an exercise.', 'warning');
    return;
  }
  const ex = _allExercises.find(e => e.id === exId);
  const payload = {
    exercise_id:   exId,
    exercise_name: ex ? ex.name : exId,
    sets:          parseInt(planSets.value) || 0,
    reps:          parseInt(planReps.value) || 0,
    duration:      parseInt(planDuration.value) || 0,
    notes:         planNotes.value.trim(),
  };
  planSaveBtn.disabled = true;
  planSaveBtn.textContent = 'Adding…';
  try {
    await api(`/api/planner/${_currentDay}`, { method: 'POST', body: payload });
    showToast(`Added to ${_currentDay}.`, 'success');
    closeModal(planModal);
    loadDay(_currentDay);
    loadAllBadges();
  } catch (err) {
    showToast(err.message || 'Failed to add entry.', 'error');
  } finally {
    planSaveBtn.disabled = false;
    planSaveBtn.textContent = 'Add to Day';
  }
}

/* --------------------------------------------------------------------------
   Day tabs
   -------------------------------------------------------------------------- */
document.getElementById('dayTabs').addEventListener('click', e => {
  const tab = e.target.closest('.day-tab');
  if (!tab) return;
  document.querySelectorAll('.day-tab').forEach(t => t.classList.remove('active'));
  tab.classList.add('active');
  loadDay(tab.dataset.day);
});

/* --------------------------------------------------------------------------
   Reset all completions
   -------------------------------------------------------------------------- */
document.getElementById('btnResetWeek').addEventListener('click', async () => {
  if (!confirm('Mark all exercises across the whole week as not completed?')) return;
  try {
    await api('/api/planner/reset', { method: 'POST' });
    showToast('All completions reset.', 'success');
    loadDay(_currentDay);
    loadAllBadges();
  } catch (err) {
    showToast(err.message || 'Failed to reset.', 'error');
  }
});

/* --------------------------------------------------------------------------
   Wire buttons
   -------------------------------------------------------------------------- */
document.getElementById('btnAddToPlan').addEventListener('click', openAddToPlanModal);
document.getElementById('btnAddToPlanEmpty')?.addEventListener('click', openAddToPlanModal);
planSaveBtn.addEventListener('click', saveEntryToPlan);
planCancelBtn.addEventListener('click', () => closeModal(planModal));
planModalClose.addEventListener('click', () => closeModal(planModal));

/* --------------------------------------------------------------------------
   Init
   -------------------------------------------------------------------------- */
loadExercisesForSelect();
loadDay('Monday');
loadAllBadges();
