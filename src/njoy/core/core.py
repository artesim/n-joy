from __future__ import annotations  # PEP 563: Postponed evaluation of annotations

import typing

from njoy.hid_devices.hid_event_loop import HIDEventLoop
from njoy.game_models.elite_dangerous.elite_model import EliteModel
from PySide6.QtCore import QCoreApplication

if typing.TYPE_CHECKING:
    from njoy.hid_devices.hid_controls import InputAxis, OutputAxis
    from njoy.hid_devices.hid_controls import InputButton, OutputButton
    from njoy.hid_devices.vjoy_interface import vJoyId


class Core(QCoreApplication):
    def __init__(self, game_binding_options: dict = None):
        super().__init__()
        self.hid_event_loop = HIDEventLoop()
        self.game_model = EliteModel(core=self,
                                     game_binding_options=game_binding_options)

    def physical_axis(self, ident: str, axis: int) -> InputAxis:
        return self.hid_event_loop.physical_axis(ident, axis)

    def physical_button(self, ident: str, button: int) -> InputButton:
        """Find and return a PhysicalButton instance for button 'BUTTON' of device 'IDENT'.
        Physical buttons are read-only, they have no 'set_state' slot, they only emit signals."""
        return self.hid_event_loop.physical_button(ident, button)

    def virtual_axis(self, ident: vJoyId, axis: int, *, enable_output: bool = False) -> InputAxis | OutputAxis:
        return self.hid_event_loop.virtual_axis(ident, axis, enable_output=enable_output)

    def virtual_button(self, ident: vJoyId, button: int, *, enable_output: bool = False) -> InputButton | OutputButton:
        """Find and return a VirtualButton instance for button 'BUTTON' of virtual device number 'IDENT'.
        Virtual buttons are read-only by default, and only emit signals, just like physical buttons.
        If you want to control their state, set the 'enable_output' parameter to True, and connect
        a signal to its 'set_state' slot.
        """
        return self.hid_event_loop.virtual_button(ident, button, enable_output=enable_output)

    def start(self):
        self.game_model.generate_bindings()
        self.exec()
