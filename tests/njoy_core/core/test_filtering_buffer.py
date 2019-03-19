import random
import zmq.green as zmq
import gevent.pool

from njoy_core.core.filtering_buffer import FilteringBuffer
from njoy_core.common.messages import ControlEvent

ZMQ_CONTEXT = zmq.Context()


class MockRouter(gevent.Greenlet):
    def __init__(self, context, endpoint):
        super().__init__()
        self._ctx = context
        self._socket = context.socket(zmq.PUB)
        self._socket.bind(endpoint)

    def _run(self):
        identities = [{'node': 0, 'device': 0, 'control': i}
                      for i in range(6)]
        sent = 0
        while True:
            ControlEvent(**random.choice(identities),
                         value=random.randrange(2) == 1).send(self._socket)
            sent += 1
            if sent % 1000 == 0:
                print("Router: sent {} messages".format(sent))

            if random.randrange(10000) == 42:
                print("Router: Pausing 5s...")
                gevent.sleep(5)
            else:
                gevent.sleep(0.001)


class MockControl(gevent.Greenlet):
    def __init__(self, context, input_endpoint, input_identities):
        super().__init__()
        self._filter = FilteringBuffer(context=context,
                                       input_endpoint=input_endpoint,
                                       input_identities=input_identities)
        self._value = None

    def _run(self):
        self._filter.start()

        received = 0
        while True:
            states = self._filter.input_values
            if states is not None:
                received += 1
                if received % 100 == 0:
                    print("Control: received {} messages".format(received))

            gevent.sleep(0.001 * random.randint(1, 200))


if __name__ == '__main__':
    random.seed()

    router = MockRouter(context=ZMQ_CONTEXT,
                        endpoint='inproc://input')

    control = MockControl(context=ZMQ_CONTEXT,
                          input_endpoint='inproc://input',
                          input_identities=[ControlEvent(node=0, device=0, control=i).identity
                                            for i in range(3)])

    grp = gevent.pool.Group()
    grp.start(router)
    grp.start(control)
    grp.join()

# EOF
