from __future__ import annotations

import sys
from pathlib import Path

from PyQt6.QtCore import QEvent
from PyQt6.QtWidgets import QApplication

from settings import load_settings
from ui import PrepCutWindow


class PrepCutApplication(QApplication):
    def __init__(self, argv: list[str]) -> None:
        super().__init__(argv)
        self.window: PrepCutWindow | None = None
        self.pending_icon_drop_files: list[Path] = []

    def event(self, event: QEvent) -> bool:
        if event.type() == QEvent.Type.FileOpen and hasattr(event, "file"):
            path = Path(event.file())
            if self.window:
                self.window.add_files_from_app_icon([path])
            else:
                self.pending_icon_drop_files.append(path)
            return True
        return super().event(event)


def main() -> int:
    app = PrepCutApplication(sys.argv)
    settings = load_settings()
    window = PrepCutWindow(settings)
    app.window = window
    window.show()

    launch_files = [Path(arg) for arg in sys.argv[1:] if Path(arg).is_file()]
    pending_files = app.pending_icon_drop_files + launch_files
    if pending_files:
        window.add_files_from_app_icon(pending_files)

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
