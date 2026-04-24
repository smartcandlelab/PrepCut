# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PyQt6.QtCore import QObject, Qt, QThread, pyqtSignal
from PyQt6.QtGui import QDragEnterEvent, QDropEvent
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFrame,
    QGroupBox,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QRadioButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from processor import ProcessingError, find_tool, process_file
from settings import (
    AUDIO_AAC,
    AUDIO_PCM_16,
    UNSUPPORTED_FAIL,
    UNSUPPORTED_PRORES_422,
    UNSUPPORTED_PRORES_LT,
    PrepCutSettings,
    display_path,
    reset_output_folder,
    save_settings,
)


APP_ICON_DROP_EXTENSIONS = {".mov", ".mp4", ".m4v", ".mkv", ".webm", ".avi"}


@dataclass
class QueueItem:
    path: Path
    row: int


class DropArea(QFrame):
    files_dropped = pyqtSignal(list)

    def __init__(self) -> None:
        super().__init__()
        self.setAcceptDrops(True)
        self.setObjectName("dropArea")
        self.setMinimumHeight(150)

        layout = QVBoxLayout(self)
        label = QLabel("Drop video files here")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setObjectName("dropLabel")
        layout.addWidget(label)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        paths = [
            Path(url.toLocalFile())
            for url in event.mimeData().urls()
            if url.isLocalFile()
        ]
        if paths:
            self.files_dropped.emit(paths)
        event.acceptProposedAction()


class SettingsDialog(QDialog):
    def __init__(self, settings: PrepCutSettings, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setModal(True)
        self.settings = settings

        self.audio_aac = QRadioButton("AAC")
        self.audio_pcm = QRadioButton("Lossless PCM 16-bit")

        self.video_fail = QRadioButton("Fail")
        self.video_prores_lt = QRadioButton("Convert to ProRes LT")
        self.video_prores_422 = QRadioButton("Convert to ProRes 422")

        self.emergency_mode = QCheckBox("Enable Emergency Mode")

        self._build_layout()
        self._load_controls()

    def _build_layout(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        audio_group = QGroupBox("Audio conversion when audio is incompatible")
        audio_layout = QVBoxLayout(audio_group)
        audio_layout.addWidget(self.audio_aac)
        audio_layout.addWidget(self.audio_pcm)
        audio_note = QLabel("Lossless PCM may significantly increase file size.")
        audio_note.setWordWrap(True)
        audio_note.setObjectName("noteLabel")
        audio_layout.addWidget(audio_note)

        video_group = QGroupBox("Unsupported video handling")
        video_layout = QVBoxLayout(video_group)
        video_layout.addWidget(self.video_fail)
        video_layout.addWidget(self.video_prores_lt)
        video_layout.addWidget(self.video_prores_422)
        video_note = QLabel(
            "ProRes conversion is significantly faster on Pro/Max/Ultra Apple Silicon chips."
        )
        video_note.setWordWrap(True)
        video_note.setObjectName("noteLabel")
        video_layout.addWidget(video_note)

        emergency_group = QGroupBox("Emergency Mode")
        emergency_layout = QVBoxLayout(emergency_group)
        emergency_layout.addWidget(self.emergency_mode)
        emergency_note = QLabel(
            "Emergency Mode forces full conversion to ProRes + PCM. "
            "This ensures compatibility but increases file size."
        )
        emergency_note.setWordWrap(True)
        emergency_note.setObjectName("noteLabel")
        emergency_layout.addWidget(emergency_note)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Reset
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        buttons.button(QDialogButtonBox.StandardButton.Reset).setText(
            "Reset to Defaults"
        )
        buttons.button(QDialogButtonBox.StandardButton.Reset).clicked.connect(
            self._reset_controls
        )

        layout.addWidget(audio_group)
        layout.addWidget(video_group)
        layout.addWidget(emergency_group)
        layout.addWidget(buttons)

        self.setStyleSheet(
            """
            QDialog,
            QWidget {
                background: #f5f5f5;
                color: #2f2f2f;
            }
            QGroupBox {
                border: 1px solid #c8c8c8;
                border-radius: 6px;
                margin-top: 8px;
                padding: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 4px;
            }
            #noteLabel {
                color: #555555;
            }
            QPushButton {
                background: #ffffff;
                border: 1px solid #a8a8a8;
                border-radius: 6px;
                color: #222222;
                min-height: 28px;
                padding: 4px 12px;
            }
            """
        )

    def _load_controls(self) -> None:
        self.audio_aac.setChecked(self.settings.audio_mode == AUDIO_AAC)
        self.audio_pcm.setChecked(self.settings.audio_mode == AUDIO_PCM_16)

        self.video_fail.setChecked(
            self.settings.unsupported_video_mode == UNSUPPORTED_FAIL
        )
        self.video_prores_lt.setChecked(
            self.settings.unsupported_video_mode == UNSUPPORTED_PRORES_LT
        )
        self.video_prores_422.setChecked(
            self.settings.unsupported_video_mode == UNSUPPORTED_PRORES_422
        )

        self.emergency_mode.setChecked(self.settings.emergency_mode)

    def _reset_controls(self) -> None:
        self.audio_aac.setChecked(True)
        self.video_fail.setChecked(True)
        self.emergency_mode.setChecked(False)

    def selected_audio_mode(self) -> str:
        return AUDIO_PCM_16 if self.audio_pcm.isChecked() else AUDIO_AAC

    def selected_unsupported_video_mode(self) -> str:
        if self.video_prores_lt.isChecked():
            return UNSUPPORTED_PRORES_LT
        if self.video_prores_422.isChecked():
            return UNSUPPORTED_PRORES_422
        return UNSUPPORTED_FAIL


class FileWorker(QObject):
    finished = pyqtSignal(int, bool, str)

    def __init__(self, row: int, input_path: Path, settings: PrepCutSettings) -> None:
        super().__init__()
        self.row = row
        self.input_path = input_path
        self.settings = settings

    def run(self) -> None:
        try:
            result = process_file(
                self.input_path,
                self.settings.output_dir,
                self.settings,
            )
        except ProcessingError as exc:
            self.finished.emit(self.row, False, str(exc))
        except Exception:
            self.finished.emit(self.row, False, "File cannot be read.")
        else:
            self.finished.emit(self.row, True, result.output_path.name)


class PrepCutWindow(QMainWindow):
    def __init__(self, settings: PrepCutSettings) -> None:
        super().__init__()
        self.setWindowTitle("PrepCut")
        self.resize(720, 500)

        self.settings = settings
        self.queue: list[QueueItem] = []
        self.processing = False
        self.current_thread: QThread | None = None
        self.current_worker: FileWorker | None = None

        self.drop_area = DropArea()
        self.drop_area.files_dropped.connect(self.add_files)

        self.output_label = QLabel()
        self.output_label.setObjectName("outputLabel")
        self.output_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )

        self.change_output_button = QPushButton("Change Output Folder")
        self.change_output_button.clicked.connect(self.choose_output_folder)
        self.reset_output_button = QPushButton("Reset Output Folder to Default")
        self.reset_output_button.clicked.connect(self.reset_output_to_default)
        self.settings_button = QPushButton("Settings")
        self.settings_button.clicked.connect(self.open_settings)

        self.emergency_warning = QLabel("Emergency Mode ON")
        self.emergency_warning.setObjectName("emergencyWarning")
        self.emergency_warning.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["File", "Status"])
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)

        self.message_label = QLabel()
        self.message_label.setObjectName("messageLabel")

        self._build_layout()
        self._apply_styles()
        self.refresh_output_label()
        self.refresh_emergency_warning()
        self.refresh_tool_status()

    def _build_layout(self) -> None:
        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        output_layout = QHBoxLayout()
        output_title = QLabel("Output folder:")
        output_layout.addWidget(output_title)
        output_layout.addWidget(self.output_label, 1)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.change_output_button)
        button_layout.addWidget(self.reset_output_button)
        button_layout.addWidget(self.settings_button)
        button_layout.addStretch(1)

        layout.addWidget(self.drop_area)
        layout.addLayout(output_layout)
        layout.addLayout(button_layout)
        layout.addWidget(self.emergency_warning)
        layout.addWidget(self.table, 1)
        layout.addWidget(self.message_label)

        self.setCentralWidget(central)

    def _apply_styles(self) -> None:
        self.setStyleSheet(
            """
            QMainWindow,
            QWidget {
                background: #f5f5f5;
                color: #2f2f2f;
            }
            #dropArea {
                background: #ffffff;
                border: 2px dashed #8a8a8a;
                border-radius: 8px;
            }
            #dropLabel {
                color: #333333;
                font-size: 20px;
                font-weight: 600;
            }
            #outputLabel {
                color: #222222;
                font-weight: 600;
            }
            #emergencyWarning {
                background: #b00020;
                border-radius: 6px;
                color: #ffffff;
                font-weight: 700;
                min-height: 28px;
            }
            QPushButton {
                background: #ffffff;
                border: 1px solid #a8a8a8;
                border-radius: 6px;
                color: #222222;
                min-height: 30px;
                padding: 4px 12px;
            }
            QPushButton:hover {
                background: #eeeeee;
            }
            QPushButton:pressed {
                background: #e0e0e0;
            }
            QTableWidget {
                background: #ffffff;
                border: 1px solid #d0d0d0;
                color: #222222;
            }
            QHeaderView::section {
                background: #303030;
                color: #ffffff;
                font-weight: 600;
                padding: 4px;
            }
            #messageLabel {
                color: #555555;
            }
            """
        )

    def choose_output_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Change Output Folder")
        if not folder:
            return

        self.settings.output_dir = Path(folder)
        self.settings.output_dir.mkdir(parents=True, exist_ok=True)
        save_settings(self.settings)
        self.refresh_output_label()
        self.message_label.setText("Output folder updated.")
        self.start_next_if_ready()

    def reset_output_to_default(self) -> None:
        reset_output_folder(self.settings)
        save_settings(self.settings)
        self.refresh_output_label()
        self.message_label.setText("Output folder reset to ~/Movies/PrepCut.")
        self.start_next_if_ready()

    def open_settings(self) -> None:
        dialog = SettingsDialog(self.settings, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        self.settings.audio_mode = dialog.selected_audio_mode()
        self.settings.unsupported_video_mode = dialog.selected_unsupported_video_mode()
        self.settings.emergency_mode = dialog.emergency_mode.isChecked()
        save_settings(self.settings)
        self.refresh_emergency_warning()
        self.message_label.setText("Settings updated.")

    def add_files_from_app_icon(self, paths: list[Path]) -> None:
        supported_paths = [
            path for path in paths if path.suffix.lower() in APP_ICON_DROP_EXTENSIONS
        ]
        if not supported_paths:
            return

        self.settings.emergency_mode = False
        save_settings(self.settings)
        self.refresh_emergency_warning()
        self.add_files(supported_paths)

    def add_files(self, paths: list[Path]) -> None:
        for path in paths:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(path.name))
            self.set_status(row, "queued")
            self.queue.append(QueueItem(path=path, row=row))

        self.start_next_if_ready()

    def start_next_if_ready(self) -> None:
        if self.processing or not self.queue:
            return

        item = self.queue.pop(0)
        self.processing = True
        self.set_status(item.row, "processing")

        # Each ffmpeg run happens off the UI thread, while this method keeps
        # the queue strictly one-file-at-a-time.
        thread = QThread(self)
        worker = FileWorker(item.row, item.path, self.settings_snapshot())
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.finished.connect(self.file_finished)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self.thread_finished)

        self.current_thread = thread
        self.current_worker = worker
        thread.start()

    def file_finished(self, row: int, success: bool, message: str) -> None:
        if success:
            self.set_status(row, "done", f"Output: {message}")
            self.message_label.setText(f"Done: {message}")
        else:
            self.set_status(row, "failed", message)
            self.message_label.setText(message)

    def thread_finished(self) -> None:
        self.processing = False
        self.current_thread = None
        self.current_worker = None
        self.start_next_if_ready()

    def set_status(self, row: int, status: str, tooltip: str | None = None) -> None:
        item = QTableWidgetItem(status)
        if tooltip:
            item.setToolTip(tooltip)
        self.table.setItem(row, 1, item)

    def refresh_output_label(self) -> None:
        self.output_label.setText(display_path(self.settings.output_dir))

    def refresh_emergency_warning(self) -> None:
        self.emergency_warning.setVisible(self.settings.emergency_mode)

    def refresh_tool_status(self) -> None:
        missing = [
            name for name in ("ffmpeg", "ffprobe") if find_tool(name) is None
        ]
        if missing:
            self.message_label.setText(
                "ffmpeg/ffprobe not found. Place binaries in ./vendor/ffmpeg/ "
                "or install them on PATH."
            )
        else:
            self.message_label.setText("Drop files to process them.")

    def settings_snapshot(self) -> PrepCutSettings:
        return PrepCutSettings(
            output_dir=self.settings.output_dir,
            audio_mode=self.settings.audio_mode,
            unsupported_video_mode=self.settings.unsupported_video_mode,
            emergency_mode=self.settings.emergency_mode,
        )
