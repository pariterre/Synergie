import logging
import os
from typing import Callable

import numpy as np
from core.utils.DotDevice import DotDevice
from core.database.DatabaseManager import DatabaseManager
from core.utils.xdpchandler import XdpcHandler
import asyncio
if os.name == 'nt':
    from winsdk.windows.devices import radios

from .DotDevice import initialize_bluetooth_dot_device
from .errors import BluetoothCommunicationError, MissingSensorsError
from .movella_loader import movelladot_sdk

_logger = logging.getLogger(__name__)


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
    def __init__(self, database_manager : DatabaseManager) -> None:
        self._database_manager = database_manager
        self._devices : list[DotDevice] = []
        self._previous_plugged_devices : list[DotDevice] = []

    def initialize_connexion(self) -> None:
        """
        Initial connection to sensors.

        Returns:
            None if successful, otherwise raises an exception.

        Raises:
            BluetoothCommunicationError: If there is an issue with Bluetooth communication.
            MissingSensorsError: If at least one bluetooth sensor is missing (problably not connected to the base).
        """

        self._devices = []
        self._previous_plugged_devices = []

        # Disable Bluetooth
        if os.name == 'nt':
            asyncio.run(_bluetooth_power(False))
        elif os.name == 'posix':
            os.system('rfkill block bluetooth')
        else:
            raise NotImplementedError("Bluetooth power control not implemented for this OS.")

        # Initialize USB connection handler
        xdpc_handler = XdpcHandler()
        if not xdpc_handler.initialize():
            xdpc_handler.cleanup()
            _logger.error("XdpcHandler initialization failed.")
            raise BluetoothCommunicationError()
        
        # Connect USB devices
        port_info_usb = {}
        xdpc_handler.detect_usb_devices()
        while len(xdpc_handler.connected_usb_dots()) < len(xdpc_handler.detected_dots()):
            xdpc_handler.connect_dots()
        for device in xdpc_handler.connected_usb_dots():
            port_info_usb[str(device.deviceId())] = device.portInfo()
        xdpc_handler.cleanup()
        _logger.info(f"Connected USB devices: {list(port_info_usb.keys())}")

        # Re-enable Bluetooth
        if os.name == 'nt':
            asyncio.run(_bluetooth_power(True))
        elif os.name == 'posix':
            os.system('rfkill unblock bluetooth')
        else:
            raise NotImplementedError("Bluetooth power control not implemented for this OS.")

        xdpc_handler = XdpcHandler()
        if not xdpc_handler.initialize():
            xdpc_handler.cleanup()
            _logger.error("XdpcHandler initialization failed.")
            raise BluetoothCommunicationError()
        xdpc_handler.scan_for_dots()
        port_info_bluetooth = xdpc_handler.detected_dots()
        xdpc_handler.cleanup()
        _logger.info(f"Detected Bluetooth devices: {[info.bluetoothAddress() for info in port_info_bluetooth]}")

        unconnected_devices = []
        for port_info_bluetooth in port_info_bluetooth:
            device = self._database_manager.get_dot_from_bluetooth(port_info_bluetooth.bluetoothAddress())
            device_id = initialize_bluetooth_dot_device(movelladot_sdk.XsDotConnectionManager(), port_info_bluetooth) if device is None else device.id
            
            if str(device_id) in port_info_usb:
                self._devices.append(
                    DotDevice(
                        port_info_usb=port_info_usb[str(device_id)], 
                        port_info_bluetooth=port_info_bluetooth, 
                        database_manager=self._database_manager
                        )
                    )
            else:
                unconnected_devices.append(device.get('tag_name'))
        
        if unconnected_devices:
            raise MissingSensorsError(sensor_names=unconnected_devices)

        self._previous_plugged_devices = self._devices
        return
    
    def check_plug_statuses(
            self, 
            start_recording_callback: Callable[[DotDevice], None],
            stop_recording_callback: Callable[[DotDevice], None]
        ) -> tuple[list[DotDevice], list[DotDevice]]:
        """
        Detects USB-connected sensors to capture any new connections or disconnections.

        Args:
            start_recording_callback (Callable): Function to call when a non-recording device disconnects.
            stop_recording_callback (Callable): Function to call when a recording device reconnects.

        Returns:
            Tuple[List[DotDevice], List[DotDevice]]: Lists of last connected and last disconnected devices.
        """
        
        plugged_devices = [device for device in self._devices if device.is_battery_charging]

        has_connected = []
        has_disconnected = []
        
        # Check for newly unplugged devices
        for device in self._previous_plugged_devices:
            if device not in plugged_devices:
                device.close_usb()
                has_disconnected.append(device)
                
                # If device is not currently recording, start it.
                if not device.is_recording:
                    start_recording_callback(device)

        # Check for newly plugged devices
        for device in plugged_devices:
            if device not in self._previous_plugged_devices:
                device.open_usb()
                has_connected.append(device)

                # If device is currently recording or has pending records, stop it.
                if device.is_recording or device.recording_count > 0:
                    stop_recording_callback(device)
       
        self._previous_plugged_devices = plugged_devices
        return has_connected, has_disconnected

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
