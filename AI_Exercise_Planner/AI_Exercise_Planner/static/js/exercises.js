/**
 * exercises.js – Exercise Library page logic.
 * Handles: load list, search/filter, add, edit, delete, view details.
 */

'use strict';

let _allExercises = [];
let _editingId    = null;
let _detailId     = null;

/* --------------------------------------------------------------------------
   DOM refs
   -------------------------------------------------------------------------- */
const searchInput       = document.getElementById('searchInput');
const filterCategory    = document.getElementById('filterCategory');
const filterDifficulty  = document.getElementById('filterDifficulty');
const tableBody         = document.getElementById('exerciseTableBody');
const emptyState        = document.getElementById('emptyState');
const loadingRow        = document.getElementById('loadingRow');

// Exercise modal
const exerciseModal      = document.getElementById('exerciseModal');
const exerciseModalTitle = document.getElementById('exerciseModalTitle');
const exerciseModalClose = document.getElementById('exerciseModalClose');
const exerciseForm       = document.getElementById('exerciseForm');
const exerciseId         = document.getElementById('exerciseId');
const exName             = document.getElementById('exName');
const exNameError        = document.getElementById('exNameError');
const exCategory         = document.getElementById('exCategory');
const exDifficulty       = document.getElementById('exDifficulty');
const exEquipment        = document.getElementById('exEquipment');
const exSets             = document.getElementById('exSets');
const exReps             = document.getElementById('exReps');
const exDuration         = document.getElementById('exDuration');
const exNotes            = document.getElementById('exNotes');
const exSaveBtn          = document.getElementById('exSaveBtn');
const exCancelBtn        = document.getElementById('exCancelBtn');

// Detail modal
const detailModal      = document.getElementById('detailModal');
const detailModalTitle = document.getElementById('detailModalTitle');
const detailModalClose = document.getElementById('detailModalClose');
const detailModalBody  = document.getElementById('detailModalBody');
const detailCloseBtn   = document.getElementById('detailCloseBtn');
const detailEditBtn    = document.getElementById('detailEditBtn');

/* --------------------------------------------------------------------------
   Load & render exercises
   -------------------------------------------------------------------------- */
async function loadExercises() {
  try {
    const q    = searchInput.value.trim();
    const cat  = filterCategory.value;
    const diff = filterDifficulty.value;
    const params = new URLSearchParams();
    if (q)    params.set('q', q);
    if (cat)  params.set('category', cat);
    if (diff) params.set('difficulty', diff);

    const data = await api(`/api/exercises?${params}`);
    _allExercises = data.exercises || [];
    renderTable(_allExercises);
  } catch (err) {
    tableBody.innerHTML = `<tr><td colspan="8" class="text-center text-danger py-6">Failed to load exercises: ${esc(err.message)}</td></tr>`;
  }
}

function renderTable(list) {
  if (loadingRow) loadingRow.remove();
  tableBody.innerHTML = '';

  if (!list.length) {
    emptyState.classList.remove('hidden');
    return;
  }
  emptyState.classList.add('hidden');

  list.forEach(ex => {
    const dur = ex.duration > 0 ? `${ex.duration} min` : '—';
    const sets = ex.sets > 0 ? ex.sets : '—';
    const reps = ex.reps > 0 ? ex.reps : '—';
    const tr = document.createElement('tr');
    tr.dataset.id = ex.id;
    tr.innerHTML = `
      <td class="exercise-name"><strong>${esc(ex.name)}</strong></td>
      <td><span class="badge badge--blue">${esc(ex.category)}</span></td>
      <td class="text-center">${sets}</td>
      <td class="text-center">${reps}</td>
      <td class="text-center">${dur}</td>
      <td>${difficultyBadge(ex.difficulty)}</td>
      <td><span class="text-muted text-sm">${esc(ex.equipment)}</span></td>
      <td class="text-right">
        <button class="btn btn-ghost btn-sm btn-view"   data-id="${esc(ex.id)}">👁</button>
        <button class="btn btn-ghost btn-sm btn-edit"   data-id="${esc(ex.id)}">✏️</button>
        <button class="btn btn-danger  btn-sm btn-delete" data-id="${esc(ex.id)}">🗑️</button>
      </td>`;
    tableBody.appendChild(tr);
  });
}

/* --------------------------------------------------------------------------
   Search / filter (debounced)
   -------------------------------------------------------------------------- */
let _debounceTimer;
function debounceLoad() {
  clearTimeout(_debounceTimer);
  _debounceTimer = setTimeout(loadExercises, 220);
}
searchInput.addEventListener('input', debounceLoad);
filterCategory.addEventListener('change', loadExercises);
filterDifficulty.addEventListener('change', loadExercises);

/* --------------------------------------------------------------------------
   Table action delegation
   -------------------------------------------------------------------------- */
tableBody.addEventListener('click', e => {
  const btn = e.target.closest('button');
  if (!btn) return;
  const id = btn.dataset.id;
  if (btn.classList.contains('btn-view'))   openDetailModal(id);
  if (btn.classList.contains('btn-edit'))   openEditModal(id);
  if (btn.classList.contains('btn-delete')) deleteExercise(id);
});

/* --------------------------------------------------------------------------
   Add / Edit modal
   -------------------------------------------------------------------------- */
function resetForm() {
  exerciseForm.reset();
  exNameError.textContent = '';
  exName.classList.remove('input-error');
  exSets.value     = '3';
  exReps.value     = '10';
  exDuration.value = '0';
  exerciseId.value = '';
  _editingId = null;
}

function openAddModal() {
  resetForm();
  exerciseModalTitle.textContent = 'Add Exercise';
  openModal(exerciseModal);
  exName.focus();
}

function openEditModal(id) {
  const ex = _allExercises.find(e => e.id === id);
  if (!ex) { showToast('Exercise not found.', 'error'); return; }
  resetForm();
  _editingId           = id;
  exerciseId.value     = id;
  exerciseModalTitle.textContent = 'Edit Exercise';
  exName.value         = ex.name;
  exCategory.value     = ex.category;
  exDifficulty.value   = ex.difficulty;
  exEquipment.value    = ex.equipment;
  exSets.value         = ex.sets;
  exReps.value         = ex.reps;
  exDuration.value     = ex.duration;
  exNotes.value        = ex.notes || '';
  openModal(exerciseModal);
  exName.focus();
}

async function saveExercise() {
  exNameError.textContent = '';
  const name = exName.value.trim();
  if (!name) {
    exNameError.textContent = 'Exercise name is required.';
    exName.focus();
    return;
  }

  const payload = {
    name,
    category:   exCategory.value,
    difficulty: exDifficulty.value,
    equipment:  exEquipment.value,
    sets:       parseInt(exSets.value) || 0,
    reps:       parseInt(exReps.value) || 0,
    duration:   parseInt(exDuration.value) || 0,
    notes:      exNotes.value.trim(),
  };

  exSaveBtn.disabled = true;
  exSaveBtn.textContent = 'Saving…';
  try {
    if (_editingId) {
      await api(`/api/exercises/${_editingId}`, { method: 'PUT', body: payload });
      showToast('Exercise updated.', 'success');
    } else {
      await api('/api/exercises', { method: 'POST', body: payload });
      showToast('Exercise added.', 'success');
    }
    closeModal(exerciseModal);
    loadExercises();
  } catch (err) {
    showToast(err.message || 'Failed to save exercise.', 'error');
  } finally {
    exSaveBtn.disabled = false;
    exSaveBtn.textContent = 'Save Exercise';
  }
}

/* --------------------------------------------------------------------------
   Delete
   -------------------------------------------------------------------------- */
async function deleteExercise(id) {
  const ex = _allExercises.find(e => e.id === id);
  const name = ex ? ex.name : id;
  if (!confirm(`Delete "${name}"?\nThis will also remove it from the weekly plan.`)) return;
  try {
    await api(`/api/exercises/${id}`, { method: 'DELETE' });
    showToast('Exercise deleted.', 'success');
    loadExercises();
  } catch (err) {
    showToast(err.message || 'Failed to delete.', 'error');
  }
}

/* --------------------------------------------------------------------------
   Detail modal
   -------------------------------------------------------------------------- */
function openDetailModal(id) {
  const ex = _allExercises.find(e => e.id === id);
  if (!ex) return;
  _detailId = id;
  detailModalTitle.textContent = ex.name;
  const dur = ex.duration > 0 ? `${ex.duration} min` : '—';
  detailModalBody.innerHTML = `
    <div class="form-grid" style="gap:10px">
      <div><span class="text-muted text-sm">Category</span><br><span class="badge badge--blue">${esc(ex.category)}</span></div>
      <div><span class="text-muted text-sm">Difficulty</span><br>${difficultyBadge(ex.difficulty)}</div>
      <div><span class="text-muted text-sm">Equipment</span><br>${esc(ex.equipment)}</div>
      <div><span class="text-muted text-sm">Sets / Reps</span><br>${ex.sets} × ${ex.reps}</div>
      <div><span class="text-muted text-sm">Duration</span><br>${dur}</div>
    </div>
    ${ex.notes ? `<div class="mt-4"><span class="text-muted text-sm">Notes</span><p class="mt-1">${esc(ex.notes)}</p></div>` : ''}`;
  openModal(detailModal);
}

/* --------------------------------------------------------------------------
   Wire up buttons
   -------------------------------------------------------------------------- */
document.getElementById('btnAddExercise').addEventListener('click', openAddModal);
document.getElementById('btnAddExerciseEmpty')?.addEventListener('click', openAddModal);
exSaveBtn.addEventListener('click', saveExercise);
exCancelBtn.addEventListener('click', () => closeModal(exerciseModal));
exerciseModalClose.addEventListener('click', () => closeModal(exerciseModal));

detailModalClose.addEventListener('click', () => closeModal(detailModal));
detailCloseBtn.addEventListener('click',   () => closeModal(detailModal));
detailEditBtn.addEventListener('click', () => {
  closeModal(detailModal);
  if (_detailId) openEditModal(_detailId);
});

/* --------------------------------------------------------------------------
   Init
   -------------------------------------------------------------------------- */
loadExercises();
