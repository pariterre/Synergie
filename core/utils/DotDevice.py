from datetime import datetime
import logging
import os
from threading import Event
import time

import movelladot_pc_sdk
import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFont, ImageTk

import constants
from core.database.DatabaseManager import DatabaseManager, JumpData
from .movella_loader import movelladot_sdk

_logger = logging.getLogger(__name__)


def initialize_bluetooth_dot_device(
        bluetooth_manager: movelladot_sdk.XsDotConnectionManager, 
        port_info_bluetooth: movelladot_sdk.XsPortInfo,
    ) -> movelladot_sdk.XsDotDevice:
    """
    Initialize the Bluetooth connection

    Raises:
        Exception: If the connection to the device fails
    """
    while True:
        bluetooth_manager.closePort(port_info_bluetooth)
        if bluetooth_manager.openPort(port_info_bluetooth):
            device: movelladot_sdk.XsDotDevice = bluetooth_manager.device(port_info_bluetooth.deviceId())
            if device:
                time.sleep(1)
                if device.deviceTagName() and device.batteryLevel():
                    return device
        _logger.warning(f"Bluetooth device {port_info_bluetooth.bluetoothAddress()} failed, retrying...")


class DotDevice(movelladot_sdk.XsDotCallback):
    """
    Manages individual sensors (dots) connected via Bluetooth and USB.
    """

    def __init__(
        self,
        port_info_usb: movelladot_sdk.XsPortInfo,
        port_info_bluetooth: movelladot_sdk.XsPortInfo,
        database_manager: DatabaseManager,
    ):
        super().__init__()

        self._database_manager = database_manager

        self._port_info_usb = port_info_usb
        self._usb_manager = movelladot_sdk.XsDotConnectionManager()
        while self._usb_manager is None:
            self._usb_manager = movelladot_sdk.XsDotConnectionManager()
        self._usb_manager.addXsDotCallbackHandler(self)
        self._usb_device: movelladot_sdk.XsDotUsbDevice = None
        self._initialize_usb()

        self._port_info_bluetooth = port_info_bluetooth
        self._bluetooth_manager = movelladot_sdk.XsDotConnectionManager()
        while self._bluetooth_manager is None:
            self._bluetooth_manager = movelladot_sdk.XsDotConnectionManager()
        self._bluetooth_manager.addXsDotCallbackHandler(self)
        self._bluetooth_device: movelladot_sdk.XsDotDevice = None
        self._bluetooth_device = initialize_bluetooth_dot_device(
            bluetooth_manager=self._bluetooth_manager, port_info_bluetooth=self._port_info_bluetooth
        )

        self._is_recording = self._usb_device.recordingCount() == -1
        if self._is_recording:
            self._recording_count = 0
        else:
            self._recording_count = self._usb_device.recordingCount()
        self._is_battery_charging = False
        self._is_plugged = True
        self._timing_record = datetime.now().timestamp()

        self._load_images()
        self._current_image = self._image_active

        self._save_data_to_file = False
        self._count = 0
        self._packets_received = []
        self._synchro_time = 0
        self._export_done = False

        _logger.info(
            f"DotDevice initialized: {self.device_tag_name} (ID: {self.deviceId})"
        )

    @property
    def is_recording(self) -> bool:
        return self._is_recording

    @property
    def device_id(self) -> str:
        return str(self._usb_device.deviceId())

    @property
    def device_tag_name(self) -> str:
        return str(self._bluetooth_device.deviceTagName())

    @property
    def battery_level(self) -> int:
        return self._bluetooth_device.batteryLevel()

    @property
    def timing_record(self) -> float:
        return self._timing_record

    @property
    def is_plugged(self) -> bool:
        return self._is_plugged

    @property
    def is_battery_charging(self) -> bool:
        return self._is_battery_charging

    @property
    def current_image(self) -> ImageTk.PhotoImage:
        return self._current_image

    @property
    def recording_count(self) -> int:
        return self._recording_count

    def _initialize_usb(self):
        """
        Initialize the USB connection
        """

        if hasattr(self._port_info_usb, "serial"):
            serial_info = self._port_info_usb.serial
        elif hasattr(self._port_info_usb, "serialNumber"):
            serial_info = self._port_info_usb.serialNumber
        else:
            serial_info = "Unknown Serial"

        self._usb_manager.closePort(self._port_info_usb)
        while True:
            self._usb_manager.openPort(self._port_info_usb)
            device = self._usb_manager.usbDevice(self._port_info_usb.deviceId())
            if device:
                break
            _logger.warning(f"Connection to USB Device {serial_info} failed")

        _logger.info(f"USB connection established with device ID: {self.device_id}")
        self._usb_device = device
        self.is_plugged = True

    def _load_images(self):
        """
        Load the images for the active and inactive states of the sensor.
        """
        base_folder = os.path.dirname(
            __file__
        )  # TODO : This can be changed to relative with a proper packaging
        font_tag = ImageFont.truetype(font="arialbd.ttf", size=60)

        text = self.device_tag_name
        text_offset_x = 93 if len(text) == 1 else 75

        img_active = Image.open(f"{base_folder}/resources/img/dot_active.png")
        d = ImageDraw.Draw(img_active)
        d.text((text_offset_x, 65), text, font=font_tag, fill="black")
        img_active = img_active.resize((116, 139))
        self._image_active = ImageTk.PhotoImage(img_active)

        # Load inactive image
        img_inactive = Image.open(f"{base_folder}/resources/img/dot_inactive.png")
        d = ImageDraw.Draw(img_inactive)
        d.text((text_offset_x, 65), text, font=font_tag, fill="black")
        img_inactive = img_inactive.resize((116, 139))
        self._image_inactive = ImageTk.PhotoImage(img_inactive)

    def start_recording(self) -> bool:
        """
        Start recording on the sensor

        Returns:
        bool: Whether the recording was started successfully
        """

        if not self._bluetooth_device.startRecording():
            _logger.warning(
                "Failed to start recording on Bluetooth device. Trying to reconnect once..."
            )
            self._bluetooth_device = initialize_bluetooth_dot_device(
                bluetooth_manager=self._bluetooth_manager, port_info_bluetooth=self._port_info_bluetooth
            )
            if not self._bluetooth_device.startRecording():
                _logger.warning("Failed to start recording on Bluetooth device.")
                return False

        self._timing_record = datetime.now().timestamp()
        self._is_recording = True
        _logger.info(f"Recording started at {self.timing_record} seconds.")
        return True

    def stop_recording(self) -> bool:
        """
        Stop recording on the sensor

        Returns:
        bool: Whether the recording was stopped successfully
        """

        if not self._bluetooth_device.stopRecording():
            _logger.warning(
                "Failed to stop recording on Bluetooth device. Trying to reconnect once..."
            )
            self._bluetooth_device = initialize_bluetooth_dot_device(
                bluetooth_manager=self._bluetooth_manager, port_info_bluetooth=self._port_info_bluetooth
            )
            if not self._bluetooth_device.stopRecording():
                _logger.warning("Failed to stop recording on Bluetooth device.")
                return False

        self._is_recording = False
        self._recording_count = self._usb_device.recordingCount()
        self._current_image = self._image_inactive
        _logger.info(f"Recording stopped at {datetime.now().timestamp()} seconds.")
        return True

    def export_data(self, save_data_to_file: bool, extract_event: Event):
        """
        Export the sensor data

        Args:
        save_data_to_file : Whether to save all available data (not just the data needed for the models)
        extract_event : Event to inform the main thread that the extraction is complete

        Raises:
        Exception: If the export fails
        """
        _logger.info("Exporting data from sensor...")

        self._save_data_to_file = save_data_to_file
        self._export_done = False
        self._packets_received = []
        self._count = 0
        data = movelladot_pc_sdk.XsIntArray()
        # Define the types of data to export
        data.push_back(movelladot_pc_sdk.RecordingData_Timestamp)
        data.push_back(movelladot_pc_sdk.RecordingData_Euler)
        data.push_back(movelladot_pc_sdk.RecordingData_Acceleration)
        data.push_back(movelladot_pc_sdk.RecordingData_AngularVelocity)
        if self._save_data_to_file:
            data.push_back(movelladot_pc_sdk.RecordingData_MagneticField)
            data.push_back(movelladot_pc_sdk.RecordingData_Quaternion)
            data.push_back(movelladot_pc_sdk.RecordingData_Status)

        # Select the data types for export
        if not self._usb_device.selectExportData(data):
            _logger.error(
                f"Could not select export data. Reason: {self._usb_device.lastResultText()}"
            )
            self._export_done = True
            return

        # Iterate through each recording and export data
        for index in range(1, self._usb_device.recordingCount() + 1):
            rec_info = self._usb_device.getRecordingInfo(index)
            if rec_info.empty():
                _logger.warning(
                    f"Could not get recording info. Reason: {self._usb_device.lastResultText()}"
                )
                continue  # Skip to the next recording

            record_date = rec_info.startUTC()
            training_id = self._database_manager.get_current_record(self.device_id)
            if training_id:
                self._database_manager.set_training_date(training_id, record_date)
                if not self._usb_device.startExportRecording(index):
                    _logger.error(
                        f"Could not export recording. Reason: {self._usb_device.lastResultText()}"
                    )
                    continue

                while not self._export_done:
                    time.sleep(0.1)
                _logger.info("File export finished!")

                columnSelected = [
                    "PacketCounter",
                    "SampleTimeFine",
                    "Euler_X",
                    "Euler_Y",
                    "Euler_Z",
                ]
                if self._save_data_to_file:
                    columnSelected += [
                        "Quat_W",
                        "Quat_X",
                        "Quat_Y",
                        "Quat_Z",
                        "Acc_X",
                        "Acc_Y",
                        "Acc_Z",
                        "Gyr_X",
                        "Gyr_Y",
                        "Gyr_Z",
                        "Mag_X",
                        "Mag_Y",
                        "Mag_Z",
                    ]
                else:
                    columnSelected += [
                        "Acc_X",
                        "Acc_Y",
                        "Acc_Z",
                        "Gyr_X",
                        "Gyr_Y",
                        "Gyr_Z",
                    ]

                df = pd.DataFrame.from_records(
                    self._packets_received, columns=columnSelected
                )
                date = datetime.fromtimestamp(record_date).strftime("%Y_%m_%d")
                start_sample_time = df["SampleTimeFine"].iloc[0]  # TODO Check the iloc
                new_sample_time_fine = []
                for timeFine in df["SampleTimeFine"]:
                    new_time = timeFine - start_sample_time
                    if new_time < 0:
                        new_sample_time_fine.append(new_time + 2**32)
                    else:
                        new_sample_time_fine.append(new_time)
                df["SampleTimeFine"] = new_sample_time_fine
                self._synchro_time = max(0, self._synchro_time - start_sample_time)

                csv_path = f"data/raw/{date}/{self._synchro_time}_{training_id}.csv"
                os.makedirs(os.path.dirname(csv_path), exist_ok=True)
                df.to_csv(csv_path, index=False)
                _logger.info(f"Data exported to {csv_path}")

                # Predict training data and update the database
                self.predict_training(training_id, df)
                self._database_manager.remove_current_record(self.deviceId, training_id)
                self._recording_count -= 1

        # Erase sensor's flash memory after exporting
        self._usb_device.eraseFlash()
        _logger.info("You can disconnect the dot.")
        self._recording_count = 0
        extract_event.set()
        self._current_image = self._image_active

    def predict_training(self, training_id: str, df: pd.DataFrame):
        from core.data_treatment.data_generation.exporter import export

        """
        Predict the training data and update the database
        """
        try:
            df = export(df)
            _logger.info("End of data processing.")
            training_jumps = []
            unknow_rotation = []
            for _, row in df.iterrows():
                jump_time_min, jump_time_sec = row["videoTimeStamp"].split(":")
                jump_time = "{:02d}:{:02d}".format(
                    int(jump_time_min), int(jump_time_sec)
                )
                val_rot = float(row["rotations"])

                if row["type"] < 5 and val_rot > 0.5:
                    if val_rot < 2:
                        val_rot = np.ceil(val_rot - 0.3)
                    else:
                        val_rot = np.ceil(val_rot - 0.15)
                    jump_data = JumpData(
                        0,
                        training_id,
                        constants.JumpType(int(row["type"])).name,
                        val_rot,
                        bool(row["success"]),
                        jump_time,
                        float(row["rotation_speed"]),
                        float(row["length"]),
                    )
                    training_jumps.append(jump_data.to_dict())
                elif row["type"] == 5 and val_rot > 0.8:
                    val_rot = np.ceil(val_rot - 0.7) + 0.5
                    jump_data = JumpData(
                        0,
                        training_id,
                        constants.JumpType(int(row["type"])).name,
                        val_rot,
                        bool(row["success"]),
                        jump_time,
                        float(row["rotation_speed"]),
                        float(row["length"]),
                    )
                    training_jumps.append(jump_data.to_dict())
                else:
                    jump_data = JumpData(
                        0,
                        training_id,
                        constants.JumpType(int(row["type"])).name,
                        0,
                        bool(row["success"]),
                        jump_time,
                        float(row["rotation_speed"]),
                        float(row["length"]),
                    )
                    unknow_rotation.append(jump_data)

            if training_jumps:
                self._database_manager.add_jumps_to_training(
                    training_id, training_jumps
                )
            else:
                for jump in unknow_rotation:
                    training_jumps.append(jump.to_dict())
                self._database_manager.add_jumps_to_training(
                    training_id, training_jumps
                )

            _logger.info(f"Training {training_id} updated with jump data.")

        except Exception as e:
            _logger.error(f"Error during prediction training: {e}")

    def onRecordedDataAvailable(self, device, packet: movelladot_sdk.XsDataPacket):
        """
        Callback function that is called when data is available
        """
        self._count += 1
        euler = packet.orientationEuler()
        captor = packet.calibratedData()
        if self._save_data_to_file:
            quaternion = packet.orientationQuaternion()
            data = np.concatenate(
                [
                    [
                        int(self._count),
                        packet.sampleTimeFine(),
                        euler.x(),
                        euler.y(),
                        euler.z(),
                    ],
                    quaternion,
                    captor.m_acc,
                    captor.m_gyr,
                    captor.m_mag,
                ]
            )
        else:
            data = np.concatenate(
                [
                    [
                        int(self._count),
                        packet.sampleTimeFine(),
                        euler.x(),
                        euler.y(),
                        euler.z(),
                    ],
                    captor.m_acc,
                    captor.m_gyr,
                ]
            )
        self._packets_received.append(data)

    def onRecordedDataDone(self, device):
        """
        Callback function that is called when the data are done recording
        """
        self._export_done = True

    def __eq__(self, device) -> bool:
        """
        Check if two devices are the same
        """
        return (self._usb_device == device.usbDevice) and (
            self._bluetooth_device == device.btDevice
        )

    def get_export_estimated_time(self) -> int:
        """
        Get the estimated time to export
        """
        estimatedTime = 0
        for index in range(1, self._usb_device.recordingCount() + 1):
            storage_size = self._usb_device.getRecordingInfo(index).storageSize()
            estimatedTime = estimatedTime + round(storage_size / (237568 * 8), 1)
        return estimatedTime + 1

    def onBatteryUpdated(
        self, device: movelladot_sdk.XsDotDevice, battery_level: int, charging_status: int
    ):
        """
        Callback function that is called when the battery level is updated
        """
        self._is_battery_charging = charging_status == 1
        _logger.info(
            f"Battery level updated: {battery_level}%, Charging: {self._is_battery_charging}"
        )

    def onButtonClicked(self, device: movelladot_sdk.XsDotDevice, timestamp: int):
        """
        Callback function that is called when the button is clicked
        """
        self._synchro_time = timestamp
        _logger.info(f"Button clicked at timestamp: {self._synchro_time}")

    def close_usb(self):
        """
        Close the USB connection
        """
        self._usb_manager.closePort(self._port_info_usb)
        self._is_plugged = False
        _logger.info("USB connection closed.")

    def open_usb(self):
        """
        Open the USB connection
        """
        if hasattr(self._port_info_usb, "serial"):
            serial_info = self._port_info_usb.serial
        elif hasattr(self._port_info_usb, "serialNumber"):
            serial_info = self._port_info_usb.serialNumber
        else:
            serial_info = "Unknown Serial"

        while True:
            self._usb_manager.openPort(self._port_info_usb)
            device = self._usb_manager.usbDevice(self._port_info_usb.deviceId())
            if device:
                break
            _logger.warning(f"Connection to USB Device {serial_info} failed")

        self._usb_device = device
        _logger.info("USB connection opened.")

        if self.is_recording:
            _logger.info("USB device is currently recording. Stopping recording...")
            self.stop_recording()

        self._is_plugged = True
