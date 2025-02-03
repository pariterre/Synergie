#  Copyright (c) 2003-2023 Movella Technologies B.V. or subsidiaries worldwide.
#  All rights reserved.
#
#  Redistribution and use in source and binary forms, with or without modification,
#  are permitted provided that the following conditions are met:
#
#  1.	Redistributions of source code must retain the above copyright notice,
#  	this list of conditions and the following disclaimer.
#
#  2.	Redistributions in binary form must reproduce the above copyright notice,
#  	this list of conditions and the following disclaimer in the documentation
#  	and/or other materials provided with the distribution.
#
#  3.	Neither the names of the copyright holders nor the names of their contributors
#  	may be used to endorse or promote products derived from this software without
#  	specific prior written permission.
#
#  THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY
#  EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
#  MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL
#  THE COPYRIGHT HOLDERS OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
#  SPECIAL, EXEMPLARY OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT
#  OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
#  HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY OR
#  TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
#  SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#

import logging
import time

from .movella_loader import movelladot_sdk
from .errors import UsbCommunicationError

_logger = logging.getLogger(__name__)


class XdpcHandler(movelladot_sdk.XsDotCallback):
    def __init__(self, whitelist: list[str] = None):
        movelladot_sdk.XsDotCallback.__init__(self)

        self._manager: movelladot_sdk.XsDotConnectionManager = 0
        self._error_received = False
        self._update_done = False
        self._detected_dots: list[movelladot_sdk.XsPortInfo] = list()
        self._connected_dots: list[movelladot_sdk.XsDotDevice] = list()
        self._connected_usb_dots: list[movelladot_sdk.XsDotUsbDevice] = list()
        self._whitelist = whitelist

    def initialize(self):
        """
        Initialize the PC SDK

        - Prints the used PC SDK version to show we connected to XDPC
        - Constructs the connection manager used for discovering and connecting to DOTs
        - Connects this class as callback handler to the XDPC

        Returns:
            False if there was a problem creating a connection manager.
        """
        # Create connection manager
        self._manager = movelladot_sdk.XsDotConnectionManager()
        if self._manager is None:
            _logger.error("Manager could not be constructed, exiting.")
            raise UsbCommunicationError()

        # Attach callback handler (self) to connection manager
        self._manager.addXsDotCallbackHandler(self)
        return True

    def cleanup(self):
        """
        Close connections to any Movella DOT devices and destructs the connection manager created in initialize
        """
        self._manager.close()

    def scan_for_dots(self):
        """
        Scan if any Movella DOT devices can be detected via Bluetooth

        Enables device detection in the connection manager and uses the
        onAdvertisementFound callback to detect active Movella DOT devices
        Disables device detection when done

        """
        # Start a scan and wait until we have found one or more DOT Devices
        _logger.info("Scanning for devices...")
        self._manager.enableDeviceDetection()

        count = 0
        startTime = movelladot_sdk.XsTimeStamp_nowMs()
        while not self.error_received() and movelladot_sdk.XsTimeStamp_nowMs() - startTime <= 10000:
            time.sleep(0.1)

            connected = self.detected_dots()
            if len(connected) != count:
                count = len(connected)
                _logger.info(f"New dot connected, total of {count} connected.")

        self._manager.disableDeviceDetection()
        _logger.info("Stopped scanning for devices.")

    def connect_dots(self):
        """
        Connects to Movella DOTs found via either USB or Bluetooth connection

        Uses the isBluetooth function of the XsPortInfo to determine if the device was detected
        via Bluetooth or via USB. Then connects to the device accordingly
        When using Bluetooth, a retry has been built in, since wireless connection sometimes just fails the 1st time
        Connected devices can be retrieved using either connectedDots() or connectedUsbDots()

        USB and Bluetooth devices should not be mixed in the same session!
        """
        for port_info in self.detected_dots():
            if port_info.isBluetooth():
                address = port_info.bluetoothAddress()

                connected_devices_id = [x.deviceId() for x in self._connected_dots]
                while True:
                    if self._manager.openPort(port_info):
                        device: movelladot_sdk.XsDotDevice = self._manager.device(port_info.deviceId())
                        if device is None or not device.deviceTagName():
                            continue

                        if device.deviceId() not in connected_devices_id:
                            self._connected_dots.append(device)
                            break
                    else:
                        _logger.error(f"Connection to Device {address} failed")

                _logger.info(f"Found a device with Tag: {device.deviceTagName()} @ address: {address}")

            else:
                _logger.info(
                    f"Opening DOT with ID: {port_info.deviceId().toXsString()} @ port: {port_info.portName()}, baudrate: {port_info.baudrate()}"
                )
                if not self._manager.openPort(port_info):
                    _logger.error(f"Could not open DOT. Reason: {self._manager.lastResultText()}")
                    continue

                device = self._manager.usbDevice(port_info.deviceId())
                if device is None:
                    continue

                self._connected_usb_dots.append(device)
                _logger.info(f"Device: {device.productCode()}, with ID: {device.deviceId().toXsString()} opened.")

    def detect_usb_devices(self):
        """
        Scans for USB connected Movella DOT devices for data export
        """
        self._detected_dots = self._manager.detectUsbDevices()

    def detected_dots(self) -> list[movelladot_sdk.XsPortInfo]:
        """
        Returns:
             An XsPortInfoArray containing information on detected Movella DOT devices
        """
        return self._detected_dots

    def connected_dots(self) -> list[movelladot_sdk.XsDotDevice]:
        """
        Returns:
            A list containing an XsDotDevice pointer for each Movella DOT device connected via Bluetooth
        """
        return self._connected_dots

    def connected_usb_dots(self) -> list[movelladot_sdk.XsDotUsbDevice]:
        """
        Returns:
             A list containing an XsDotUsbDevice pointer for each Movella DOT device connected via USB */
        """
        return self._connected_usb_dots

    def error_received(self):
        """
        Returns:
             True if an error was received through the onError callback
        """
        return self._error_received

    def update_done(self):
        """
        Returns:
             Whether update done was received through the onDeviceUpdateDone callback
        """
        return self._update_done

    def reset_update_done(self):
        """
        Resets the update done member variable to be ready for a next device update
        """
        self._update_done = False

    def onAdvertisementFound(self, port_info: movelladot_sdk.XsPortInfo):
        """
        Called when an Movella DOT device advertisement was received. Updates m_detectedDots.
        Parameters:
            port_info: The XsPortInfo of the discovered information
        """
        if not self._whitelist or port_info.bluetoothAddress() in self._whitelist:
            self._detected_dots.append(port_info)
        else:
            _logger.debug(f"Ignoring {port_info.bluetoothAddress()}")

    def onError(self, result, errorString):
        """
        Called when an internal error has occurred. Prints to screen.
        Parameters:
            result: The XsResultValue related to this error
            errorString: The error string with information on the problem that occurred
        """
        _logger.error(f"Error: {movelladot_sdk.XsResultValue_toString(result)}: {errorString}")
        self._error_received = True

    def onDeviceUpdateDone(self, portInfo, result):
        """
        Called when the firmware update process has completed. Prints to screen.
        Parameters:
            portInfo: The XsPortInfo of the updated device
            result: The XsDotFirmwareUpdateResult of the firmware update
        """
        _logger.info(
            f"\n{portInfo.bluetoothAddress()}  Firmware Update done. Result: {movelladot_sdk.XsDotFirmwareUpdateResultToString(result)}"
        )
        self._update_done = True
