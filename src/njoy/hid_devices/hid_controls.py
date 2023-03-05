from __future__ import annotations  # PEP 563: Postponed evaluation of annotations

import sdl2
import typing

from njoy.core.controls import InputAxisInterface, OutputAxisInterface
from njoy.core.controls import InputButtonInterface, OutputButtonInterface, OutputSwitchMixin, OutputPulseMixin
from PySide6.QtCore import Slot

if typing.TYPE_CHECKING:
    from .hid_device import HIDDevice, VirtualDevice


class InputAxis(InputAxisInterface):
    def __init__(self, *, device: HIDDevice | VirtualDevice, axis_id: int):
        super().__init__(parent=device)
        self.device: HIDDevice | VirtualDevice = device
        self.axis_id = axis_id

    def __repr__(self):
        return f'<{self.__class__.__name__} #{self.axis_id} of {self.device.name}>'

    def _get_value(self) -> float:
        return self.device.get_axis_value(self.axis_id)

    def process_event(self, event: sdl2.SDL_Event):
        if event.type == sdl2.SDL_JOYAXISMOTION:
            self.moved_signal.emit(2 * (event.jaxis.value + 0x8000) / 0xFFFF - 1)


class OutputAxis(OutputAxisInterface):
    def __init__(self, *, device: VirtualDevice, axis_id: int):
        super().__init__(parent=device)
        self.device: HIDDevice | VirtualDevice = device
        self.axis_id = axis_id

    def __repr__(self):
        return f'<{self.__class__.__name__} #{self.axis_id} of {self.device.name}>'

    def _get_value(self) -> float:
        return self.device.get_axis_value(self.axis_id)

    def _set_value(self, value: float):
        self.device.set_axis(self.axis_id, value)

    def process_event(self, event: sdl2.SDL_Event):
        if event.type == sdl2.SDL_JOYAXISMOTION:
            self.moved_signal.emit(2 * (event.jaxis.value + 0x8000) / 0xFFFF - 1)


class InputButton(InputButtonInterface):
    def __init__(self, *, device: HIDDevice | VirtualDevice, button_id: int):
        super().__init__(parent=device)
        self.device: HIDDevice | VirtualDevice = device
        self.button_id = button_id

    def __repr__(self):
        return f'<{self.__class__.__name__} #{self.button_id} of {self.device.name}>'

    def _get_state(self) -> bool:
        return self.device.get_button_state(self.button_id)

    def process_event(self, event: sdl2.SDL_Event):
        if event.type == sdl2.SDL_JOYBUTTONDOWN:
            self.pressed_signal.emit()
        if event.type == sdl2.SDL_JOYBUTTONUP:
            self.released_signal.emit()
        self.switched_signal.emit(event.jbutton.state == 1)


class OutputButton(OutputButtonInterface, OutputSwitchMixin, OutputPulseMixin):
    def __init__(self, *, device: VirtualDevice, button_id: int):
        super().__init__(parent=device)
        self.device: HIDDevice | VirtualDevice = device
        self.button_id = button_id

    def __repr__(self):
        return f'<{self.__class__.__name__} #{self.button_id} of {self.device.name}>'

    def _get_state(self) -> bool:
        return self.device.get_button_state(self.button_id)

    def _set_state(self, state: bool):
        return self.device.set_button(self.button_id, state)

    @Slot(bool)
    def switch(self, target_state: bool = None):
        if target_state is not None and target_state == self.state:
            return
        self.device.set_button(self.button_id, target_state or not self.state)

    @Slot(bool)
    def pulse(self, target_state: bool = None):
        if target_state is not None and target_state == self.state:
            return
        target = target_state if target_state is not None else not self.state
        self.device.set_button(self.button_id, target)
        (self._pulse_on_timer if target else self._pulse_off_timer).start()

    @Slot()
    def _on_pulse_on_end(self):
        self.device.set_button(self.button_id, False)

    @Slot()
    def _on_pulse_off_end(self):
        self.device.set_button(self.button_id, True)

    def process_event(self, event: sdl2.SDL_Event):
        if event.type == sdl2.SDL_JOYBUTTONDOWN:
            self.pressed_signal.emit()
        if event.type == sdl2.SDL_JOYBUTTONUP:
            self.released_signal.emit()
        self.switched_signal.emit(event.jbutton.state == 1)
