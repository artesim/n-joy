from __future__ import annotations  # PEP 563: Postponed evaluation of annotations

import functools
import njoy
import njoy.game_models.elite_dangerous.elite_model
import njoy.hid_devices.hid_device
import njoy.hid_devices.hid_event_loop
import njoy.hid_devices.vjoy_interface
import sys


def main():
    njoy_core = njoy.Core()

    left_button = functools.partial(njoy_core.physical_button, 'LEFT VPC Stick MT-50CM3')
    left_axis = functools.partial(njoy_core.physical_axis, 'LEFT VPC Stick MT-50CM3')
    right_button = functools.partial(njoy_core.physical_button, 'RIGHT VPC Stick MT-50CM3')
    right_axis = functools.partial(njoy_core.physical_axis, 'RIGHT VPC Stick MT-50CM3')
    _b = njoy_core.game_model.bindings

    # for i in range(29):
    #     vjoy_2_buttons[i].state = virpil_left_buttons[i].state
    #     vjoy_2_buttons[32 + i].state = virpil_right_buttons[i].state

    ui_prev_page = _b['/general/interface_mode/cycle_previous_page']
    ui_next_page = _b['/general/interface_mode/cycle_next_page']
    ui_prev_panel = _b['/general/interface_mode/cycle_previous_panel']
    ui_next_panel = _b['/general/interface_mode/cycle_next_panel']
    ui_up = _b['/general/interface_mode/ui_up']
    ui_right = _b['/general/interface_mode/ui_right']
    ui_down = _b['/general/interface_mode/ui_down']
    ui_left = _b['/general/interface_mode/ui_left']
    ui_select = _b['/general/interface_mode/ui_select']
    ui_back = _b['/general/interface_mode/ui_back']
    fa_off = _b['/ship/flight_miscellaneous/flight_assist_off']
    boost = _b['/ship/flight_miscellaneous/use_boost_juice']
    roll = _b['/ship/flight_rotation/roll_axis_raw']
    pitch = _b['/ship/flight_rotation/pitch_axis_raw']
    yaw = _b['/ship/flight_rotation/yaw_axis_raw']
    fwd = _b['/ship/flight_thrust/ahead_thrust']
    lateral = _b['/ship/flight_thrust/lateral_thrust_raw']
    vertical = _b['/ship/flight_thrust/vertical_thrust_raw']
    thr_up = _b['/ship/flight_throttle/forward_key']
    thr_down = _b['/ship/flight_throttle/backward_key']
    thr_75 = _b['/ship/flight_throttle/set_speed_75']
    gear = _b['/ship/miscellaneous/landing_gear_toggle']
    night_vision = _b['/ship/miscellaneous/night_vision_toggle']
    lights = _b['/ship/miscellaneous/ship_spot_light_toggle']
    cargo_scoop = _b['/ship/miscellaneous/toggle_cargo_scoop']
    hud_mode = _b['/ship/mode_switches/player_hud_mode_toggle']

    left_button(0).pressed_signal.connect(gear.switch_off)
    left_button(1).pressed_signal.connect(gear.switch_on)
    left_button(14).pressed_signal.connect(boost.pulse)
    left_button(15).switched_signal.connect(cargo_scoop.switch)
    left_button(17).switched_signal.connect(thr_75.switch)
    left_button(19).switched_signal.connect(thr_down.switch)
    left_button(20).switched_signal.connect(thr_up.switch)

    right_button(0).pressed_signal.connect(hud_mode.switch_on)
    right_button(1).pressed_signal.connect(hud_mode.switch_off)
    right_button(13).pressed_signal.connect(fa_off.switch_on)
    right_button(14).pressed_signal.connect(fa_off.switch_off)

    left_axis(0).moved_signal.connect(lateral.move)
    left_axis(1).moved_signal.connect(vertical.move)
    left_axis(2).moved_signal.connect(roll.move)
    right_axis(0).moved_signal.connect(yaw.move)
    right_axis(1).moved_signal.connect(pitch.move)
    right_axis(2).moved_signal.connect(fwd.move)
    # left_axis(0).moved_signal.connect(yaw.move)
    # left_axis(1).moved_signal.connect(pitch.move)
    # left_axis(2).moved_signal.connect(roll.move)
    # right_axis(0).moved_signal.connect(lateral.move)
    # right_axis(1).moved_signal.connect(vertical.move)
    # right_axis(2).moved_signal.connect(fwd.move)

    njoy_core.start()


if __name__ == '__main__':
    sys.exit(main())
