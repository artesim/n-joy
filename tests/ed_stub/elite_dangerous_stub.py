# Elite Dangerous stub
#
# - file watcher for a .binds file
#    => for changing hold/toggle button mode on the fly
#    => to know which bindings to listen to
# - monitor a vjoy device for binding events
# - update game state through a fake status.json and journal.json

from __future__ import annotations  # PEP 563: Postponed evaluation of annotations

import collections
import ctypes
import datetime
import json
import re
import sys

import sdl2
import sdl2.ext
import typing

from sdl_interface import SDLError, _SDL, DeviceIndex
from vjoy_interface import vJoyId
from PySide6.QtCore import QObject, Slot, QThread, QCoreApplication
from pathlib import Path

if typing.TYPE_CHECKING:
    pass


def timestamp_str() -> str:
    return datetime.datetime.now().isoformat()


class HIDEventLoop(QObject):
    __RE_VJOY_PATH__ = re.compile(rb'HID#HIDCLASS&COL(\d+)#')

    def __init__(self):
        super().__init__(parent=None)
        self._controls = collections.defaultdict(lambda: {'axis': dict(),
                                                          'buttons': dict(),
                                                          'hats': dict()})

        # Initialize the SDL subsystems once, when first importing this module
        sdl2.ext.init(joystick=True, controller=False, haptic=False, sensor=False, events=True)

        # Listen to some vjoy buttons for the test
        device_index = _SDL.find_vjoy_device_index(vJoyId(0))
        sdl_device = _SDL.open(device_index)
        for i in range(101):
            if i == 19:
                vjoy1_button = StubButton(parent=self,
                                          sdl_device=sdl_device,
                                          device_index=device_index,
                                          button_id=i,
                                          label='analysis_mode',
                                          status_flag=0x08000000,
                                          configured_in_hold_mode=False)
            elif i == 10:
                vjoy1_button = StubButton(parent=self,
                                          sdl_device=sdl_device,
                                          device_index=device_index,
                                          button_id=i,
                                          label='flight_assist_off',
                                          status_flag=0x00000020,
                                          configured_in_hold_mode=True)

            else:
                vjoy1_button = StubButton(parent=self,
                                          sdl_device=sdl_device,
                                          device_index=device_index,
                                          button_id=i)
            self._controls[vjoy1_button.instance_id]['buttons'][i] = vjoy1_button

        self._sdl_thread = QThread()
        self.moveToThread(self._sdl_thread)
        self._sdl_thread.started.connect(self.run)
        self._sdl_thread.start()

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


C = Path('C:/')
STATUS_JSON = C / 'Users' / 'artes' / 'Saved Games' / 'Frontier Developments' / 'Elite Dangerous' / 'Status.json'


class StubButton(QObject):
    def __init__(self,
                 *,
                 parent: QObject,
                 sdl_device,
                 device_index: DeviceIndex,
                 button_id: int,
                 label: str = None,
                 status_flag: int = None,
                 configured_in_hold_mode: bool = False):
        super().__init__(parent=parent)
        self.sdl = sdl_device
        self.device_index = device_index
        self.button_id = button_id
        self.label = label
        self.configured_in_hold_mode = configured_in_hold_mode
        self.status_flag = status_flag

    def __repr__(self):
        label_str = f' ({self.label})' if self.label else ''
        return f'<StubButton #{self.button_id} of device {self.device_index}{label_str}>'

    @property
    def instance_id(self) -> int:
        return _SDL.get_instance_id(self.device_index)

    def get_state(self) -> bool:
        if self.status_flag is None:
            return False
        status_lines = STATUS_JSON.read_text().splitlines()
        status = json.loads(status_lines[0])
        return (status['Flags'] & self.status_flag) == self.status_flag

    def set_state(self, state: bool):
        status_lines = STATUS_JSON.read_text().splitlines()
        status = json.loads(status_lines[0])
        if state:
            status['Flags'] |= self.status_flag
        else:
            status['Flags'] &= (0xFFFFFFFFFFFFFFFF ^ self.status_flag)
        STATUS_JSON.write_text(json.dumps(status))

    def process_event(self, event: sdl2.SDL_Event):
        # First print the actual input as-is
        if event.type == sdl2.SDL_JOYBUTTONUP:
            print(f"{timestamp_str()}: {self}: Received UP")
        elif event.type == sdl2.SDL_JOYBUTTONDOWN:
            print(f"{timestamp_str()}: {self}: Received DOWN")

        # If we need to generate feedback for this button, print the resulting state change (if any)
        if self.status_flag is None:
            return

        old_state = self.get_state()
        if self.configured_in_hold_mode:
            if event.type == sdl2.SDL_JOYBUTTONDOWN:
                self.set_state(True)
            elif event.type == sdl2.SDL_JOYBUTTONUP:
                self.set_state(False)

        else:  # toggle mode, on released
            if event.type == sdl2.SDL_JOYBUTTONDOWN:
                pass
            elif event.type == sdl2.SDL_JOYBUTTONUP:
                self.set_state(not self.get_state())

        new_state = self.get_state()
        if old_state != new_state:
            print(f"{timestamp_str()}: {self}: {old_state} => {new_state}")


def main():
    app = QCoreApplication()
    loop = HIDEventLoop()
    app.exec()


if __name__ == '__main__':
    sys.exit(main())
