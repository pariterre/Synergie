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