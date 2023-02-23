from __future__ import annotations  # PEP 563: Postponed evaluation of annotations

import njoy
import njoy.game_models.elite_dangerous.elite_model
import njoy.hid_devices.hid_device
import njoy.hid_devices.hid_event_loop
import njoy.hid_devices.vjoy_interface
import sys


def main():
    njoy_core = njoy.Core()

    virpil_left_buttons = [njoy_core.physical_button('LEFT VPC Stick MT-50CM3', i) for i in range(29)]

    physical_buttons = [
        njoy_core.physical_button('LEFT VPC Stick MT-50CM3', 21),  # left pov 1 center
        njoy_core.physical_button('LEFT VPC Stick MT-50CM3', 22),  # left pov 2 center
        njoy_core.physical_button('LEFT VPC Stick MT-50CM3', 23),  # left pov 3 center
        njoy_core.physical_button('LEFT VPC Stick MT-50CM3', 24),  # left pov 4 center
        njoy_core.physical_button('LEFT VPC Stick MT-50CM3', 26),  # left red button
        njoy_core.physical_button('LEFT VPC Stick MT-50CM3', 27),  # left black button
        njoy_core.physical_button('LEFT VPC Stick MT-50CM3', 28)  # left pinkie button
    ]

    vjoy_buttons = [njoy_core.virtual_button(njoy.hid_devices.vjoy_interface.vJoyId(i), i, enable_output=True)
                    for i in range(7)]

    for i in range(7):
        physical_buttons[i].switched_signal.connect(vjoy_buttons[i].switch)

    njoy_core.start()


if __name__ == '__main__':
    sys.exit(main())
