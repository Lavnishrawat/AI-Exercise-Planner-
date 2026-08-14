/**
 * ai_assistant.js – AI Workout Assistant page logic.
 * Handles: form submission, calling /api/ai/generate, rendering the plan,
 * saving the plan, and adding it to the weekly planner.
 */

'use strict';

let _lastPlan    = null;
let _lastRawText = '';

/* --------------------------------------------------------------------------
   DOM refs
   -------------------------------------------------------------------------- */
const aiForm          = document.getElementById('aiForm');
const aiGenerateBtn   = document.getElementById('aiGenerateBtn');
const aiStatus        = document.getElementById('aiStatus');
const aiOutputBody    = document.getElementById('aiOutputBody');
const aiOutputActions = document.getElementById('aiOutputActions');
const aiDaysError     = document.getElementById('aiDaysError');
const aiDurationError = document.getElementById('aiDurationError');

const btnSavePlan     = document.getElementById('btnSavePlan');
const btnAddToPlanner = document.getElementById('btnAddToPlanner');

/* --------------------------------------------------------------------------
   Show status in the left panel
   -------------------------------------------------------------------------- */
function setStatus(message, type = '') {
  aiStatus.textContent = message;
  aiStatus.className   = `ai-status mt-3 ${type}`;
  aiStatus.classList.toggle('hidden', !message);
}

/* --------------------------------------------------------------------------
   Validate inputs, return payload or null
   -------------------------------------------------------------------------- */
function buildPayload() {
  aiDaysError.textContent     = '';
  aiDurationError.textContent = '';

  const goal       = document.getElementById('aiGoal').value;
  const experience = document.getElementById('aiExperience').value;
  const equipment  = document.getElementById('aiEquipment').value;
  const notesRaw   = document.getElementById('aiNotes').value.trim();
  const extra_notes = (notesRaw === 'e.g. Avoid jumping exercises, focus on upper body…') ? '' : notesRaw;

  const days = parseInt(document.getElementById('aiDays').value);
  if (!days || days < 1 || days > 7) {
    aiDaysError.textContent = 'Must be between 1 and 7.';
    document.getElementById('aiDays').focus();
    return null;
  }

  const duration = parseInt(document.getElementById('aiDuration').value);
  if (!duration || duration < 15 || duration > 120) {
    aiDurationError.textContent = 'Must be between 15 and 120 minutes.';
    document.getElementById('aiDuration').focus();
    return null;
  }

  return { goal, experience, days_per_week: days, duration_min: duration, equipment, extra_notes };
}

/* --------------------------------------------------------------------------
   Render the parsed plan into the output panel
   -------------------------------------------------------------------------- */
function renderPlan(plan) {
  aiOutputBody.innerHTML = '';

  // Meta chips
  const metaSection = document.createElement('div');
  metaSection.className = 'plan-section';
  const metaDiv = document.createElement('div');
  metaDiv.className = 'plan-meta';
  const chips = [
    `🎯 ${plan.goal || '?'}`,
    `🏅 ${plan.experience || '?'}`,
    `📅 ${plan.days_per_week || '?'} days/week`,
    `⏱ ${plan.duration_min || '?'} min/session`,
    `🏋 ${plan.equipment || '?'}`,
  ];
  chips.forEach(c => {
    const chip = document.createElement('span');
    chip.className = 'plan-meta-chip';
    chip.textContent = c;
    metaDiv.appendChild(chip);
  });
  metaSection.appendChild(metaDiv);
  aiOutputBody.appendChild(metaSection);

  // Warm-up
  if (plan.warm_up && plan.warm_up.description) {
    aiOutputBody.appendChild(renderInfoSection('🔥 Warm-Up',
      `${plan.warm_up.description} (${plan.warm_up.duration_min || 0} min)`));
  }

  // Schedule
  if (plan.schedule && plan.schedule.length) {
    const schedSec = document.createElement('div');
    schedSec.className = 'plan-section';
    const schedTitle = document.createElement('div');
    schedTitle.className = 'plan-section-title';
    schedTitle.textContent = '📅 Weekly Schedule';
    schedSec.appendChild(schedTitle);

    plan.schedule.forEach(dayBlock => {
      const block = document.createElement('div');
      block.className = 'day-block';

      const hdr = document.createElement('div');
      hdr.className = 'day-block-header';
      hdr.textContent = dayBlock.day + (dayBlock.focus ? ` — ${dayBlock.focus}` : '');
      block.appendChild(hdr);

      (dayBlock.exercises || []).forEach(ex => {
        const item = document.createElement('div');
        item.className = 'exercise-item';
        const nameLine = document.createElement('div');
        nameLine.className = 'exercise-item-name';
        nameLine.textContent = ex.name || '?';
        item.appendChild(nameLine);

        const metaParts = [];
        if (ex.sets && ex.reps)   metaParts.push(`${ex.sets} sets × ${ex.reps} reps`);
        else if (ex.duration_min) metaParts.push(`${ex.duration_min} min`);
        if (ex.rest_sec)          metaParts.push(`Rest: ${ex.rest_sec}s`);
        if (ex.difficulty)        metaParts.push(ex.difficulty);

        if (metaParts.length) {
          const meta = document.createElement('div');
          meta.className = 'exercise-item-meta';
          meta.textContent = metaParts.join('  ·  ');
          item.appendChild(meta);
        }
        if (ex.instructions) {
          const instr = document.createElement('div');
          instr.className = 'exercise-item-instructions';
          instr.textContent = ex.instructions;
          item.appendChild(instr);
        }
        block.appendChild(item);
      });
      schedSec.appendChild(block);
    });
    aiOutputBody.appendChild(schedSec);
  }

  // Cool-down
  if (plan.cool_down && plan.cool_down.description) {
    aiOutputBody.appendChild(renderInfoSection('❄️ Cool-Down',
      `${plan.cool_down.description} (${plan.cool_down.duration_min || 0} min)`));
  }

  // Recovery
  if (plan.recovery_recommendations) {
    aiOutputBody.appendChild(renderInfoSection('💤 Recovery', plan.recovery_recommendations));
  }

  // Disclaimer
  const discBox = document.createElement('div');
  discBox.className = 'disclaimer-box mt-4';
  discBox.textContent = '⚠️ AI-generated workout suggestions are for general fitness information only and are NOT a substitute for professional medical advice.';
  aiOutputBody.appendChild(discBox);
}

function renderInfoSection(title, text) {
  const sec = document.createElement('div');
  sec.className = 'plan-section';
  const t = document.createElement('div');
  t.className = 'plan-section-title';
  t.textContent = title;
  sec.appendChild(t);
  const p = document.createElement('p');
  p.className = 'text-sm';
  p.textContent = text;
  sec.appendChild(p);
  return sec;
}

/* --------------------------------------------------------------------------
   Generate workout plan
   -------------------------------------------------------------------------- */
aiForm.addEventListener('submit', async e => {
  e.preventDefault();
  const payload = buildPayload();
  if (!payload) return;

  aiGenerateBtn.disabled  = true;
  aiGenerateBtn.textContent = '⏳ Generating…';
  setStatus('Contacting IBM Granite… This may take up to 60 seconds.', 'loading');

  aiOutputBody.innerHTML = `<div class="spinner-wrap" style="min-height:200px"><div class="spinner"></div><p class="text-muted mt-3 text-sm">IBM Granite is generating your plan…</p></div>`;
  aiOutputActions.style.display = 'none';
  _lastPlan = null;

  try {
    const result = await api('/api/ai/generate', { method: 'POST', body: payload });

    if (result.success && result.plan) {
      _lastPlan    = result.plan;
      _lastRawText = result.raw_text || '';
      renderPlan(result.plan);
      setStatus('✔ Plan generated successfully!', 'success');
      aiOutputActions.style.display = '';
      btnSavePlan.disabled     = false;
      btnAddToPlanner.disabled = false;
    } else {
      throw new Error(result.error || 'Generation failed.');
    }
  } catch (err) {
    const msg = err.data?.error || err.message || 'An unexpected error occurred.';
    const raw = err.data?.raw_text || '';
    aiOutputBody.innerHTML = `
      <div class="banner banner--danger">
        <strong>❌ Error</strong>
        <p class="mt-2" style="white-space:pre-wrap">${esc(msg)}</p>
        ${raw ? `<details class="mt-3"><summary class="cursor-pointer text-sm">Show raw response</summary><pre style="white-space:pre-wrap;font-size:.8rem;margin-top:8px">${esc(raw)}</pre></details>` : ''}
      </div>`;
    setStatus('❌ Generation failed.', 'error');
  } finally {
    aiGenerateBtn.disabled  = false;
    aiGenerateBtn.textContent = '🤖 Generate AI Workout Plan';
  }
});

/* --------------------------------------------------------------------------
   Save plan
   -------------------------------------------------------------------------- */
btnSavePlan.addEventListener('click', async () => {
  if (!_lastPlan) return;
  btnSavePlan.disabled = true;
  try {
    const result = await api('/api/ai/save-plan', {
      method: 'POST',
      body: { plan: _lastPlan, raw_text: _lastRawText },
    });
    showToast(`Plan saved! You now have ${result.total_saved} saved plan(s).`, 'success');
  } catch (err) {
    showToast(err.message || 'Failed to save plan.', 'error');
  } finally {
    btnSavePlan.disabled = false;
  }
});

/* --------------------------------------------------------------------------
   Add to planner
   -------------------------------------------------------------------------- */
btnAddToPlanner.addEventListener('click', async () => {
  if (!_lastPlan) return;
  btnAddToPlanner.disabled = true;
  try {
    const result = await api('/api/ai/add-to-planner', {
      method: 'POST',
      body: { plan: _lastPlan },
    });
    showToast(`Added ${result.added} exercise(s) to the weekly planner.`, 'success');
  } catch (err) {
    showToast(err.message || 'Failed to add to planner.', 'error');
  } finally {
    btnAddToPlanner.disabled = false;
  }
});
