from __future__ import annotations  # PEP 563: Postponed evaluation of annotations

import datetime
import enum
import json
import lxml.etree
import re
import typing

from .elite_controls import FeedbackSwitch, FeedbackHoldSwitch
from .elite_monitor import StatusFlags
from njoy.hid_devices.hid_event_loop import vJoyId
from lxml import objectify
from pathlib import Path, PurePosixPath
from PySide6.QtCore import QObject

if typing.TYPE_CHECKING:
    from .elite_controls import EliteOutputControl
    from .elite_model import EliteModel
    from njoy.hid_devices.hid_event_loop import HIDEventLoop


def timestamp_str() -> str:
    return datetime.datetime.now().isoformat()


C = Path('C:/')
D = Path('D:/')
__BINDINGS_DIR__ = D / 'config' / 'Elite Dangerous' / 'Bindings'
__DEFAULT_GENERATED_BINDING_FILE__ = __BINDINGS_DIR__ / 'njoy.4.0.binds'
__ED_EMPTY_BINDINGS_FILE__ = C / 'Program Files (x86)' / 'Steam' / 'steamapps' / 'common' / 'Elite Dangerous' / 'Products' / 'elite-dangerous-odyssey-64' / 'ControlSchemes' / 'Empty.binds'

# 		<Primary Device="vJoy" DeviceIndex="6" Key="Joy_1" />  =>  vJoyId(0) = 6
# 		<Primary Device="vJoy" DeviceIndex="1" Key="Joy_2" />  =>  vJoyId(1) = 1
# 		<Primary Device="vJoy" DeviceIndex="3" Key="Joy_3" />  =>  vJoyId(2) = 3
# 		<Primary Device="vJoy" DeviceIndex="5" Key="Joy_4" />  =>  vJoyId(3) = 5
# 		<Primary Device="vJoy" DeviceIndex="0" Key="Joy_5" />  =>  vJoyId(4) = 0
# 		<Primary Device="vJoy" DeviceIndex="2" Key="Joy_6" />  =>  vJoyId(5) = 2
# 		<Primary Device="vJoy" DeviceIndex="4" Key="Joy_7" />  =>  vJoyId(6) = 4
__VJOY_TO_ED__: dict[vJoyId, int] = {vJoyId(i): j for (i, j) in enumerate([6, 1, 3, 5, 0, 2, 4])}
__ED_TO_VJOY__: dict[int, vJoyId] = {i: vJoyId(j) for (i, j) in enumerate([4, 1, 5, 2, 6, 3, 0])}
__ELITE_DANGEROUS_AXIS_NAMES__ = ['Joy_XAxis',
                                  'Joy_YAxis',
                                  'Joy_ZAxis',
                                  'Joy_RXAxis',
                                  'Joy_RYAxis',
                                  'Joy_RZAxis',
                                  'Joy_UAxis',
                                  'Joy_VAxis']


class GameFeedbackKind(enum.StrEnum):
    EliteStatusFlags = enum.auto()
    pip_controller = enum.auto()
    fire_groups_controller = enum.auto()


class EliteBindings(QObject):
    # Adapted from https://stackoverflow.com/a/12867228
    # Added a group to capture an optional leading underscore (replacement pattern becomes group 2)
    # Added a variant to add underscores before numbers, too
    __RE_CAMEL_TO_SNAKE__ = re.compile(r'(_)?((?<=[a-z0-9])[A-Z]|(?<=[a-zA-Z])[0-9]|(?!^)[A-Z](?=[a-z]))')

    # Elite still cannot see buttons past the 32nd (old directx limitation, they never updated),
    # so skip the buttons above 32 when looking for the next available one
    __OUTPUT_BUTTON_RANGE__ = range(32)

    def __init__(self,
                 *,
                 elite_model: EliteModel,
                 hid_event_loop: HIDEventLoop,
                 metadata_file: Path = Path(__file__).with_suffix('.json'),
                 ignored_output_device_ids: set[vJoyId] = None):
        super().__init__(elite_model)
        self._elite_model = elite_model
        self._hid_event_loop = hid_event_loop
        self._ignored_output_device_ids = ignored_output_device_ids or set()

        metadata = json.loads(metadata_file.read_text())
        self.njoy_version_requirement = metadata['njoy_version']
        self.game_version_requirement = metadata['game_version']
        self._control_metadata = self._parse_controls(metadata)
        self._control_instances: dict[str | PurePosixPath, EliteOutputControl] = dict()

    def __getitem__(self, item: str | PurePosixPath) -> EliteOutputControl:
        path = PurePosixPath(item)
        if path in self._control_instances:
            return self._control_instances[path]

        metadata = self._control_metadata[path]
        if not metadata['is_button']:
            binding = self._hid_event_loop.next_virtual_output_axis(device_ignore_list=self._ignored_output_device_ids)

        elif 'game_feedback' in metadata:
            if not metadata['game_feedback'].startswith("StatusFlags."):
                raise NotImplementedError

            feedback_flag = StatusFlags[metadata['game_feedback'].split('.')[1]]
            feedback = self._elite_model.elite_monitor.elite_status.flags[feedback_flag]
            output = self._hid_event_loop.next_virtual_output_button(button_range=self.__OUTPUT_BUTTON_RANGE__,
                                                                     device_ignore_list=self._ignored_output_device_ids)
            binding = FeedbackSwitch(parent=self,
                                     output=output,
                                     feedback=feedback)
        else:
            binding = self._hid_event_loop.next_virtual_output_button(device_ignore_list=self._ignored_output_device_ids)

        self._control_instances[path] = binding
        return binding

    def _parse_controls(self, metadata: dict) -> dict[PurePosixPath, dict]:
        """Parses a companion metadata file.
        For each available binding in Elite, it provides information about:
        - which kind of control (binding) it is (button or axis)
        - if it is button, which mode of operation are available (normal pulse button, or hold mode)
        - (not used yet) if it is a button, is it part of a group of buttons that are an alternative to an axis ?
        - where to read feedback from the game, if it provides any for this binding
        """
        controls_metadata: dict[PurePosixPath, dict] = dict()
        for section in [k for k in metadata.keys() if k not in {'njoy_version', 'game_version'}]:
            for sub_section, sub_section_metadata in metadata[section].items():
                for control_name, control_metadata in sub_section_metadata.items():
                    name = self.__RE_CAMEL_TO_SNAKE__.sub(r'_\2', control_name).lower()
                    path = PurePosixPath(f'/{section}/{sub_section}/{name}')

                    alt_names = [self.__RE_CAMEL_TO_SNAKE__.sub(r'_\2', alt_name).lower()
                                 for alt_name in control_metadata.get('alternate_names', [])]
                    alt_paths = [PurePosixPath(f'/{section}/{sub_section}/{alt_name}')
                                 for alt_name in alt_names]

                    if 'alternate_names' in control_metadata:
                        del control_metadata['alternate_names']
                    control_metadata['elite_name'] = control_name
                    control_metadata['alternates'] = [path] + alt_paths

                    for alt_path in set([path] + alt_paths):
                        if alt_path in controls_metadata:
                            raise KeyError(f"Duplicate control : {alt_path}")
                        controls_metadata[alt_path] = control_metadata
        return {k: controls_metadata[k] for k in sorted(controls_metadata.keys())}

    def generate_bindings(self, bindings_file: Path = None):
        bindings_in_file = bindings_file or __DEFAULT_GENERATED_BINDING_FILE__
        if bindings_in_file.exists():
            bindings = self._parse_and_cleanup_bindings(bindings_in_file)
            # bindings_out_file = bindings_in_file.with_stem(bindings_in_file.stem + '.out')
            bindings_out_file = bindings_in_file
        else:
            bindings = self._generate_empty_bindings()
            bindings_out_file = bindings_in_file

        for path, control in self._control_instances.items():
            metadata = self._control_metadata[path]
            for elt in bindings.iterchildren(metadata['elite_name']):
                if 'game_feedback' in metadata:
                    output = control.output
                else:
                    output = control

                if metadata['is_button']:
                    elt_empty_binding = self._next_empty_binding(elt, is_button=True)
                    self._overwrite_binding(elt=elt_empty_binding,
                                            device_index=str(__VJOY_TO_ED__[output.device.vjoy_id]),
                                            key=f'Joy_{output.button_id + 1}')
                    if metadata['has_hold_mode']:
                        self._set_toggle_on(elt, True)
                else:
                    elt_empty_binding = self._next_empty_binding(elt, is_button=False)
                    self._overwrite_binding(elt=elt_empty_binding,
                                            device_index=str(__VJOY_TO_ED__[output.device.vjoy_id]),
                                            key=__ELITE_DANGEROUS_AXIS_NAMES__[output.axis_id])
                    # FIXME: dirty patch to only invert pitch
                    self._set_inverted_axis(elt, inverted=metadata['elite_name'] == 'PitchAxisRaw')

        bindings_out_file.write_bytes(lxml.etree.tostring(bindings.getroottree(),
                                                          encoding='UTF-8',
                                                          xml_declaration=True,
                                                          pretty_print=True))

    def _parse_and_cleanup_bindings(self, bindings_file: Path) -> objectify.ObjectifiedElement:
        """Parses an existing binding file, and remove any existing binding to vJoy devices (except ignored ones)"""
        root = objectify.fromstring(bindings_file.read_bytes())
        for control in root.iterchildren():
            for param in control.iterchildren():
                if self._is_re_assignable_binding(param):
                    self._clear_binding(param)
        return root

    @staticmethod
    def _generate_empty_bindings() -> objectify.ObjectifiedElement:
        return objectify.fromstring(__ED_EMPTY_BINDINGS_FILE__.read_bytes())

    def _is_re_assignable_binding(self, elt: objectify.ObjectifiedElement):
        if elt.tag not in {'Primary', 'Secondary', 'Binding'}:
            return False
        if elt.get('Device') != 'vJoy':
            return False
        if __ED_TO_VJOY__[int(elt.get('DeviceIndex'))] in self._ignored_output_device_ids:
            return False
        return True

    @staticmethod
    def _next_empty_binding(elt: objectify.ObjectifiedElement, is_button: bool) -> objectify.ObjectifiedElement:
        for child in (elt.iterchildren('Primary', 'Secondary') if is_button else elt.iterchildren('Binding')):
            if child.get('Device') == '{NoDevice}':
                return child

    @staticmethod
    def _set_toggle_on(elt: objectify.ObjectifiedElement, toggle_on: bool):
        for child in elt.iterchildren('ToggleOn'):
            child.set('Value', '1' if toggle_on else '0')

    @staticmethod
    def _set_inverted_axis(elt: objectify.ObjectifiedElement, inverted: bool):
        for child in elt.iterchildren('Inverted'):
            child.set('Value', '1' if inverted else '0')

    def _overwrite_binding(self, elt: objectify.ObjectifiedElement, device_index: str, key: str):
        self._clear_binding_attributes(elt)
        elt.set('Device', 'vJoy')
        elt.set('DeviceIndex', device_index)
        elt.set('Key', key)

    def _clear_binding(self, elt: objectify.ObjectifiedElement):
        self._clear_binding_attributes(elt)
        elt.set('Device', '{NoDevice}')
        elt.set('Key', '')

    def _clear_binding_attributes(self, elt: objectify):
        self._pop_attribute(elt, 'Device')
        self._pop_attribute(elt, 'DeviceIndex')
        self._pop_attribute(elt, 'Key')
        self._pop_attribute(elt, 'key')

    @staticmethod
    def _pop_attribute(elt: objectify.ObjectifiedElement, attribute: str):
        try:
            elt.attrib.pop(attribute)
        except KeyError:
            pass
