import json
from datetime import datetime
from pathlib import Path

TRACKER_PATH = Path(__file__).parent.parent / "data" / "applications.json"

VALID_STATUSES = {"applied", "interview", "offer", "rejected", "withdrawn"}


class ApplicationTracker:
    def __init__(self):
        TRACKER_PATH.parent.mkdir(parents=True, exist_ok=True)

    def _load(self) -> list:
        if not TRACKER_PATH.exists():
            return []
        return json.loads(TRACKER_PATH.read_text())

    def _save(self, apps: list) -> None:
        TRACKER_PATH.write_text(json.dumps(apps, indent=2, ensure_ascii=False))

    def add(self, company: str, role: str, files: dict) -> str:
        apps = self._load()
        app_id = f"{len(apps) + 1:04d}"
        apps.append(
            {
                "id": app_id,
                "company": company,
                "role": role,
                "applied_at": datetime.now().isoformat(timespec="seconds"),
                "status": "applied",
                "files": files,
            }
        )
        self._save(apps)
        return app_id

    def update_status(self, app_id: str, status: str) -> None:
        if status not in VALID_STATUSES:
            raise ValueError(f"Status must be one of: {', '.join(sorted(VALID_STATUSES))}")
        apps = self._load()
        for app in apps:
            if app["id"] == app_id:
                app["status"] = status
                app["updated_at"] = datetime.now().isoformat(timespec="seconds")
                self._save(apps)
                print(f"Application {app_id} ({app['role']} @ {app['company']}) → {status}")
                return
        raise ValueError(f"Application ID '{app_id}' not found.")

    def display(self) -> None:
        apps = self._load()
        if not apps:
            print("No applications tracked yet.")
            return

        status_icons = {
            "applied": "📤",
            "interview": "🗓 ",
            "offer": "🎉",
            "rejected": "❌",
            "withdrawn": "↩ ",
        }

        col = "{:<6} {:<28} {:<32} {:<14} {}"
        print()
        print(col.format("ID", "Company", "Role", "Status", "Date"))
        print("─" * 90)
        for app in apps:
            icon = status_icons.get(app["status"], "  ")
            date = app["applied_at"][:10]
            print(
                col.format(
                    app["id"],
                    app["company"][:27],
                    app["role"][:31],
                    f"{icon} {app['status']}",
                    date,
                )
            )
        print()
