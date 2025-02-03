import threading
import time

from PIL import Image, ImageTk
from tkinter.font import BOLD, Font
import ttkbootstrap as ttkb

from .img import logo_s2mjump_rgb_png_path
from ..core.database.DatabaseManager import DatabaseManager
from ..core.utils.DotDevice import DotDevice

class StopingPage:
    def __init__(self, device : DotDevice, db_manager : DatabaseManager) -> None:
        self._device = device
        self._database_manager = db_manager
        self._device_tag = self._device.device_tag_name
        self._window = ttkb.Toplevel(title="Confirmation", size=(1000,400), topmost=True)
        self._window.place_window_center()
        
        ico = Image.open(logo_s2mjump_rgb_png_path)
        photo = ImageTk.PhotoImage(ico)
        self._window.wm_iconphoto(False, photo)
        self._window.grid_rowconfigure(0, weight = 1)
        self._window.grid_columnconfigure(0, weight = 1)
        self._frame = ttkb.Frame(self._window)
        self._frame.grid_rowconfigure(0, weight = 0)
        self._frame.grid_rowconfigure(1, weight = 1)
        self._frame.grid_rowconfigure(2, weight = 1)
        self._frame.grid_columnconfigure(0, weight = 1)
        label = ttkb.Label(self._frame, text=f"Arrêtez l'enregistrement du capteur {self._device_tag}", font=Font(self._window, size=20, weight=BOLD))
        label.grid(row=0,column=0,pady=20)
        buttonStyle = ttkb.Style()
        buttonStyle.configure("my.TButton", font=Font(self._frame, size=12, weight=BOLD))
        ttkb.Button(self._frame, text="Arrêt", style="my.TButton", command=self.stopRecord).grid(row=1,column=0,sticky="nsew",pady=20)
        self.estimatedTime = self._device.get_export_estimated_time()
        ttkb.Button(self._frame, text=f"Arrêt et extraction des données \n Temps estimé : {round(self.estimatedTime,0)} min", style="my.TButton", command=self.stopRecordAndExtract).grid(row=2,column=0,sticky="nsew")
        self._save_data_to_file = ttkb.Checkbutton(self._frame, text="Sauvegarder plus de données (pour la recherche)")
        self._save_data_to_file.state(["!alternate"])
        self._save_data_to_file.grid(row=3,column=0,sticky="nsew")
        self._frame.grid(sticky ="nswe")
        self._window.grid()

    def stopRecord(self):
        recordStopped = self._device.stop_recording()
        self._frame.destroy()
        self._frame = ttkb.Frame(self._window)
        if recordStopped :
            message = f"Enregistrement stoppé sur le capteur {self._device_tag}"
        else : 
            message = "Erreur durant l'arrêt, impossible d'arrêter l'enregistrement"
        label = ttkb.Label(self._frame, text=message, font=Font(self._window, size=20, weight=BOLD))
        label.grid()
        self._frame.grid()
        self._window.update()
        time.sleep(1)
        self._window.destroy()
    
    def stopRecordAndExtract(self):
        recordStopped = self._device.stop_recording()
        _save_data_to_file = self._save_data_to_file.instate(["selected"])
        self._frame.destroy()
        self._frame = ttkb.Frame(self._window)
        self._frame.grid_columnconfigure(0, weight=1)
        self._frame.grid_rowconfigure(0, weight=1)
        self._frame.grid_rowconfigure(1, weight=1)
        if recordStopped :
            message = f"Enregistrement stoppé sur le capteur {self._device_tag}"
        else : 
            message = "Erreur durant l'arrêt, impossible d'arrêter l'enregistrement"
        self.text = ttkb.StringVar(self._frame, value = message)
        self.label = ttkb.Label(self._frame, textvariable=self.text, font=Font(self._window, size=20, weight=BOLD))
        self.label.grid(row=0,column=0, pady=50)
        self._frame.grid()
        self._window.update()
        time.sleep(1)
        self.text.set(f"Extraction des données du capteur {self._device_tag} \nNe pas deconnecter ce capteur")
        self.label.update()
        self.max_val = 60*self.estimatedTime
        self.progressExtract = ttkb.Progressbar(self._frame, value=0, maximum=self.max_val, style="success.Striped.Horizontal.TProgressbar", mode="determinate")
        self.progressExtract.start(1000)
        self.progressExtract.grid(row=1, column=0, sticky="we")
        self._frame.grid()
        self._window.update()
        self.extractEvent = threading.Event()
        self.checkFinish()
        if recordStopped :
            threading.Thread(target=self._device.export_data, args=([_save_data_to_file, self.extractEvent]),daemon=True).start()
        else:
            self.extractEvent.set()

    def checkFinish(self):
        try:
            self.checkProgressBar()
        except:
            pass
        self._window.update()
        if self.extractEvent.is_set():
            self.text.set("Extraction finie")
            self.label.update()
            time.sleep(1)
            self._window.destroy()
        self._window.after(1000, self.checkFinish)
    
    def checkProgressBar(self):
        if self.progressExtract["value"] >= self.max_val-1: 
            self.progressExtract.stop()
            self.progressExtract["value"] = self.max_val