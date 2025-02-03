import threading
import time

from tkinter.font import BOLD, Font
import ttkbootstrap as ttkb


class ExtractingPage:
    def __init__(self, device_tag: str, estimated_time, event: threading.Event) -> None:
        self._device_tag = device_tag
        self._event = event

        self._window = ttkb.Toplevel(title="Confirmation", size=(1000, 400), topmost=True)
        self._window.place_window_center()
        self._window.grid_columnconfigure(0, weight=1)
        self._window.grid_rowconfigure(0, weight=1)
        self._window.grid_rowconfigure(1, weight=1)
        self.text = ttkb.StringVar(
            self._window,
            value=f"Extraction des données du capteur {self._device_tag} \nNe pas déconnecter ce capteur",
        )
        self._label = ttkb.Label(
            self._window,
            textvariable=self.text,
            font=Font(self._window, size=20, weight=BOLD),
        )
        self._label.grid(row=0, column=0)
        self._max_value = 60 * estimated_time
        self._progress_extract = ttkb.Progressbar(
            self._window,
            value=0,
            maximum=self._max_value,
            length=self._label.winfo_reqwidth(),
            style="success.Striped.Horizontal.TProgressbar",
            mode="determinate",
        )
        self._progress_extract.start(1000)
        self._progress_extract.grid(row=1, column=0)
        self._check_finish()

    def _check_finish(self):
        try:
            self._check_progress_bar()
        except:
            pass
        if self._event.is_set():
            self.text.set("Extraction finie")
            self._label.update()
            time.sleep(1)
            self._window.destroy()
        self._window.after(1000, self._check_finish)

    def _check_progress_bar(self):
        if self._progress_extract["value"] >= self._max_value - 1:
            self._progress_extract.stop()
            self._progress_extract["value"] = self._max_value
