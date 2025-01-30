from datetime import datetime
from tkinter.font import BOLD, Font
import ttkbootstrap as ttkb

from core.utils.DotDevice import DotDevice

class DotFrame(ttkb.Frame):
    def __init__(self, parent, device : DotDevice, **kwargs) -> None:
        super().__init__(parent, **kwargs)
        self.parent = parent
        self.device = device
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=1)
        self.grid_rowconfigure(3, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.imageLabel = ttkb.Label(self, image=self.device.current_image)
        self.imageLabel.grid(row=0, column=0)
        labelFont = Font(self, size=15, weight=BOLD)
        self.pluggedLabel = ttkb.Label(self, text=f"En charge : {self.device.is_plugged}", font=labelFont)
        self.pluggedLabel.grid(row=1, column=0, sticky="w")
        self.batteryLabel = ttkb.Label(self, text=f"Batterie : {self.device.batteryLevel}%", font=labelFont)
        self.batteryLabel.grid(row=2, column=0, sticky="w")
        if self.device._is_recording: 
            recording = "en cours" 
        else: 
            recording = self.device.recording_count
        self.recordsLabel = ttkb.Label(self, text=f"Enregistrements stockés: {recording}", font=labelFont)
        self.recordsLabel.grid(row=3, column=0, sticky="w")
        if self.device._is_recording:
            duration = datetime.now().timestamp() - self.device.timing_record
            displayTime = '{:02d}:{:02d}'.format(int(duration//60), int(duration%60))
            recordMessage = f"Enregistrement en cours ...\n    {displayTime}"
        else:
            recordMessage = "Pas d'enregistrement en cours"
        self.recordingLabel = ttkb.Label(self, text=recordMessage, font=labelFont)
        self.recordingLabel.grid(row=4, column=0, sticky="w")
        self.grid(row=0, column=0)
    
    def updateDot(self):
        self.imageLabel.configure({"image" : self.device.current_image})
        self.pluggedLabel.configure({"text" : f"En charge : {self.device.is_plugged}"})
        self.batteryLabel.configure({"text" : f"Batterie : {self.device.batteryLevel}%"})
        if self.device._is_recording:
            recording = "en cours" 
        else: 
            recording = self.device.recording_count
        self.recordsLabel.configure({"text" : f"Enregistrements stockés : {recording}"})
        if self.device._is_recording:
            duration = datetime.now().timestamp() - self.device.timing_record
            displayTime = '{:02d}:{:02d}'.format(int(duration//60), int(duration%60))
            recordMessage = f"Enregistrement en cours ...\n    {displayTime}"
        else:
            recordMessage = "Pas d'enregistrement en cours"
        self.recordingLabel.configure({"text" : recordMessage})
