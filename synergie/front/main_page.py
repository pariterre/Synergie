import threading
from tkinter.font import BOLD, Font
import ttkbootstrap as ttkb
import webbrowser

from .dot_page import DotPage
from .extracting_page import ExtractingPage
from ..core.database.database_manager import DatabaseManager
from ..core.utils.dot_device import DotDevice
from ..core.utils.dot_manager import DotManager, DotConnexionStatus


class MainPage:
    def __init__(
        self,
        dots_connected: list[DotDevice],
        dot_manager: DotManager,
        database_manager: DatabaseManager,
        root: ttkb.Window = None,
    ) -> None:
        self._root = root
        self._dots_connected = dots_connected
        self._dot_manager = dot_manager
        self._database_manager = database_manager
        self._root.grid_rowconfigure(0, weight=1)
        self._root.grid_columnconfigure(0, weight=1)
        self._frame = ttkb.Frame(root)
        self._frame.grid_rowconfigure(0, weight=1, pad=50)
        self._frame.grid_rowconfigure(1, weight=1)
        self._frame.grid_columnconfigure(0, weight=1)
        button_style = ttkb.Style()
        button_style.configure("home.TButton", font=Font(self._frame, size=20, weight=BOLD))
        label_font = Font(self._root, size=15, weight=BOLD)
        self._waiting_frame = ttkb.Frame(self._frame)
        self._waiting_label = ttkb.Label(self._waiting_frame, text="Connexion aux capteurs USB...", font=label_font)
        self._waiting_label.grid(row=0, column=0, pady=50)
        waiting_progress = ttkb.Progressbar(self._waiting_frame, mode="indeterminate", length=200)
        waiting_progress.grid(row=1, column=0)
        waiting_progress.start(10)
        self._waiting_frame.grid(row=0, column=0)
        self._frame.grid(sticky="nswe")

        self._dot_page: DotPage = None
        self._estimated_time: float = -1
        self._save_data_to_file: ttkb.Checkbutton = None

    @property
    def dots_connected(self):
        return self._dots_connected

    @dots_connected.setter
    def dots_connected(self, dots_connected: list[DotDevice]):
        self._dots_connected = dots_connected
        self._make_dot_page()

    def connexion_status_changed(self, status: DotConnexionStatus):
        if status == DotConnexionStatus.CONNECTING_USB:
            self._waiting_label.config(text="Connexion aux capteurs USB...")
        elif status == DotConnexionStatus.CONNECTING_BLUETOOTH:
            self._waiting_label.config(text="Connexion aux capteurs Bluetooth...")
        elif status == DotConnexionStatus.IDENTIFYING_BLUETOOTH_DEVICES:
            self._waiting_label.config(text="Identification des capteurs Bluetooth...")
        elif status == DotConnexionStatus.CONNECTED:
            self._waiting_label.config(text="Connexion établie, lancement du monitoring...")
        else:
            self._waiting_label.config(text="Erreur de connexion, veuillez réessayer...")

    def _make_dot_page(self):
        self._frame.destroy()
        self._frame = ttkb.Frame(self._root)
        self._frame.grid_rowconfigure(0, weight=1)
        self._frame.grid_rowconfigure(1, weight=1)
        self._frame.grid_rowconfigure(2, weight=1)
        self._frame.grid_columnconfigure(0, weight=1)

        self._dot_page = DotPage(self._frame, self._dots_connected)
        self._dot_page.grid(row=0, column=0, sticky="nswe")

        self._make_export_button()

        label_font = Font(self._root, size=15, weight=BOLD)
        button_style = ttkb.Style()
        button_style.configure("home.TButton", font=Font(self._frame, size=20, weight=BOLD))
        usage_frame = ttkb.Frame(self._frame)
        usage_frame.grid_columnconfigure(0, weight=1, pad=200)
        usage_frame.grid_columnconfigure(1, weight=1)
        ttkb.Label(
            usage_frame,
            text="Débranchez un capteur pour commencer un enregistrement",
            font=label_font,
        ).grid(row=0, column=0)
        ttkb.Label(
            usage_frame,
            text="Rebranchez un capteur pour arrêter un enregistrement",
            font=label_font,
        ).grid(row=1, column=0)
        ttkb.Button(
            usage_frame,
            text="Ouvrir page de visualisation",
            style="home.TButton",
            command=lambda: webbrowser.open("https://synergie-qc.streamlit.app/"),
        ).grid(row=0, column=1, rowspan=2, sticky="nswe")
        usage_frame.grid(row=2, column=0)

        self._frame.grid(sticky="nswe")
        self._run_periodic_background_func()

    def _make_export_button(self):
        self._estimated_time = self._dot_manager.get_export_estimated_time()
        export_frame = ttkb.Frame(self._frame)
        ttkb.Button(
            export_frame,
            text=f"Exporter les données de tout les capteurs, temps estimé : {round(self._estimated_time,0)} min",
            style="home.TButton",
            command=self._export_all_dots,
        ).grid(row=0, column=0)
        self._save_data_to_file = ttkb.Checkbutton(
            export_frame, text="Sauvergarder plus de données (pour la recherche)"
        )
        self._save_data_to_file.state(["!alternate"])
        self._save_data_to_file.grid(row=1, column=0)
        export_frame.grid(row=1, column=0)

    def _export_all_dots(self):
        for device in self._dots_connected:
            if not device._is_recording and device.is_plugged and device.recording_count > 0:
                extract_event = threading.Event()
                threading.Thread(
                    target=device.export_data, args=([bool(self._save_data_to_file), extract_event]), daemon=True
                ).start()
                ExtractingPage(device.device_tag_name, self._estimated_time, extract_event)

    def _run_periodic_background_func(self):
        self._dot_page.updatePage()
        self._root.after(1000, self._run_periodic_background_func)
