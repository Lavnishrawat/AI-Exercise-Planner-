/**
 * quick_workout.js – Quick Workout page logic.
 * Handles: generate random exercises, toggle completed, add to today's plan.
 */

'use strict';

let _quickExercises = [];

/* --------------------------------------------------------------------------
   DOM refs
   -------------------------------------------------------------------------- */
const contentDiv  = document.getElementById('quickWorkoutContent');
const btnGenerate = document.getElementById('btnGenerate');
const btnMarkAll  = document.getElementById('btnMarkAll');
const btnAddToday = document.getElementById('btnAddToday');

/* --------------------------------------------------------------------------
   Generate
   -------------------------------------------------------------------------- */
async function generateQuickWorkout() {
  contentDiv.innerHTML = '<div class="spinner-wrap"><div class="spinner"></div></div>';
  _quickExercises = [];
  try {
    const data = await api('/api/quick-workout');
    _quickExercises = (data.exercises || []).map(ex => ({ ...ex, completed: false }));
    renderQuickList();
  } catch (err) {
    contentDiv.innerHTML = `
      <div class="banner banner--warning">
        <strong>⚠️ ${esc(err.message)}</strong>
        <p class="mt-2 text-sm">Go to the <a href="/exercises">Exercise Library</a> and add at least 3 exercises.</p>
      </div>`;
  }
}

/* --------------------------------------------------------------------------
   Render
   -------------------------------------------------------------------------- */
function renderQuickList() {
  if (!_quickExercises.length) {
    contentDiv.innerHTML = '<div class="empty-state"><div class="empty-icon">⚡</div><p>No exercises generated yet.</p></div>';
    return;
  }

  const list = document.createElement('div');
  list.className = 'quick-exercise-list';

  _quickExercises.forEach((ex, i) => {
    const card = document.createElement('div');
    card.className = `quick-exercise-card${ex.completed ? ' done' : ''}`;
    card.dataset.index = i;

    const setReps = (ex.sets && ex.reps)
      ? `${ex.sets} sets × ${ex.reps} reps`
      : ex.duration > 0 ? `${ex.duration} min` : '';

    card.innerHTML = `
      <div class="quick-check">${ex.completed ? '✅' : '⬜'}</div>
      <div class="quick-exercise-body">
        <div class="quick-exercise-name">${esc(ex.name)}</div>
        <div class="quick-exercise-meta">
          <span class="badge badge--blue">${esc(ex.category)}</span>
          ${setReps ? `<span>${esc(setReps)}</span>` : ''}
          ${difficultyBadge(ex.difficulty)}
        </div>
        ${ex.notes ? `<div class="text-muted text-xs mt-1">${esc(ex.notes)}</div>` : ''}
      </div>`;

    card.addEventListener('click', () => toggleExercise(i));
    list.appendChild(card);
  });

  contentDiv.innerHTML = '';
  contentDiv.appendChild(list);

  // Summary
  const done  = _quickExercises.filter(e => e.completed).length;
  const total = _quickExercises.length;
  const summary = document.createElement('p');
  summary.className = 'text-muted text-sm mt-3';
  summary.textContent = `${done} / ${total} completed — click a card to toggle.`;
  contentDiv.appendChild(summary);
}

/* --------------------------------------------------------------------------
   Toggle single exercise
   -------------------------------------------------------------------------- */
function toggleExercise(index) {
  if (index < 0 || index >= _quickExercises.length) return;
  _quickExercises[index].completed = !_quickExercises[index].completed;
  renderQuickList();
}

/* --------------------------------------------------------------------------
   Mark all done
   -------------------------------------------------------------------------- */
btnMarkAll.addEventListener('click', () => {
  _quickExercises.forEach(ex => { ex.completed = true; });
  renderQuickList();
});

/* --------------------------------------------------------------------------
   Add to today's plan
   -------------------------------------------------------------------------- */
btnAddToday.addEventListener('click', async () => {
  if (!_quickExercises.length) {
    showToast('Generate a workout first.', 'warning');
    return;
  }
  btnAddToday.disabled = true;
  const today = new Date().toLocaleDateString('en-US', { weekday: 'long' });
  const validDays = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday'];
  const targetDay = validDays.includes(today) ? today : 'Monday';

  let addedCount = 0;
  let errors = 0;
  for (const ex of _quickExercises) {
    try {
      await api(`/api/planner/${targetDay}`, {
        method: 'POST',
        body: {
          exercise_id:   ex.id,
          exercise_name: ex.name,
          sets:          ex.sets || 0,
          reps:          ex.reps || 0,
          duration:      ex.duration || 0,
          notes:         ex.notes || '',
        },
      });
      addedCount++;
    } catch (_) { errors++; }
  }

  if (addedCount > 0) {
    showToast(`Added ${addedCount} exercise(s) to ${targetDay}'s plan.`, 'success');
  }
  if (errors > 0) {
    showToast(`${errors} exercise(s) could not be added.`, 'warning');
  }
  btnAddToday.disabled = false;
});

/* --------------------------------------------------------------------------
   Wire buttons
   -------------------------------------------------------------------------- */
btnGenerate.addEventListener('click', generateQuickWorkout);

/* --------------------------------------------------------------------------
   Init
   -------------------------------------------------------------------------- */
generateQuickWorkout();
