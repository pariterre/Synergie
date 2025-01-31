import logging
import time
import threading
import sys

from PIL import Image, ImageTk
from tkinter import messagebox
import ttkbootstrap as ttkb

# TODO Move this in a synergy package
from core.database.DatabaseManager import DatabaseManager
from core.utils.errors import InternetConnectionError, InvalidCertificateError, BluetoothCommunicationError, MissingSensorsError
from core.utils.DotManager import DotManager
from front.ConnectionPage import ConnectionPage
from front.MainPage import MainPage
from front.StartingPage import StartingPage
from front.StopingPage import StopingPage

_logger = logging.getLogger(__name__)


class App:
    """
    The main application class that orchestrates the connection process,
    device (dot) management, and transitions between different pages (ConnectionPage,
    MainPage, StartingPage, and StoppingPage).

    This class initializes the database and dot managers, checks user
    connection status, manages dot connections, and launches appropriate UI pages.
    """

    def __init__(self, root: ttkb.Window):
        """
        Initialize the application with the given root window.

        Args:
            root (ttkb.Window): The main application window (tkinter-based).
        """
        # Initialize the database manager and the dot manager.
        while True:
            try: 
                self.db_manager = DatabaseManager(certificate_path="s2m-skating-firebase-adminsdk-3ofmb-8552d58146.json")
                break
            except InternetConnectionError:
                _logger.error("No internet connection available")
                messagebox.showerror("Connexion Internet", "Aucune connexion Internet détectée. Veuillez vérifier votre réseau, puis cliquer sur OK")
                continue
            except InvalidCertificateError:
                _logger.error("Invalid certificate")
                messagebox.showerror("Certificat Invalide", "Le certificat fourni n'est pas valide. Veuillez vérifier le fichier fourni et relancer l'application.")
                exit()
            except Exception as e:
                _logger.error(f"Unknown error while initializing the DatabaseManager: {e}")
                messagebox.showerror("Erreur", "Une erreur inconnue est survenue lors de la connexion à la base de données.")
                exit()
            
                
        self.dot_manager = DotManager(self.db_manager)

        # Store the root window for later use in the application.
        self.root = root

        # Launch the ConnectionPage to prompt user login.
        self.connectionPage = ConnectionPage(self.root, self.db_manager)

        # Check periodically if the user has logged in.
        try:
            self.checkConnection()
        except BluetoothCommunicationError:
            _logger.error("Bluetooth communication error")
            messagebox.showerror(
                "Erreur de Communication Bluetooth", 
                "Une erreur de communication Bluetooth est survenue. Veuillez vérifier vos appareils et relancer l'application."
            )
            exit()

    def checkConnection(self):
        """
        Periodically check if the user is connected. If the user is connected,
        destroy the connection frame and launch the main page. Otherwise,
        schedule another check.
        """
        if self.connectionPage.userConnected != "":
            # User is connected, store the user id and move to the main page.
            self.userConnected = self.connectionPage.userConnected
            self.connectionPage.frame.destroy()
            self.root.update()
            self.launchMainPage()
        else:
            # User not connected yet, recheck after 100 ms.
            self.root.after(100, self.checkConnection)

    def launchMainPage(self):
        """
        Launch the MainPage once the user is connected. This sets up
        an asynchronous initialization process to detect and connect dots.
        """
        # Initialize main page with empty list of dots (will be updated later).
        self.mainPage = MainPage([], self.dot_manager, self.db_manager, self.root)

        # Create an event to signal when initialization is complete.
        self.initialEvent = threading.Event()

        # Run the initialization in a separate thread to avoid blocking the UI.
        threading.Thread(target=self.initialize, args=([self.initialEvent]), daemon=True).start()

        # Check periodically if initialization is done.
        self.checkInit()

    def checkInit(self):
        """
        Once the initialization (first device connection attempt) is complete,
        update the main page with the connected devices and display them.
        """
        if self.initialEvent.is_set():
            # Initialization is done, update dots in the MainPage.
            self.mainPage.dotsConnected = self.dot_manager.get_devices()
            self.mainPage.make_dot_page()
            # Clear the event for potential future use if needed.
            self.initialEvent.clear()
        else:
            # Not initialized yet, check again after 100 ms.
            self.root.after(100, self.checkInit)

    def initialize(self, initialEvent: threading.Event):
        """
        Attempt the first connection to all necessary devices (dots).
        If any device is not connected, prompt the user to retry until all
        are connected or the user cancels. Once successful, start a separate thread
        to monitor device connections/disconnections (USB events).

        Args:
            initialEvent (threading.Event): An event to set once initialization is done.
        """
        while True:
            try:
                self.dot_manager.initialize_connexion()
                break
            except MissingSensorsError as e:
                _logger.error(f"Missing sensors: {e.sensor_names}")
                messagebox.showerror(
                    "Capteurs Manquants", f"Veuillez reconnecter les capteurs : {', '.join(e.sensor_names)}"
                )
        
        # Now that all devices are connected, check if any are currently recording.
        devices = self.dot_manager.get_devices()
        for device in devices:
            if device._bluetooth_device.stopRecording() is True:
               _logger.info(f"{device.device_tag_name} was recording and was stopped")

        initialEvent.set()

        
        # Start a separate thread to monitor device connections/disconnections.
        # TODO This should be done by the DotManager
        usb_detection_thread = threading.Thread(
            target=self.check_usb_dots,
            args=([self.startStarting, self.startStopping]),
            daemon=True,
        )
        usb_detection_thread.start()

    def check_usb_dots(self, start_recording_callback, stop_recording_callback):
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
            self.dot_manager.check_plug_statuses(start_recording_callback=start_recording_callback, stop_recording_callback=stop_recording_callback)

            # Wait a short time before checking again.
            time.sleep(0.2)

    def startStopping(self, device):
        """
        Launch the StopingPage for a given device to stop recording.

        Args:
            device: The device instance that needs to be stopped.
        """
        StopingPage(device, self.db_manager)

    def startStarting(self, device):
        """
        Launch the StartingPage for a given device to start a new recording.

        Args:
            device: The device instance to start recording.
        """
        StartingPage(device, self.db_manager, self.userConnected)


# Entry point of the application.
if __name__ == "__main__":
    # Set up the logging configuration.
    logging.basicConfig(level=logging.INFO)

    # Initialize the main application window.
    root = ttkb.Window(title="Synergie", themename="minty")

    # Create an instance of the App class with the root window.
    myapp = App(root)

    # Maximize the window to the screen size.
    width = root.winfo_screenwidth()
    height = root.winfo_screenheight()
    root.geometry(f"{width}x{height}")

    # Try to load the application icon from the PyInstaller bundle or from a local path.
    ico = Image.open('resources/img/logo_s2mjump_rgb.png')

    photo = ImageTk.PhotoImage(ico)
    root.wm_iconphoto(False, photo)

    # Start the main event loop.
    root.mainloop()
