# EduTrack Student Management System

A responsive Flask student-management system with an animated homepage, a persistent SQLite database, and a live student directory.

## Run locally

```powershell
cd C:\Users\DELL\Documents\Codex\2026-09-13\cr\outputs\student-management-system
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

Open `http://127.0.0.1:5000` in your browser.

## Included API

- `GET /api/students?q=` — list or search students
- `POST /api/students` — add a student with JSON `name`, `course`, and optional `status`
- `PUT /api/students/:id` — update a student
- `DELETE /api/students/:id` — delete a student
- `GET /api/summary` — dashboard totals

Student data is stored in `edutrack.db`, created automatically at the first run. For production, add login, role permissions, attendance, and grade models.
