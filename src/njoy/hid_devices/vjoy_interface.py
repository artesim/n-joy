from __future__ import annotations  # PEP 563: Postponed evaluation of annotations

import enum
import math
import pyvjoy
import typing

from typing import NewType

if typing.TYPE_CHECKING:
    pass


vJoyId = NewType('vJoyID', int)


class AxisID(enum.IntEnum):
    X = 0
    Y = 1
    Z = 2
    RX = 3
    RY = 4
    RZ = 5
    SL0 = 6
    SL1 = 7
    WHEEL = 8
    POV = 9


class VJoyDevice(pyvjoy.VJoyDevice):
    """Wrapper class around pyvjoy.VJoyDevice.
        It serves three purposes :
        - fixing some quirks of the pyvjoy interface I don't like, such 1-based indexes.
        - augment the pyvjoy interface with some useful utility functions.
        - most importantly, provide a layer of abstraction, should I want to switch to something else later."""

    def __init__(self, vjoy_id: vJoyId):
        """vjoy_id is 0-based, internally converted to vjoy 1-based index."""
        super().__init__(1 + vjoy_id)
        self.reset()
        self.reset_buttons()
        self.reset_data()
        self.reset_povs()

    @staticmethod
    def _to_vjoy_axis_id(axis: AxisID) -> int:
        mapping = {AxisID.X: pyvjoy.HID_USAGE_X,
                   AxisID.Y: pyvjoy.HID_USAGE_Y,
                   AxisID.Z: pyvjoy.HID_USAGE_Z,
                   AxisID.RX: pyvjoy.HID_USAGE_RX,
                   AxisID.RY: pyvjoy.HID_USAGE_RY,
                   AxisID.RZ: pyvjoy.HID_USAGE_RZ,
                   AxisID.SL0: pyvjoy.HID_USAGE_SL0,
                   AxisID.SL1: pyvjoy.HID_USAGE_SL1,
                   AxisID.WHEEL: pyvjoy.HID_USAGE_WHL,
                   AxisID.POV: pyvjoy.HID_USAGE_POV}
        return mapping[axis]

    def set_button(self, button_id: int, state: bool):
        """Set a given button to On (1 or True) or Off (0 or False)
        button_id is 0-based, internally converted to vjoy 1-based button ID"""
        super().set_button(buttonID=1 + button_id,
                           state=state)

    def set_axis(self, axis_id: AxisID, value: float):
        """Set a given axis to the given value.
        axis_id is an AxisID enum (actually an IntEnum, 0-based), internally converted to vjoy axis ID
        value is a float in range [-1.0 .. 1.0], internally converted to vjoy int range [0X0001..0x8000]"""
        def _0x0001_to_0x8000(_value: float) -> int:
            return math.floor(1 + (0x7FFF * (1 + _value)) / 2)

        def _0x0000_to_0x8000(_value: float) -> int:
            return math.floor(0x8000 * (1 + _value) / 2)

        return super().set_axis(AxisID=self._to_vjoy_axis_id(axis_id),
                                AxisValue=_0x0000_to_0x8000(value))

    def set_cont_pov(self, pov_id: int, value: int):  # pylint: disable=arguments-differ
        """Set a given POV to a continuous direction :
        pov_id is 0-based, internally converted to vjoy 1-based pov ID
        value is an int in range [0 .. 35900] (tenth of degrees) or -1 for None (not pressed)"""
        return super().set_cont_pov(PovID=1 + pov_id,
                                    PovValue=value)
