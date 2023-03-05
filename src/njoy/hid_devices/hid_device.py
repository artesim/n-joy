from __future__ import annotations  # PEP 563: Postponed evaluation of annotations

import sdl2
import sdl2.ext
import typing

from .hid_controls import InputAxis, OutputAxis
from .hid_controls import InputButton, OutputButton
from .sdl_interface import InstanceID, SDLError, _SDL
from .vjoy_interface import VJoyDevice, vJoyId, AxisID
from PySide6.QtCore import QObject

if typing.TYPE_CHECKING:
    from .sdl_interface import DeviceIndex


class _CachedDeviceMeta(type(QObject), type):
    instances: dict[str | vJoyId, HIDDevice | VirtualDevice] = dict()

    def __call__(cls, ident: str | vJoyId, *args, **kwargs):
        if ident not in cls.instances:
            if cls is VirtualDevice:
                instance = super().__call__(*args,
                                            ident=ident,
                                            device_index=_SDL.find_vjoy_device_index(ident),
                                            **kwargs)
            else:
                instance = super().__call__(*args,
                                            device_index=_SDL.find_hid_device_index(ident),
                                            **kwargs)
            cls.instances[ident] = instance
        return cls.instances.get(ident)


class HIDDevice(QObject, metaclass=_CachedDeviceMeta):
    def __init__(self,
                 *,
                 parent: QObject = None,
                 device_index: DeviceIndex):
        super().__init__(parent)
        self._device_index = device_index
        self._sdl = _SDL.open(device_index)
        self.axis: dict[int, InputAxis] = dict()
        self.buttons: dict[int, InputButton] = dict()
        # self.hats: dict[int, PhysicalHat] = dict()

    def __repr__(self):
        return f'<HIDDevice {self.name}>'

    def __del__(self):
        sdl2.SDL_JoystickClose(self._sdl)

    @property
    def device_index(self) -> DeviceIndex:
        return self._device_index

    @property
    def instance_id(self) -> InstanceID:
        instance_id = sdl2.SDL_JoystickInstanceID(self._sdl)
        if instance_id < 0:
            raise SDLError(sdl2.SDL_GetError())
        return InstanceID(instance_id)

    @property
    def name(self) -> str:
        name = sdl2.SDL_JoystickName(self._sdl)
        if not name:
            raise SDLError(sdl2.SDL_GetError())
        return name.decode()

    @property
    def nb_axes(self) -> int:
        nb_axes = sdl2.SDL_JoystickNumAxes(self._sdl)
        if nb_axes < 0:
            raise SDLError(sdl2.SDL_GetError())
        return nb_axes

    @property
    def nb_balls(self) -> int:
        nb_balls = sdl2.SDL_JoystickNumBalls(self._sdl)
        if nb_balls < 0:
            raise SDLError(sdl2.SDL_GetError())
        return nb_balls

    @property
    def nb_buttons(self) -> int:
        nb_buttons = sdl2.SDL_JoystickNumButtons(self._sdl)
        if nb_buttons < 0:
            raise SDLError(sdl2.SDL_GetError())
        return nb_buttons

    @property
    def nb_hats(self) -> int:
        nb_hats = sdl2.SDL_JoystickNumHats(self._sdl)
        if nb_hats < 0:
            raise SDLError(sdl2.SDL_GetError())
        return nb_hats

    def get_axis_value(self, i: int) -> float:
        # (-32768 to 32767), 0 on error
        value = sdl2.SDL_JoystickGetAxis(self._sdl, i)
        if value == 0:
            raise SDLError(sdl2.SDL_GetError())
        return 2 * (value + 0x8000) / 0xFFFF - 1

    def register_axis(self, axis_id: int) -> InputAxis:
        if axis_id not in self.axis:
            self.axis[axis_id] = InputAxis(device=self, axis_id=axis_id)
        return self.axis[axis_id]

    def get_button_state(self, i: int) -> bool:
        return sdl2.SDL_JoystickGetButton(self._sdl, i) == sdl2.SDL_PRESSED

    def register_button(self, button_id: int) -> InputButton:
        if button_id not in self.buttons:
            self.buttons[button_id] = InputButton(device=self, button_id=button_id)
        return self.buttons[button_id]


class VirtualDevice(HIDDevice):
    @classmethod
    def next_available_virtual_axis(cls,
                                    *,
                                    device_parent: QObject,
                                    enable_output: bool = False,
                                    device_ignore_list: set[vJoyId] = None) -> InputAxis | OutputAxis:
        for vjoy_id, _ in _SDL.vjoy_device_index_iterator():
            # First check if this device is in the user's ignore list
            if device_ignore_list is not None and vjoy_id in device_ignore_list:
                continue

            device: VirtualDevice = VirtualDevice(ident=vjoy_id, parent=device_parent)

            # If all the axis of this device are already assigned, try the next one
            if len(device.axis) == device.nb_axes:
                continue

            # Find the next available button id
            next_axis_id = min(set(range(device.nb_axes)) - set(device.axis.keys()))

            # Find and register the first available button in this device
            return device.register_axis(axis_id=next_axis_id,
                                        enable_output=enable_output)

        raise IndexError(f"No more available axis on any vjoy device: please create more")

    @classmethod
    def next_available_virtual_button(cls,
                                      *,
                                      device_parent: QObject,
                                      enable_output: bool = False,
                                      device_ignore_list: set[vJoyId] = None,
                                      button_range: range = None) -> InputButton | OutputButton:
        for vjoy_id, _ in _SDL.vjoy_device_index_iterator():
            # First check if this device is in the user's ignore list
            if device_ignore_list is not None and vjoy_id in device_ignore_list:
                continue

            device: VirtualDevice = VirtualDevice(ident=vjoy_id, parent=device_parent)

            # If all the buttons of this device are already assigned, try the next one
            if len(device.buttons) == device.nb_buttons:
                continue

            # Find the next available button id
            next_button_id = min(set(range(device.nb_buttons)) - set(device.buttons.keys()))

            # If a button_range was provided, ensure the button is part of it
            if button_range is not None and next_button_id not in button_range:
                continue

            # Otherwise find and register the first available button in this device
            return device.register_button(button_id=next_button_id,
                                          enable_output=enable_output)

        raise IndexError(f"No more available button on any vjoy device: please create more")

    def __init__(self,
                 *,
                 ident: vJoyId,
                 parent: QObject = None,
                 device_index: DeviceIndex):
        super().__init__(parent=parent, device_index=device_index)
        self.vjoy_id: vJoyId = ident
        self._vjoy: VJoyDevice | None = None
        self.axis: dict[int, InputAxis | OutputAxis] = dict()
        self.buttons: dict[int, InputButton | OutputButton] = dict()
        # self.hats: dict[int, VirtualHat] = dict()

    def __repr__(self):
        return f'<VirtualDevice {self.name}>'

    @property
    def name(self) -> str:
        return f'{super().name} #{self.vjoy_id + 1}'

    def set_axis(self, axis_id: int, value: float):
        if self._vjoy is None:
            raise AttributeError(f"Output has not been enabled for {self}")
        self._vjoy.set_axis(AxisID(axis_id), value)

    def register_axis(self, axis_id: int, *, enable_output: bool = False) -> InputAxis | OutputAxis:
        # Only open the vjoy device if we need output for at least one control
        # Otherwise, reading it with the SDL is enough, no need to reserve it
        if enable_output and self._vjoy is None:
            self._vjoy = VJoyDevice(self.vjoy_id)

        output_now_enabled = self._vjoy is not None

        if axis_id not in self.axis:
            cls = OutputAxis if output_now_enabled else InputAxis
            self.axis[axis_id] = cls(device=self, axis_id=axis_id)

        if output_now_enabled:
            self._enable_all_control_outputs()

        return self.axis[axis_id]

    def set_button(self, button_id: int, value: bool):
        if self._vjoy is None:
            raise AttributeError(f"Output has not been enabled for {self}")
        self._vjoy.set_button(button_id, value)

    def register_button(self, button_id: int, *, enable_output: bool = False) -> InputButton | OutputButton:
        # Only open the vjoy device if we need output for at least one control
        # Otherwise, reading it with the SDL is enough, no need to reserve it
        if enable_output and self._vjoy is None:
            self._vjoy = VJoyDevice(self.vjoy_id)

        output_now_enabled = self._vjoy is not None

        if button_id not in self.buttons:
            cls = OutputButton if output_now_enabled else InputButton
            self.buttons[button_id] = cls(device=self, button_id=button_id)

        # Ensure the output is enabled for all buttons if requested now, even if it was not requested the first time
        # If output is not requested now, but it was before, then leave them enabled
        if output_now_enabled:
            self._enable_all_control_outputs()

        return self.buttons[button_id]

    def _enable_all_control_outputs(self):
        # Ensure the output is enabled for all controls if requested now, even if it was not requested the first time
        # If output is not requested now, but it was before, then leave them enabled
        for i in self.buttons.keys():
            button = self.buttons[i]
            if isinstance(button, OutputButton):
                continue
            self.buttons[i] = OutputButton(device=self, button_id=i)
            button.deleteLater()

        for i in self.axis.keys():
            axis = self.axis[i]
            if isinstance(axis, OutputAxis):
                continue
            self.axis[i] = OutputAxis(device=self, axis_id=i)
            axis.deleteLater()
