import logging
import threading

from PIL import Image, ImageTk
from tkinter import messagebox
import ttkbootstrap as ttkb

from .connexion_page import ConnexionPage
from .img import logo_s2mjump_rgb_png_path
from .main_page import MainPage
from .starting_page import StartingPage
from .stoping_page import StopingPage
from ..core.database.database_manager import DatabaseManager
from ..core.utils.dot_manager import DotManager
from ..core.utils.errors import (
    InternetConnectionError,
    InvalidCertificateError,
    BluetoothCommunicationError,
    MissingSensorsError,
)

_logger = logging.getLogger(__name__)


class App:
    """
    The main application class that orchestrates the connection process,
    device (dot) management, and transitions between different pages (ConnectionPage,
    MainPage, StartingPage, and StoppingPage).

    This class initializes the database and dot managers, checks user
    connection status, manages dot connections, and launches appropriate UI pages.
    """

    def __init__(self, dots_white_list: list[str] = None):
        """
        Initialize the application
        """
        # Initialize the main application window.
        self._root_window = ttkb.Window(title="Synergie", themename="minty")
        self.maximize()

        # Load the icon for the application window.
        ico = Image.open(logo_s2mjump_rgb_png_path)
        self._root_window.wm_iconphoto(False, ImageTk.PhotoImage(ico))

        # Initialize the database manager and the dot manager.
        while True:
            try:
                self._database_manager = DatabaseManager(
                    certificate_path="s2m-skating-firebase-adminsdk-3ofmb-8552d58146.json"
                )
                break
            except InternetConnectionError:
                _logger.error("No internet connection available")
                messagebox.showerror(
                    "Connexion Internet",
                    "Aucune connexion Internet détectée. Veuillez vérifier votre réseau, puis cliquer sur OK",
                )
                continue
            except InvalidCertificateError:
                _logger.error("Invalid certificate")
                messagebox.showerror(
                    "Certificat Invalide",
                    "Le certificat fourni n'est pas valide. Veuillez vérifier le fichier fourni et relancer l'application.",
                )
                exit()
            except Exception as e:
                _logger.error(f"Unknown error while initializing the DatabaseManager: {e}")
                messagebox.showerror(
                    "Erreur",
                    "Une erreur inconnue est survenue lors de la connexion à la base de données.",
                )
                exit()

        self._dots_white_list = dots_white_list if dots_white_list else {}
        self._dot_manager = DotManager(self._database_manager)

        # Launch the ConnectionPage to prompt user login.
        self._connexion_page = ConnexionPage(self._root_window, self._database_manager)

        # Check periodically if the user has logged in.
        try:
            self._check_connexion()
        except BluetoothCommunicationError:
            _logger.error("Bluetooth communication error")
            messagebox.showerror(
                "Erreur de Communication Bluetooth",
                "Une erreur de communication Bluetooth est survenue. Veuillez vérifier vos appareils et relancer l'application.",
            )
            exit()

    def run(self):
        """
        Start the main event loop of the application.
        """
        self._root_window.mainloop()

    def maximize(self) -> None:
        """
        Maximize the application window.
        """
        width = self._root_window.winfo_screenwidth()
        height = self._root_window.winfo_screenheight()
        self._root_window.geometry(f"{width}x{height}")

    def _check_connexion(self):
        """
        Periodically check if the user is connected. If the user is connected,
        destroy the connection frame and launch the main page. Otherwise,
        schedule another check.
        """
        if not self._connexion_page.user_id:
            self._root_window.after(100, self._check_connexion)
            return

        # User is connected, store the user id and move to the main page.
        self._connexion_page.destroy()
        self._root_window.update()
        self._show_launch_main_page()

    def _show_launch_main_page(self):
        """
        Launch the MainPage once the user is connected. This sets up
        an asynchronous initialization process to detect and connect dots.
        """
        # Initialize main page with empty list of dots (will be updated later).
        self._main_page = MainPage([], self._dot_manager, self._database_manager, self._root_window)

        # Run the initialization in a separate thread to avoid blocking the UI.
        initialialize_event = threading.Event()
        threading.Thread(
            target=self._initialize_dot_manager,
            args=([initialialize_event]),
            daemon=True,
        ).start()
        self._wait_for_event(initialialize_event, self._show_dots_connected_page)

    def _show_dots_connected_page(self):
        """
        Show the MainPage once all devices are connected.
        """
        self._main_page.dots_connected = self._dot_manager.get_devices()

    def _wait_for_event(self, event: threading.Event, callback_when_set: callable):
        """
        Wait for a given event to be set.

        Args:
            event (threading.Event): The event to wait for.
        """
        if not event.is_set():
            self._root_window.after(100, self._wait_for_event, event, callback_when_set)
            return

        callback_when_set()
        event.clear()

    def _initialize_dot_manager(self, initialialize_event: threading.Event):
        """
        Attempt the first connection to all necessary devices (dots).
        If any device is not connected, prompt the user to retry until all
        are connected or the user cancels. Once successful, start a separate thread
        to monitor device connections/disconnections (USB events).

        Args:
            initialialize_event (threading.Event): An event to set once initialization is done.
        """
        while True:
            try:
                self._dot_manager.initialize_connexion(dots_white_list=self._dots_white_list)
                break
            except MissingSensorsError as e:
                _logger.error(f"Missing sensors: {e.sensor_names}")
                messagebox.showerror(
                    "Capteurs Manquants",
                    f"Veuillez reconnecter les capteurs : {', '.join(e.sensor_names)}",
                )

        # Notify the main thread that initialization is done.
        self._dot_manager.start_usb_monitoring(self._show_start_page, self._show_stopping_page)
        initialialize_event.set()

    def _show_start_page(self, device):
        """
        Launch the StartingPage for a given device to start a new recording.

        Args:
            device: The device instance to start recording.
        """
        StartingPage(device, self._database_manager, self._connexion_page.user_id)

    def _show_stopping_page(self, device):
        """
        Launch the StopingPage for a given device to stop recording.

        Args:
            device: The device instance that needs to be stopped.
        """
        StopingPage(device, self._database_manager)
