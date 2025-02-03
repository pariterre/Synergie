class InternetConnectionError(Exception):
    def __init__(self):
        self.message = "No internet connection available"
        super().__init__(self.message)

    def __str__(self):
        return self.message


class InvalidCertificateError(Exception):
    def __init__(self):
        self.message = "Invalid certificate"
        super().__init__(self.message)

    def __str__(self):
        return self.message


class DeviceNotFoundError(Exception):
    def __init__(self, device_id: str):
        self._device_id = device_id
        self.message = f"Device with id {self._device_id} not found"
        super().__init__(self.message)

    def __str__(self):
        return self.message


class UsbCommunicationError(Exception):
    def __init__(self):
        self.message = "USB communication error"
        super().__init__(self.message)

    def __str__(self):
        return self.message


class BluetoothCommunicationError(Exception):
    def __init__(self):
        self.message = "Bluetooth communication error"
        super().__init__(self.message)

    def __str__(self):
        return self.message


class MissingSensorsError(Exception):
    def __init__(self, sensor_names: list[str]):
        self.sensor_names = sensor_names
        self.message = "Missing sensors: " + ", ".join(self.sensor_names)
        super().__init__(self.message)

    def __str__(self):
        return self.message


class NoDataFoundForIdError(Exception):
    def __init__(self, data_type: str, data_id: str):
        self._data_id = data_id
        self._data_type = data_type
        self.message = f"No {self._data_type} found with id: {self._data_id}"
        super().__init__(self.message)

    def __str__(self):
        return self.message
