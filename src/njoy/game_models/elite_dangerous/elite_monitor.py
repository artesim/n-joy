from __future__ import annotations  # PEP 563: Postponed evaluation of annotations

import collections
import json
import time

from .elite_controls import StatusFlags, LegalStatus, GuiFocus
from .elite_controls import FlagInput, GuiFocusInput, LegalStatusInput
from datetime import datetime, timezone
from pathlib import Path
from PySide6.QtCore import QObject, Signal, Slot, QFileSystemWatcher


class EliteMonitor(QObject):
    """Monitors the state of Elite Dangerous using several of its log files, and emits Qt signals when it changes."""

    __LOG_DIR__ = Path.home() / 'Saved Games' / 'Frontier Developments' / 'Elite Dangerous'

    journal_file_changed = Signal()
    status_file_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._watcher = QFileSystemWatcher(self)

        self._active_journal = self._find_active_journal()
        self.journal_file_changed.connect(self._active_journal.on_journal_file_changed)

        self.elite_status = EliteStatus(status_file=self.__LOG_DIR__ / 'Status.json', parent=self)
        self.status_file_changed.connect(self.elite_status.on_status_file_changed)

        self._watcher.directoryChanged.connect(self.on_directory_changed)
        self._watcher.fileChanged.connect(self.on_file_changed)
        self._watcher.addPaths([str(self.__LOG_DIR__),
                                str(self._active_journal.latest_part()),
                                str(self.elite_status.status_file)])

    @Slot()
    def on_directory_changed(self, _):
        current_journal = self._active_journal
        new_journal = self._find_active_journal()

        if new_journal.timestamp != current_journal.timestamp:
            # This is a new journal
            self._active_journal = new_journal
            self.journal_file_changed.connect(self._active_journal.on_journal_file_changed)
            self.journal_file_changed.disconnect(current_journal.on_journal_file_changed)
            self._watcher.removePath(str(current_journal.latest_part()))
            self._watcher.addPath(str(self._active_journal.latest_part()))

        elif new_journal.latest_part() != current_journal.latest_part():
            # This is just a new part of the same journal
            self._watcher.removePath(str(self._active_journal.latest_part()))
            self._active_journal.add_part(new_journal.latest_part())
            self._watcher.addPath(str(self._active_journal.latest_part()))

        else:
            pass  # Unrelated change, ignoring

    @Slot()
    def on_file_changed(self, path):
        ppath = Path(path)

        if not ppath.exists():
            return  # File simply removed

        if path not in self._watcher.files():
            # Probably updated by CopyOnWrite, or log rotation : re-adding it
            self._watcher.addPath(path)

        if self._active_journal.has_part(ppath):
            self.journal_file_changed.emit()

        if ppath == self.elite_status.status_file:
            self.status_file_changed.emit()

    def _find_active_journal(self) -> SessionJournal:
        # First read all the journal headers and group them by timestamp
        timestamp_groups = collections.defaultdict(list)
        for journal_file in self.__LOG_DIR__.glob('Journal*.log'):
            header = self._journal_file_header(journal_file)
            timestamp_groups[header['timestamp']].append(header)

        # Build and return a SessionJournal with the last group of journal files
        last_timestamp = max(timestamp_groups.keys())
        last_group_parts = [header['journal_file'] for header in sorted(timestamp_groups[last_timestamp],
                                                                        key=lambda h: h['part'])]
        return SessionJournal(timestamp=last_timestamp,
                              parts=last_group_parts,
                              parent=self)

    @staticmethod
    def _journal_file_header(journal_file: Path) -> dict:
        while True:
            try:
                with journal_file.open() as f:
                    header = json.loads(f.readline())
                    if 'event' not in header:
                        raise ValueError
                    if header['event'].lower() != 'fileheader':
                        raise ValueError
                    return {'journal_file': journal_file,
                            'timestamp': datetime.fromisoformat(header['timestamp']),
                            'part': header['part']}
            except json.JSONDecodeError:
                # FIXME: understand why the json is temporarily malformed while ED is starting a game
                time.sleep(0.250)
                continue


class SessionJournal(QObject):
    journal_event = Signal(dict)

    def __init__(self, timestamp: datetime, parts: list[Path], parent=None):
        super().__init__(parent)
        self.timestamp = timestamp
        self.parts = parts
        self._idx_current_part = 0
        self._last_processed: datetime = datetime.utcfromtimestamp(0).replace(tzinfo=timezone.utc)  # epoch

    def __repr__(self):
        return f'<SessionJournal {self.timestamp}>'

    def add_part(self, part: Path):
        self.parts.append(part)

    def has_part(self, part: Path) -> bool:
        return part in self.parts

    def latest_part(self) -> Path:
        return self.parts[-1]

    @Slot()
    def on_journal_file_changed(self):
        for i in range(self._idx_current_part, len(self.parts)):
            for entry_str in self.parts[i].read_text().splitlines():
                entry = json.loads(entry_str)
                entry['timestamp'] = datetime.fromisoformat(entry['timestamp'])
                if entry['timestamp'] >= self._last_processed:
                    self.journal_event.emit(entry)
                    self._last_processed = entry['timestamp']
        self._idx_current_part = len(self.parts) - 1


class EliteStatus(QObject):
    status_event = Signal(dict)

    def __init__(self, status_file: Path, parent=None):
        super().__init__(parent)
        self.status_file = status_file

        self.flags: dict[StatusFlags, FlagInput] = {flag: FlagInput(parent=self,
                                                                    status_flag=flag)
                                                    for flag in StatusFlags}
        for control in self.flags.values():
            self.status_event.connect(control.on_status_event)

        self.gui_focus: GuiFocusInput = GuiFocusInput(parent=self)
        self.status_event.connect(self.gui_focus.on_status_event)

        self.legal_status: LegalStatusInput = LegalStatusInput(parent=self)
        self.status_event.connect(self.legal_status.on_status_event)

    def _read_status_file(self) -> dict | None:
        status_data = self.status_file.read_text()
        if not status_data:
            return None
        entry = json.loads(status_data.splitlines()[0])

        entry['timestamp'] = datetime.fromisoformat(entry['timestamp'])

        entry['Flags'] = StatusFlags((entry.get('Flags2', 0) << 32) + entry.get('Flags', 0))
        if 'Flags2' in entry:
            del entry['Flags2']

        if 'GuiFocus' in entry:
            entry['GuiFocus'] = GuiFocus(entry['GuiFocus'])

        if 'LegalStatus' in entry:
            entry['LegalStatus'] = LegalStatus(entry['LegalStatus'])

        return entry

    @Slot()
    def on_status_file_changed(self):
        if status := self._read_status_file():
            self.status_event.emit(status)
