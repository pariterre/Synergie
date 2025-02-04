import threading
import time

from PIL import Image, ImageTk
from tkinter.font import BOLD, Font
import ttkbootstrap as ttkb

from .img import logo_s2mjump_rgb_png_path
from ..core.database.database_manager import DatabaseManager
from ..core.utils.dot_device import DotDevice


class StopingPage:
    def __init__(self, device: DotDevice, db_manager: DatabaseManager) -> None:
        self._device = device
        self._database_manager = db_manager
        self._device_tag = self._device.device_tag_name
        self._window = ttkb.Toplevel(title="Confirmation", size=(1000, 400), topmost=True)
        self._window.place_window_center()

        ico = Image.open(logo_s2mjump_rgb_png_path)
        photo = ImageTk.PhotoImage(ico)
        self._window.wm_iconphoto(False, photo)
        self._window.grid_rowconfigure(0, weight=1)
        self._window.grid_columnconfigure(0, weight=1)
        self._frame = ttkb.Frame(self._window)
        self._frame.grid_rowconfigure(0, weight=0)
        self._frame.grid_rowconfigure(1, weight=1)
        self._frame.grid_rowconfigure(2, weight=1)
        self._frame.grid_columnconfigure(0, weight=1)
        label = ttkb.Label(
            self._frame,
            text=f"Arrêtez l'enregistrement du capteur {self._device_tag}",
            font=Font(self._window, size=20, weight=BOLD),
        )
        label.grid(row=0, column=0, pady=20)
        button_style = ttkb.Style()
        button_style.configure("my.TButton", font=Font(self._frame, size=12, weight=BOLD))
        ttkb.Button(self._frame, text="Arrêt", style="my.TButton", command=self._stop_record).grid(
            row=1, column=0, sticky="nsew", pady=20
        )
        self._estimated_time = self._device.get_export_estimated_time()
        ttkb.Button(
            self._frame,
            text=f"Arrêt et extraction des données \n Temps estimé : {round(self._estimated_time,0)} min",
            style="my.TButton",
            command=self._stop_record_and_extract,
        ).grid(row=2, column=0, sticky="nsew")
        self._save_data_to_file = ttkb.Checkbutton(self._frame, text="Sauvegarder plus de données (pour la recherche)")
        self._save_data_to_file.state(["!alternate"])
        self._save_data_to_file.grid(row=3, column=0, sticky="nsew")
        self._frame.grid(sticky="nswe")
        self._window.grid()

    def _stop_record(self):
        record_stopped = self._device.stop_recording()
        self._frame.destroy()
        self._frame = ttkb.Frame(self._window)
        if record_stopped:
            message = f"Enregistrement stoppé sur le capteur {self._device_tag}"
        else:
            message = "Erreur durant l'arrêt, impossible d'arrêter l'enregistrement"
        label = ttkb.Label(self._frame, text=message, font=Font(self._window, size=20, weight=BOLD))
        label.grid()
        self._frame.grid()
        self._window.update()
        time.sleep(1)
        self._window.destroy()

    def _stop_record_and_extract(self):
        record_stopped = self._device.stop_recording()
        _save_data_to_file = self._save_data_to_file.instate(["selected"])
        self._frame.destroy()
        self._frame = ttkb.Frame(self._window)
        self._frame.grid_columnconfigure(0, weight=1)
        self._frame.grid_rowconfigure(0, weight=1)
        self._frame.grid_rowconfigure(1, weight=1)
        if record_stopped:
            message = f"Enregistrement stoppé sur le capteur {self._device_tag}"
        else:
            message = "Erreur durant l'arrêt, impossible d'arrêter l'enregistrement"
        self._text = ttkb.StringVar(self._frame, value=message)
        self._label = ttkb.Label(
            self._frame,
            textvariable=self._text,
            font=Font(self._window, size=20, weight=BOLD),
        )
        self._label.grid(row=0, column=0, pady=50)
        self._frame.grid()
        self._window.update()
        time.sleep(1)

        self._text.set(f"Extraction des données du capteur {self._device_tag} \nNe pas deconnecter ce capteur")
        self._label.update()
        self._max_value = 60 * self._estimated_time
        self._progress_extract = ttkb.Progressbar(
            self._frame,
            value=0,
            maximum=self._max_value,
            style="success.Striped.Horizontal.TProgressbar",
            mode="determinate",
        )
        self._progress_extract.start(1000)
        self._progress_extract.grid(row=1, column=0, sticky="we")
        self._frame.grid()
        self._window.update()
        self._extract_event = threading.Event()
        self._check_finish()
        if record_stopped:
            threading.Thread(
                target=self._device.export_data,
                args=([_save_data_to_file, self._extract_event]),
                daemon=True,
            ).start()
        else:
            self._extract_event.set()

    def _check_finish(self):
        try:
            self._check_progress_bar()
        except:
            pass
        self._window.update()
        if self._extract_event.is_set():
            self._text.set("Extraction terminée")
            self._label.update()
            time.sleep(1)
            self._window.destroy()
        self._window.after(1000, self._check_finish)

    def _check_progress_bar(self):
        if self._progress_extract["value"] >= self._max_value - 1:
            self._progress_extract.stop()
            self._progress_extract["value"] = self._max_value
