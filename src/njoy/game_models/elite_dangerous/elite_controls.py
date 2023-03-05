from __future__ import annotations  # PEP 563: Postponed evaluation of annotations

import enum
import typing

from PySide6.QtCore import QObject, Slot, Signal, Property
from njoy.hid_devices.hid_controls import OutputAxis, OutputButton
from njoy.core.controls import InputButtonInterface
from njoy.core.controls import OutputButtonInterface, OutputSwitchMixin
from typing import TypeAlias

if typing.TYPE_CHECKING:
    pass


class FeedbackSwitch(OutputButtonInterface, OutputSwitchMixin):
    """Models an in-game switch:
    - for which we have feedback
    - which can only be bound to a toggle button, without a configurable hold mode,
      so we have to pulse the same binding to toggle between on and off, we cannot
      just keep it pressed or released.
    """
    def __init__(self,
                 *,
                 parent: QObject = None,
                 output: OutputButton,
                 feedback: FlagInput):
        super().__init__(parent=parent)
        self.output = output
        self._requested_state: bool | None = None
        self._feedback: FlagInput = feedback
        self._feedback.switched_signal.connect(self.on_feedback_changed)

    def _update_output_state(self):
        self.output.pulse_on_off()

    def _get_state(self) -> bool:
        return self._feedback.state

    def _set_state(self, state: bool):
        self._requested_state = state
        if self._requested_state != self.state:
            self._update_output_state()

    @Slot(bool)
    def switch(self, target_state: bool = None):
        self._set_state(not self.state if target_state is None else target_state)

    @Slot(bool)
    def on_feedback_changed(self, feedback_state: bool):
        if self._requested_state is None:
            return
        if self._requested_state != feedback_state:
            self._update_output_state()


class FeedbackHoldSwitch(FeedbackSwitch):
    """Models an in-game switch:
    - for which we have feedback
    - which can be bound to a button, which can (and will) be configured in hold mode
    """
    def _update_output_state(self):
        # - if the output binding is already in the requested state, pulse it
        #   in order to have the game detect the state change, then set it back
        # - if the output binding was not in the requested state, just switch it
        if self.output.state == self._requested_state:
            self.output.pulse_on_off()
        else:
            self.output.switch(self._requested_state)


# Elite status flags and flags2 merged into a single 64 bits enum value
# Values from https://elite-journal.readthedocs.io/en/latest/Status%20File/
class StatusFlags(enum.IntFlag, boundary=enum.STRICT):
    # Status Flags bits:
    DOCKED = enum.auto()  # on a landing pad
    LANDED = enum.auto()  # on planet surface
    LANDING_GEAR_DOWN = enum.auto()
    SHIELDS_UP = enum.auto()
    SUPERCRUISE = enum.auto()
    FLIGHT_ASSIST_OFF = enum.auto()
    HARDPOINTS_DEPLOYED = enum.auto()
    IN_WING = enum.auto()
    LIGHTS_ON = enum.auto()
    CARGO_SCOOP_DEPLOYED = enum.auto()
    SILENT_RUNNING = enum.auto()
    SCOOPING_FUEL = enum.auto()
    SRV_HANDBRAKE = enum.auto()
    SRV_USING_TURRET_VIEW = enum.auto()
    SRV_TURRET_RETRACTED = enum.auto()  # close to ship
    SRV_DRIVE_ASSIST = enum.auto()
    FSD_MASS_LOCKED = enum.auto()
    FSD_CHARGING = enum.auto()
    FSD_COOLDOWN = enum.auto()
    LOW_FUEL = enum.auto()  # < 25%
    OVER_HEATING = enum.auto()  # > 100%
    HAS_LAT_LONG = enum.auto()
    IS_IN_DANGER = enum.auto()
    BEING_INTERDICTED = enum.auto()
    IN_MAIN_SHIP = enum.auto()
    IN_FIGHTER = enum.auto()
    IN_SRV = enum.auto()
    HUD_IN_ANALYSIS_MODE = enum.auto()  # self._bindings.bind_button('/ship/mode_switches/player_hud_mode_toggle')
    NIGHT_VISION = enum.auto()
    ALTITUDE_FROM_AVERAGE_RADIUS = enum.auto()
    FSD_JUMP = enum.auto()
    SRV_HIGH_BEAM = enum.auto()
    # Status Flags2 bits:
    ON_FOOT = enum.auto()
    IN_TAXI = enum.auto()  # or in a dropship, or shuttle
    IN_MULTICREW = enum.auto()  # i.e. in someone else's ship
    ON_FOOT_IN_STATION = enum.auto()
    ON_FOOT_ON_PLANET = enum.auto()
    AIM_DOWN_SIGHT = enum.auto()
    LOW_OXYGEN = enum.auto()
    LOW_HEALTH = enum.auto()
    COLD = enum.auto()
    HOT = enum.auto()
    VERY_COLD = enum.auto()
    VERY_HOT = enum.auto()
    GLIDE_MODE = enum.auto()
    ON_FOOT_IN_HANGAR = enum.auto()
    ON_FOOT_SOCIAL_SPACE = enum.auto()
    ON_FOOT_EXTERIOR = enum.auto()
    BREATHABLE_ATMOSPHERE = enum.auto()
    TELEPRESENCE_MULTICREW = enum.auto()
    PHYSICAL_MULTICREW = enum.auto()


class GuiFocus(enum.IntEnum):
    NO_FOCUS = 0
    INTERNAL_PANEL = 1
    EXTERNAL_PANEL = 2
    COMMS_PANEL = 3
    ROLE_PANEL = 4
    STATION_SERVICES = 5
    GALAXY_MAP = 6
    SYSTEM_MAP = 7
    ORRERY = 8
    FSS_MODE = 9
    SAA_MODE = 10
    CODEX = 11


class LegalStatus(enum.StrEnum):
    Clean = enum.auto()
    IllegalCargo = enum.auto()
    Speeding = enum.auto()
    Wanted = enum.auto()
    Hostile = enum.auto()
    PassengerWanted = enum.auto()
    Warrant = enum.auto()


class FlagInput(InputButtonInterface):
    def __init__(self, *args, status_flag: StatusFlags, **kwargs):
        super().__init__(*args, **kwargs)
        self._flag: StatusFlags = status_flag
        self._state: bool = False

    def _get_state(self) -> bool:
        return self._state

    @Slot(dict)
    def on_status_event(self, status_event: dict):
        new_state = status_event['Flags'] & self._flag
        if self._state != new_state:
            self._state = new_state
            if self._state:
                self.released_signal.emit()
            else:
                self.pressed_signal.emit()
            self.switched_signal.emit(self._state)


class GuiFocusInput(QObject):
    changed_signal = Signal(GuiFocus)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._state: GuiFocus = GuiFocus.NO_FOCUS

    @Property(type=GuiFocus, notify=changed_signal)
    def state(self) -> GuiFocus:
        return self._state

    @Slot(dict)
    def on_status_event(self, status_event: dict):
        if 'GuiFocus' not in status_event:
            return
        if self._state != status_event['GuiFocus']:
            self._state = status_event['GuiFocus']
            self.changed_signal.emit(self._state)


class LegalStatusInput(QObject):
    changed_signal = Signal(LegalStatus)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._state: LegalStatus = LegalStatus.Clean

    @Property(type=LegalStatus, notify=changed_signal)
    def state(self) -> LegalStatus:
        return self._state

    @Slot(dict)
    def on_status_event(self, status_event: dict):
        if 'LegalStatus' not in status_event:
            return
        if self._state != status_event['LegalStatus']:
            self._state = status_event['LegalStatus']
            self.changed_signal.emit(self._state)


EliteInputControl: TypeAlias = FlagInput | GuiFocusInput | LegalStatusInput
EliteOutputSwitch: TypeAlias = FeedbackSwitch | FeedbackHoldSwitch
EliteOutputControl: TypeAlias = EliteOutputSwitch | OutputAxis | OutputButton
