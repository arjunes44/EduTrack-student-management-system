# Publish EduTrack free with PythonAnywhere

PythonAnywhere's free plan can host one Flask web app and keep the SQLite database file, which makes it a better fit for this student-management project than hosts that reset local files.

## 1. Create the free host

1. Create a free account at https://www.pythonanywhere.com/.
2. Open **Web** and choose **Add a new web app**.
3. Use the free address `YOUR_USERNAME.pythonanywhere.com`.
4. Select **Flask** and select the newest Python version offered.

## 2. Upload this project

Use the **Files** tab to create this folder:

```text
/home/YOUR_USERNAME/edutrack
```

Upload every project item into it, preserving these folders:

```text
app.py
requirements.txt
templates/index.html
templates/module.html
static/css/
static/js/
```

Do not upload `edutrack.db`; the app creates a new database automatically when it first starts.

## 3. Install Flask

Open **Consoles** → **Bash**, then run:

```bash
cd ~/edutrack
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 4. Configure the web app

Return to **Web**:

1. Set the **Virtualenv** field to `/home/YOUR_USERNAME/edutrack/.venv`.
2. Click the WSGI configuration file link and replace its contents with:

```python
import sys

project_path = '/home/YOUR_USERNAME/edutrack'
if project_path not in sys.path:
    sys.path.insert(0, project_path)

from app import app as application
```

3. In **Static files**, add this mapping:

```text
URL: /static/
Directory: /home/YOUR_USERNAME/edutrack/static/
```

4. Click **Reload**.

Your public site will be live at:

```text
https://YOUR_USERNAME.pythonanywhere.com
```

## Updating later

Upload changed files, then click **Reload** in the Web tab. The student and attendance records remain in `edutrack.db`.
