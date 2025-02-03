from datetime import datetime
from tkinter.font import BOLD, Font
import ttkbootstrap as ttkb

from ..core.utils.dot_device import DotDevice


class DotFrame(ttkb.Frame):
    def __init__(self, parent, device: DotDevice, **kwargs) -> None:
        super().__init__(parent, **kwargs)
        self.parent = parent
        self._device = device
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=1)
        self.grid_rowconfigure(3, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._image_label = ttkb.Label(self, image=self._device.current_image)
        self._image_label.grid(row=0, column=0)
        label_font = Font(self, size=15, weight=BOLD)
        self._plugged_label = ttkb.Label(self, text=f"En charge : {self._device.is_plugged}", font=label_font)
        self._plugged_label.grid(row=1, column=0, sticky="w")
        self._battery_label = ttkb.Label(self, text=f"Batterie : {self._device.battery_level}%", font=label_font)
        self._battery_label.grid(row=2, column=0, sticky="w")
        self._recording_label = ttkb.Label(self, text="", font=label_font)
        self._recording_label.grid(row=4, column=0, sticky="w")
        self._records_label = ttkb.Label(self, text="", font=label_font)
        self._records_label.grid(row=3, column=0, sticky="w")
        self.update_dot()
        self.grid(row=0, column=0)

    def update_dot(self):
        self._image_label.configure({"image": self._device.current_image})
        self._plugged_label.configure({"text": f"En charge : {self._device.is_plugged}"})
        self._battery_label.configure({"text": f"Batterie : {self._device.battery_level}%"})
        if self._device._is_recording:
            recording = "en cours"
        else:
            recording = self._device.recording_count
        self._records_label.configure({"text": f"Enregistrements stockés : {recording}"})
        if self._device._is_recording:
            duration = datetime.now().timestamp() - self._device.timing_record
            display_time = "{:02d}:{:02d}".format(int(duration // 60), int(duration % 60))
            record_message = f"Enregistrement en cours ...\n    {display_time}"
        else:
            record_message = "Pas d'enregistrement en cours"
        self._recording_label.configure({"text": record_message})
