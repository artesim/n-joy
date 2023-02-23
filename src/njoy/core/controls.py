from __future__ import annotations  # PEP 563: Postponed evaluation of annotations

import abc

from PySide6.QtCore import QObject, Signal, Slot, Property, QTimer


class MetaInputAxis(type(QObject), abc.ABCMeta):
    def __call__(cls, *args, **kwargs):
        instance = super().__call__(*args, **kwargs)
        cls.value = Property(type=bool, fget=cls._get_value, notify=cls.moved_signal)
        return instance


class MetaOutputAxis(type(QObject), abc.ABCMeta):
    def __call__(cls, *args, **kwargs):
        instance = super().__call__(*args, **kwargs)
        cls.value = Property(type=bool, fget=cls._get_value, fset=cls._set_value, notify=cls.moved_signal)
        return instance


class InputAxisInterface(QObject, metaclass=MetaInputAxis):
    moved_signal = Signal(float)

    @abc.abstractmethod
    def _get_value(self) -> float:
        ...


class OutputAxisInterface(QObject, metaclass=MetaOutputAxis):
    moved_signal = Signal(float)

    @abc.abstractmethod
    def _get_value(self) -> float:
        ...

    @abc.abstractmethod
    def _set_value(self, value: float):
        ...

    @Slot(float)
    def move(self, target_value: float):
        self._set_value(target_value)


class MetaInputButton(type(QObject), abc.ABCMeta):
    def __call__(cls, *args, **kwargs):
        instance = super().__call__(*args, **kwargs)
        cls.state = Property(type=bool, fget=cls._get_state, notify=cls.switched_signal)
        return instance


class MetaOutputButton(type(QObject), abc.ABCMeta):
    def __call__(cls, *args, **kwargs):
        instance = super().__call__(*args, **kwargs)
        cls.state = Property(type=bool, fget=cls._get_state, fset=cls._set_state, notify=cls.switched_signal)
        return instance


class InputButtonInterface(QObject, metaclass=MetaInputButton):
    pressed_signal = Signal()  # pressed indefinitely
    released_signal = Signal()  # released indefinitely
    switched_signal = Signal(bool)  # switched indefinitely

    @abc.abstractmethod
    def _get_state(self) -> bool:
        ...


class OutputButtonInterface(QObject, metaclass=MetaOutputButton):
    pressed_signal = Signal()  # pressed indefinitely
    released_signal = Signal()  # released indefinitely
    switched_signal = Signal(bool)  # switched indefinitely

    @abc.abstractmethod
    def _get_state(self) -> bool:
        ...

    @abc.abstractmethod
    def _set_state(self, state: bool):
        ...


class OutputSwitchMixin(QObject):
    @abc.abstractmethod
    @Slot(bool)
    def switch(self, target_state: bool = None):
        ...

    @Slot()
    def switch_on(self):
        self.switch(True)

    @Slot()
    def switch_off(self):
        self.switch(False)


class OutputPulseMixin(QObject):
    __PULSE_DURATION__ = 100

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._pulse_on_timer = QTimer(self)
        self._pulse_on_timer.setSingleShot(True)
        self._pulse_on_timer.setInterval(self.__PULSE_DURATION__)
        self._pulse_on_timer.timeout.connect(self._on_pulse_on_end)

        self._pulse_off_timer = QTimer(self)
        self._pulse_off_timer.setSingleShot(True)
        self._pulse_off_timer.setInterval(self.__PULSE_DURATION__)
        self._pulse_off_timer.timeout.connect(self._on_pulse_off_end)

    def __del__(self):
        self._pulse_on_timer.stop()
        self._pulse_off_timer.stop()
        self._pulse_on_timer.deleteLater()
        self._pulse_off_timer.deleteLater()

    @abc.abstractmethod
    @Slot(bool)
    def pulse(self, target_state: bool = None):
        ...

    @Slot()
    def pulse_on_off(self):
        self.pulse(True)

    @Slot()
    def pulse_off_on(self):
        self.pulse(False)

    @abc.abstractmethod
    @Slot()
    def _on_pulse_on_end(self):
        ...

    @abc.abstractmethod
    @Slot()
    def _on_pulse_off_end(self):
        ...
