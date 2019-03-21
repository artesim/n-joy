import gevent.pool

from .input_buffers import InputBuffer
from .actuators import Actuator


class CoreControl(gevent.Greenlet):
    def __init__(self, context, input_endpoint, input_identities, output_endpoint, identity):
        super().__init__()
        self._buffer = InputBuffer(context=context,
                                   input_endpoint=input_endpoint,
                                   input_identities=input_identities)
        self._actuator = Actuator(context=context,
                                  output_endpoint=output_endpoint,
                                  identity=identity)

    @property
    def identity(self):
        return self._actuator.identity

    def _process(self, values):
        # XXX: This is where we should inject an algorithm, that somehow comes up from parsing the nJoy Design.
        raise NotImplementedError

    def _run(self):
        grp = gevent.pool.Group()
        grp.start(self._buffer)
        grp.start(self._actuator)

        while True:
            values = self._buffer.input_values
            if values is not None:
                self._actuator.value = self._process(values)

            # Wait a millisecond between each read attempt, to give a chance for other greenlets to run
            gevent.sleep(0.001)


class Axis(CoreControl):
    def _process(self, values):
        return list(values.values())[0]


class Button(CoreControl):
    def _process(self, values):
        return list(values.values())[0]


class Hat(CoreControl):
    def _process(self, values):
        return list(values.values())[0]


class PseudoButton(CoreControl):
    def _process(self, values):
        return not any(values.values())

# EOF
