const gradeSelect = document.querySelector('#attendance-grade');
const dateInput = document.querySelector('#attendance-date');
const list = document.querySelector('#attendance-list');
const summary = document.querySelector('#attendance-summary');
let records = [];

dateInput.value = new Date().toLocaleDateString('en-CA');

function render() {
  list.innerHTML = records.length ? records.map((student, index) => `<div class="attendance-row"><span class="roll">${String(index + 1).padStart(2, '0')}</span><span class="attendance-avatar">${student.name.split(' ').map(word => word[0]).join('').slice(0, 2)}</span><div><b>${student.name}</b><small>Class ${gradeSelect.value}-${student.section}</small></div><div class="status-buttons"><button data-id="${student.id}" data-status="Present" class="${student.status === 'Present' ? 'chosen present' : ''}">Present</button><button data-id="${student.id}" data-status="Late" class="${student.status === 'Late' ? 'chosen late' : ''}">Late</button><button data-id="${student.id}" data-status="Absent" class="${student.status === 'Absent' ? 'chosen absent' : ''}">Absent</button></div></div>`).join('') : '<p class="empty">No active students in this class yet. Add them from Student Profiles.</p>';
  const completed = records.filter(record => record.status).length;
  summary.textContent = `${completed} of ${records.length} students marked`;
}

async function load() {
  list.innerHTML = '<p class="empty">Loading class register…</p>';
  records = await (await fetch(`/api/attendance?grade=${gradeSelect.value}&date=${dateInput.value}`)).json();
  render();
}

list.addEventListener('click', event => {
  const id = Number(event.target.dataset.id), status = event.target.dataset.status;
  if (!id || !status) return;
  records = records.map(record => record.id === id ? { ...record, status } : record); render();
});
gradeSelect.addEventListener('change', load); dateInput.addEventListener('change', load);
document.querySelector('#save-attendance').addEventListener('click', async () => {
  const marked = records.filter(record => record.status).map(record => ({ id: record.id, status: record.status }));
  if (!marked.length) { summary.textContent = 'Mark at least one student before saving.'; return; }
  const response = await fetch('/api/attendance', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ date: dateInput.value, records: marked }) });
  const data = await response.json(); summary.textContent = response.ok ? `${data.saved} attendance records saved successfully.` : data.error;
});
load().catch(() => { list.innerHTML = '<p class="empty">Unable to load attendance. Check that the server is running.</p>'; });
