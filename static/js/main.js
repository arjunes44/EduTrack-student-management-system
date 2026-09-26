const modal = document.querySelector('#student-modal');
const form = document.querySelector('#student-form');
const message = form.querySelector('.form-message');
const directory = document.querySelector('#student-directory');
let studentMap = new Map();
const initials = name => name.split(' ').map(part => part[0]).join('').slice(0, 2).toUpperCase();
const escapeHtml = value => String(value).replace(/[&<>'"]/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' })[char]);

const nameLabel = form.querySelector('input[name="name"]').closest('label');
nameLabel.insertAdjacentHTML('beforebegin', '<label>Student photo <input class="photo-input" type="file" name="photo" accept="image/png,image/jpeg,image/webp"></label>');

function updateClock() {
  const clock = document.querySelector('#live-clock');
  if (clock) clock.textContent = new Intl.DateTimeFormat([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }).format(new Date());
}
async function loadActivity() {
  const feed = document.querySelector('#activity-feed');
  if (!feed) return;
  const activities = await (await fetch('/api/activity')).json();
  feed.innerHTML = activities.length ? activities.map((item, index) => `<div class="activity-item" style="animation-delay:${index * 70}ms"><span class="activity-icon">✦</span><div><b>${escapeHtml(item.title)}</b><small>${escapeHtml(item.detail)}</small></div><time>Just added</time></div>`).join('') : '<p class="empty">No recent activity yet.</p>';
}

function showModal(student = null) {
  form.reset(); message.textContent = '';
  form.elements.id.value = student?.id || ''; form.elements.name.value = student?.name || '';
  form.elements.course.value = student?.course || ''; form.elements.grade.value = student?.grade || '1';
  form.elements.section.value = student?.section || 'A'; form.elements.guardian.value = student?.guardian || '';
  form.elements.phone.value = student?.phone || ''; form.elements.status.value = student?.status || 'Active';
  document.querySelector('#form-title').textContent = student ? 'Edit student' : 'Add a new student';
  modal.classList.add('open'); form.elements.name.focus();
}
function studentMarkup(student, compact = false) {
  const controls = compact ? '' : `<div class="student-actions"><button data-edit="${student.id}">Edit</button><button class="delete" data-delete="${student.id}">Delete</button></div>`;
  const portrait = student.photo ? `<img class="student-photo" src="/static/uploads/${encodeURIComponent(student.photo)}" alt="${escapeHtml(student.name)}">` : `<span class="avatar a${student.id % 2 + 1}">${initials(student.name)}</span>`;
  return `<div class="student">${portrait}<b>${escapeHtml(student.name)}</b><small>Class ${escapeHtml(student.grade)}${student.section ? `-${escapeHtml(student.section)}` : ''} · ${escapeHtml(student.course)}</small><em>${escapeHtml(student.status)}</em>${controls}</div>`;
}
async function loadStudents(query = '') {
  const studentsResponse = await fetch(`/api/students?q=${encodeURIComponent(query)}`);
  const students = await studentsResponse.json(); studentMap = new Map(students.map(student => [String(student.id), student]));
  directory.innerHTML = students.length ? students.map(student => studentMarkup(student)).join('') : '<p class="empty">No students found.</p>';
  const recent = document.querySelector('#recent-students');
  if (!recent) return;
  const summary = await (await fetch('/api/summary')).json();
  recent.innerHTML = students.slice(0, 2).map(student => studentMarkup(student, true)).join('') || '<small>No students yet.</small>';
  document.querySelector('#total-students').textContent = summary.total; document.querySelector('#metric-total').textContent = summary.total;
  document.querySelector('#metric-active').textContent = summary.active; document.querySelector('#active-students').textContent = `${summary.active} active`;
}
document.querySelector('#open-modal').addEventListener('click', () => showModal());
document.querySelector('.close').addEventListener('click', () => modal.classList.remove('open'));
modal.addEventListener('click', event => { if (event.target === modal) modal.classList.remove('open'); });
document.querySelector('#student-search').addEventListener('input', event => loadStudents(event.target.value));
directory.addEventListener('click', async event => {
  if (event.target.dataset.edit) showModal(studentMap.get(event.target.dataset.edit));
  const id = event.target.dataset.delete;
  if (id && confirm('Delete this student?')) { await fetch(`/api/students/${id}`, { method: 'DELETE' }); loadStudents(); }
});
form.addEventListener('submit', async event => {
  event.preventDefault(); const body = new FormData(form); const id = body.get('id'); body.delete('id');
  try {
    const response = await fetch(id ? `/api/students/${id}` : '/api/students', { method: id ? 'PUT' : 'POST', body });
    const result = await response.json(); if (!response.ok) throw new Error(result.error || 'Could not save student.');
    modal.classList.remove('open'); loadStudents();
  } catch (error) { message.textContent = error.message; message.style.color = '#b34d4d'; }
});
loadStudents().catch(() => { directory.innerHTML = '<p class="empty">Unable to connect to the server.</p>'; });
loadActivity().catch(() => {}); updateClock(); setInterval(updateClock, 1000);
