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