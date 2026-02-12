## PermissionError (logs/activity.log)
- Symptom: PermissionError when writing logs/activity.log
- Root cause: logs/activity.log existed as an empty DIRECTORY, so open() failed
- Fix: rmdir logs/activity.log -> recreate as file -> append OK
- Evidence: activity.log has records for A0001, A0002; E2E A0002 created successfully
- Note: _append_line is already correct (mkdir(exist_ok=True) + utf-8 append). No code patch needed.
