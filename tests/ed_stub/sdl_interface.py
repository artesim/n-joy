from __future__ import annotations  # PEP 563: Postponed evaluation of annotations

import re
import sdl2
import sdl2.ext
import typing

from vjoy_interface import vJoyId
from typing import NewType

DeviceIndex = NewType('DeviceIndex', int)  # aka device_index in SDL docs
InstanceID = NewType('InstanceID', int)  # aka SDL_JoystickID, InstanceID, "instance id" in SDL docs

if typing.TYPE_CHECKING:
    from typing import Iterator


class SDLError(Exception):
    pass


class _SDL:
    __RE_VJOY_PATH__ = re.compile(rb'HID#HIDCLASS&COL(\d+)#')

    # Initialize the SDL subsystems once, when first importing this module
    sdl2.ext.init(joystick=True, controller=False, haptic=False, sensor=False, events=True)

    @staticmethod
    def find_hid_device_index(ident: str) -> DeviceIndex:
        """ident can be either an HID name (str) or an HID GUID (str)"""
        candidates = list()
        for device_index in [DeviceIndex(i) for i in range(_SDL.nb_joysticks())]:
            if ident == _SDL.get_name(device_index):
                candidates.append(device_index)
            elif ident.encode() == _SDL.get_guid(device_index):
                candidates.append(device_index)

        if len(candidates) == 0:
            raise LookupError(f"No device found for HID name or GUID = {ident}, try another method")
        if len(candidates) != 1:
            raise LookupError(f"Found several devices with HID name or GUID = {ident}, try another method")
        return candidates[0]

    @staticmethod
    def find_vjoy_device_index(ident: vJoyId) -> DeviceIndex:
        for device_index in [DeviceIndex(i) for i in range(_SDL.nb_joysticks())]:
            if _SDL.get_name(device_index) != 'vJoy Device':
                continue
            if match := _SDL.__RE_VJOY_PATH__.search(_SDL.get_path(device_index)):
                # vJoy device IDs are internally 1-based, but vjoy_interface.vJoyID is 0-based
                if ident == vJoyId(int(match.group(1)) - 1):
                    return device_index
        raise LookupError(f"No device found for vJoy ID = {ident}, try another method")

    @staticmethod
    def vjoy_device_index_iterator() -> Iterator[tuple[vJoyId, DeviceIndex]]:
        """Iterate through the vjoy device by vJoy ID (1-based), not necessarily in the SDL order"""
        vjoy_id = 0
        while True:
            try:
                yield vJoyId(vjoy_id), _SDL.find_vjoy_device_index(vJoyId(vjoy_id))
            except LookupError:
                break
            vjoy_id += 1

    @staticmethod
    def open(device_index: DeviceIndex) -> sdl2.SDL_Joystick:
        device = sdl2.SDL_JoystickOpen(device_index)
        if not device:
            raise SDLError(sdl2.SDL_GetError())
        return device

    @staticmethod
    def get_instance_id(device_index: DeviceIndex) -> InstanceID:
        instance_id = sdl2.SDL_JoystickGetDeviceInstanceID(device_index)
        if instance_id < 0:
            raise SDLError(sdl2.SDL_GetError())
        return InstanceID(instance_id)

    @staticmethod
    def get_guid(device_index: DeviceIndex) -> bytes:
        guid = sdl2.SDL_JoystickGetDeviceGUID(device_index)
        if not guid:
            raise SDLError(sdl2.SDL_GetError())
        return guid.data

    @staticmethod
    def get_name(device_index: DeviceIndex) -> str:
        name = sdl2.SDL_JoystickNameForIndex(device_index)
        if not name:
            raise SDLError(sdl2.SDL_GetError())
        return name.decode()

    @staticmethod
    def get_path(device_index: DeviceIndex) -> bytes:
        path = sdl2.SDL_JoystickPathForIndex(device_index)
        if not path:
            raise SDLError(sdl2.SDL_GetError())
        return path

    @staticmethod
    def nb_joysticks() -> int:
        nb_joysticks = sdl2.SDL_NumJoysticks()
        if nb_joysticks < 0:
            raise SDLError(sdl2.SDL_GetError())
        return nb_joysticks
