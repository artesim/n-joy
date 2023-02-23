from __future__ import annotations  # PEP 563: Postponed evaluation of annotations

import typing

from .elite_bindings import EliteBindings
from PySide6.QtCore import QObject
from njoy.game_models.elite_dangerous.elite_monitor import EliteMonitor

if typing.TYPE_CHECKING:
    from pathlib import Path
    import njoy.core.core as _core


class EliteModel(QObject):
    def __init__(self, *, core: _core.Core = None, game_binding_options: dict = None):
        super().__init__(parent=core)
        self.elite_monitor = EliteMonitor(self)
        self.bindings = EliteBindings(elite_model=self,
                                      hid_event_loop=core.hid_event_loop,
                                      **(game_binding_options if game_binding_options else {}))

    def generate_bindings(self, bindings_file: Path = None):
        self.bindings.generate_bindings(bindings_file=bindings_file)
