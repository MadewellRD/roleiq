# RoleIQ Go-Live Tracker — pointer

Pinned artifact: https://claude.ai/code/artifact/8d56d82a-1bda-4a71-a8db-8869274ecea8

State lives in `tracker.json`. `tracker.html` is a generated view, built by `scripts/build_tracker.py`. To update the tracker after a merge:

```
.venv\Scripts\python.exe scripts\build_tracker.py
```

Then republish the artifact at `docs/engineering-spec/tracker.html` (same path — this keeps the URL above, per the go-live protocol's "one tracker per project, forever" rule). Never publish from a different path; that creates a second artifact instead of updating this one.
