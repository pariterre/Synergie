from enum import Enum, auto
import logging
import os
import threading
import time
from typing import Callable

import asyncio
import numpy as np

if os.name == "nt":
    from winsdk.windows.devices import radios

from .dot_device import DotDevice, initialize_bluetooth_dot_device
from .errors import BluetoothCommunicationError, MissingSensorsError
from .movella_loader import movelladot_sdk
from .xdpchandler import XdpcHandler
from ..database.database_manager import DatabaseManager

_logger = logging.getLogger(__name__)


class DotConnexionStatus(Enum):
    """
    Enumeration of the possible states of a DotDevice.
    """

    DISCONNECTED = auto()
    CONNECTING_USB = auto()
    CONNECTING_BLUETOOTH = auto()
    IDENTIFYING_BLUETOOTH_DEVICES = auto()
    CONNECTED = auto()
    MONITORING_STARTED = auto()


async def _bluetooth_power(turn_on: bool):
    """
    Asynchronously turn Bluetooth radios on or off.

    Args:
        turn_on (bool): True to turn on Bluetooth, False to turn it off.
    """
    try:
        all_radios = await radios.Radio.get_radios_async()
        for this_radio in all_radios:
            if this_radio.kind == radios.RadioKind.BLUETOOTH:
                if turn_on:
                    await this_radio.set_state_async(radios.RadioState.ON)
                    _logger.info("Bluetooth turned ON.")
                else:
                    await this_radio.set_state_async(radios.RadioState.OFF)
                    _logger.info("Bluetooth turned OFF.")

    except Exception as e:
        _logger.error(f"Exception in bluetooth_power: {e}")
        raise BluetoothCommunicationError()


class DotManager:
    """
    Managing the connection to the sensors
    """

    def __init__(self, database_manager: DatabaseManager) -> None:
        self._database_manager = database_manager
        self._devices: list[DotDevice] = []
        self._previous_plugged_devices: list[DotDevice] = []
        self._status = DotConnexionStatus.DISCONNECTED

    @property
    def status(self):
        return self._status

    def initialize_connexion(self, dots_white_list: list[str], events: threading.Event) -> None:
        """
        Initial connection to sensors.

        Args:
            dots_white_list (list[str]): List of MAC addresses to connect to.

        Returns:
            None if successful, otherwise raises an exception.

        Raises:
            BluetoothCommunicationError: If there is an issue with Bluetooth communication.
            MissingSensorsError: If at least one bluetooth sensor is missing (problably not connected to the base).
        """

        self._devices = []
        self._previous_plugged_devices = []

        # Disable Bluetooth
        if os.name == "nt":
            asyncio.run(_bluetooth_power(False))
        elif os.name == "posix":
            os.system("rfkill block bluetooth")
        else:
            raise NotImplementedError("Bluetooth power control not implemented for this OS.")

        # Initialize USB connection handler
        xdpc_handler = XdpcHandler(whitelist=dots_white_list)
        if not xdpc_handler.initialize():
            xdpc_handler.cleanup()
            _logger.error("XdpcHandler initialization failed.")
            raise BluetoothCommunicationError()

        # Connect USB devices
        self._status = DotConnexionStatus.CONNECTING_USB
        events.set()
        port_info_usb: dict[str, movelladot_sdk.XsPortInfo] = {}
        mac_addresses: list[str] = []
        xdpc_handler.detect_usb_devices()
        while len(xdpc_handler.connected_usb_dots()) < len(xdpc_handler.detected_dots()):
            xdpc_handler.connect_dots()
        for device in xdpc_handler.connected_usb_dots():
            device_id = str(device.deviceId())
            port_info_usb[device_id] = device.portInfo()
            mac_addresses.append(device.bluetoothAddress())
        xdpc_handler.cleanup()
        _logger.info(f"Connected USB devices: {list(port_info_usb.keys())}")

        # Re-enable Bluetooth
        if os.name == "nt":
            asyncio.run(_bluetooth_power(True))
        elif os.name == "posix":
            os.system("rfkill unblock bluetooth")
        else:
            raise NotImplementedError("Bluetooth power control not implemented for this OS.")

        # Initialize Bluetooth connection handler
        self._status = DotConnexionStatus.CONNECTING_BLUETOOTH
        events.set()
        xdpc_handler = XdpcHandler(whitelist=dots_white_list)
        if not xdpc_handler.initialize():
            xdpc_handler.cleanup()
            _logger.error("XdpcHandler initialization failed.")
            raise BluetoothCommunicationError()
        xdpc_handler.scan_for_dots(white_list=mac_addresses)
        port_info_bluetooth = xdpc_handler.detected_dots()
        xdpc_handler.cleanup()
        _logger.info(f"Detected Bluetooth devices: {[info.bluetoothAddress() for info in port_info_bluetooth]}")

        # Connect Bluetooth devices
        self._status = DotConnexionStatus.IDENTIFYING_BLUETOOTH_DEVICES
        events.set()
        unconnected_devices = []
        for port_info_bluetooth in port_info_bluetooth:
            device = self._database_manager.get_dot_from_bluetooth(port_info_bluetooth.bluetoothAddress())
            device_id = (
                initialize_bluetooth_dot_device(movelladot_sdk.XsDotConnectionManager(), port_info_bluetooth)
                if device is None
                else device.id
            )

            if str(device_id) in port_info_usb:
                self._devices.append(
                    DotDevice(
                        port_info_usb=port_info_usb[str(device_id)],
                        port_info_bluetooth=port_info_bluetooth,
                        database_manager=self._database_manager,
                    )
                )
            else:
                unconnected_devices.append(device.get("tag_name"))

        if unconnected_devices:
            raise MissingSensorsError(sensor_names=unconnected_devices)

        self._previous_plugged_devices = self._devices

        self._status = DotConnexionStatus.CONNECTED
        events.set()

        return

    def start_usb_monitoring(
        self,
        start_recording_callback: Callable[[DotDevice], None],
        stop_recording_callback: Callable[[DotDevice], None],
        events: threading.Event,
    ):
        """
        Start monitoring USB devices.

        Args:
            start_recording_callback (function): Function to call when a non-recording device disconnects.
            stop_recording_callback (function): Function to call when a recording device reconnects.
        """
        usb_detection_thread = threading.Thread(
            target=self._monitor_usb_dots,
            args=([start_recording_callback, stop_recording_callback]),
            daemon=True,
        )
        usb_detection_thread.start()

        self._status = DotConnexionStatus.MONITORING_STARTED
        events.set()

    def _monitor_usb_dots(
        self,
        start_recording_callback: Callable[[DotDevice], None],
        stop_recording_callback: Callable[[DotDevice], None],
    ):
        """
        Continuously monitor device connection status. If a device is connected
        while recording, stop it and notify the user. If a device is disconnected while
        not recording, start it.

        Args:
            start_recording_callback (function): Function to call when a non-recording device disconnects.
            stop_recording_callback (function): Function to call when a recording device reconnects.
        """

        while True:
            # Check the status of devices.
            self._check_plug_statuses(
                start_recording_callback=start_recording_callback,
                stop_recording_callback=stop_recording_callback,
            )

            # Wait a short time before checking again.
            time.sleep(0.2)

    def _check_plug_statuses(
        self,
        start_recording_callback: Callable[[DotDevice], None],
        stop_recording_callback: Callable[[DotDevice], None],
    ):
        """
        Detects USB-connected sensors to capture any new connections or disconnections.

        Args:
            start_recording_callback (Callable): Function to call when a non-recording device disconnects.
            stop_recording_callback (Callable): Function to call when a recording device reconnects.
        """

        plugged_devices = [device for device in self._devices if device.is_battery_charging]

        # Check for newly unplugged devices
        for device in self._previous_plugged_devices:
            if device not in plugged_devices:
                device.close_usb()

                # If device is not currently recording, start it.
                if not device.is_recording:
                    start_recording_callback(device)

        # Check for newly plugged devices
        has_connected = []
        for device in plugged_devices:
            if device not in self._previous_plugged_devices:
                device.open_usb(should_stop_recording=True)
                has_connected.append(device)

                # If device is currently recording or has pending records, stop it.
                if device.is_recording or device.recording_count > 0:
                    stop_recording_callback(device)

        self._previous_plugged_devices = plugged_devices

    def get_export_estimated_time(self) -> float:
        """
        Estimates the extraction time for all sensors simultaneously.

        Returns:
            float: The maximum estimated time among all devices.
        """
        estimated_times = [0]
        for device in self._devices:
            try:
                estimated_times.append(device.get_export_estimated_time())
            except Exception as e:
                _logger.error(f"Error estimating export time for device {device.deviceId}: {e}")
                estimated_times.append(0)

        max_time = np.max(estimated_times)
        _logger.info(f"Estimated export time: {max_time} seconds.")
        return max_time

    def get_devices(self) -> list[DotDevice]:
        """
        Retrieves the list of managed DotDevice instances.

        Returns:
            List[DotDevice]: The list of devices.
        """
        return self._devices
