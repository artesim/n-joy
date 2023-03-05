from __future__ import annotations  # PEP 563: Postponed evaluation of annotations

import collections
import ctypes
import sdl2
import sdl2.ext
import typing

from .hid_device import HIDDevice, VirtualDevice
from .sdl_interface import SDLError
from .vjoy_interface import vJoyId
from PySide6.QtCore import QObject, Slot, QThread

if typing.TYPE_CHECKING:
    from njoy.hid_devices.hid_controls import InputAxis, OutputAxis
    from njoy.hid_devices.hid_controls import InputButton, OutputButton


class HIDEventLoop(QObject):
    def __init__(self):
        super().__init__(parent=None)
        self._controls = collections.defaultdict(lambda: {'axis': dict(),
                                                          'buttons': dict(),
                                                          'hats': dict()})

        self._sdl_thread = QThread()
        self.moveToThread(self._sdl_thread)
        self._sdl_thread.started.connect(self.run)
        self._sdl_thread.start()

    def physical_axis(self, ident: str, axis_id: int) -> InputAxis:
        device: HIDDevice = HIDDevice(ident, parent=self)
        axis = device.register_axis(axis_id)
        self._controls[device.instance_id]['axis'][axis_id] = axis
        return axis

    def physical_button(self, ident: str, button_id: int) -> InputButton:
        """Find and return a ReadOnlyButton instance for button 'BUTTON' of device 'IDENT'.
        Physical buttons are read-only, they have no 'switch' or 'pulse' slot, they only emit signals."""
        device: HIDDevice = HIDDevice(ident, parent=self)
        button = device.register_button(button_id)
        self._controls[device.instance_id]['buttons'][button_id] = button
        return button

    def virtual_axis(self, ident: vJoyId, axis_id: int, *, enable_output: bool = False) -> InputAxis | OutputAxis:
        device: VirtualDevice = VirtualDevice(ident, parent=self)
        axis = device.register_axis(axis_id, enable_output=enable_output)
        self._controls[device.instance_id]['axis'][axis_id] = axis
        return axis

    def virtual_button(self, ident: vJoyId, button_id: int, *, enable_output: bool = False) -> InputButton | OutputButton:
        """Find and return a ReadOnlyButton or ReadWriteButton instance for button 'BUTTON' of virtual device number 'IDENT'.
        Virtual buttons are read-only by default, and only emit signals, just like physical buttons.
        If you want to control their state, set the 'enable_output' parameter to True, and connect
        a signal to its 'switch' or 'pulse' slots, depending on how you want to control it.
        """
        device: VirtualDevice = VirtualDevice(ident, parent=self)
        button = device.register_button(button_id, enable_output=enable_output)
        self._controls[device.instance_id]['buttons'][button_id] = button
        return button

    def next_virtual_input_axis(self, *, device_ignore_list: set[vJoyId] = None) -> InputAxis:
        return VirtualDevice.next_available_virtual_axis(device_parent=self,
                                                         enable_output=False,
                                                         device_ignore_list=device_ignore_list)

    def next_virtual_input_button(self,
                                  *,
                                  device_ignore_list: set[vJoyId] = None,
                                  button_range: range = None) -> InputButton:
        return VirtualDevice.next_available_virtual_button(device_parent=self,
                                                           enable_output=False,
                                                           device_ignore_list=device_ignore_list,
                                                           button_range=button_range)

    def next_virtual_output_axis(self, *, device_ignore_list: set[vJoyId] = None) -> OutputAxis:
        return VirtualDevice.next_available_virtual_axis(device_parent=self,
                                                         enable_output=True,
                                                         device_ignore_list=device_ignore_list)

    def next_virtual_output_button(self,
                                   *,
                                   device_ignore_list: set[vJoyId] = None,
                                   button_range: range = None) -> OutputButton:
        return VirtualDevice.next_available_virtual_button(device_parent=self,
                                                           enable_output=True,
                                                           device_ignore_list=device_ignore_list,
                                                           button_range=button_range)

    @Slot()
    def run(self):
        event = sdl2.SDL_Event()
        while sdl2.SDL_WaitEvent(ctypes.byref(event)):
            if event.type == sdl2.SDL_JOYAXISMOTION:
                if device := self._controls.get(event.jaxis.which):
                    if control := device['axis'].get(event.jaxis.axis):
                        control.process_event(event)

            elif event.type in {sdl2.SDL_JOYBUTTONDOWN, sdl2.SDL_JOYBUTTONUP}:
                if device := self._controls.get(event.jbutton.which):
                    if control := device['buttons'].get(event.jbutton.button):
                        control.process_event(event)

            elif event.type == sdl2.SDL_JOYHATMOTION:
                if device := self._controls.get(event.jhat.which):
                    if control := device['hats'].get(event.jhat.hat):
                        control.process_event(event)

        raise SDLError(sdl2.SDL_GetError())
