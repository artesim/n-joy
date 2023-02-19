import njoy
import sys


def main():
    core = njoy.Core()

    # Joystick inputs
    vjoy_7_in = core.input_device(njoy.VJOY_DEVICE_7)
    virpil_left = core.input_device('LEFT VPC Stick MT-50CM3')
    virpil_right = core.input_device('RIGHT VPC Stick MT-50CM3')

    # Joystick outputs
    vjoy_out_1 = core.output_device(njoy.VJOY_DEVICE_1)

    # Game Interface (input & output)
    elite = core.application(njoy.ELITE_DANGEROUS)

    # Bindings
    va_landing_gear_cmd = vjoy_7_in.button(1)
    va_landing_gear_cmd.pressed.connect(elite.landing_gear.set_on)
    va_landing_gear_cmd.released.connect(elite.landing_gear.set_off)

    core.start()


if __name__ == '__main__':
    sys.exit(main())
