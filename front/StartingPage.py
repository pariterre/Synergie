import time
import sys
from tkinter import VERTICAL
from PIL import Image, ImageTk
from tkinter.font import BOLD, Font
from math import ceil
import ttkbootstrap as ttkb

from core.utils.DotDevice import DotDevice
from core.database.DatabaseManager import DatabaseManager, TrainingData

class StartingPage:
    """
    A class that creates a tkinter Toplevel window used for confirming and starting
    a training data recording session for a given device and a selected skater.

    This class provides a user interface that displays all the skaters associated
    with a particular coach. The coach can then select a skater and start recording
    training data for that skater on the specified device.
    """

    def __init__(self, device: DotDevice, db_manager: DatabaseManager, userConnected: str) -> None:
        """
        Initialize the StartingPage window.

        Args:
            device (DotDevice): The device instance for which the recording will be initiated.
            db_manager (DatabaseManager): The database manager instance for retrieving skaters
                                          and handling training data operations.
            userConnected (str): The username or identifier of the connected coach.

        The constructor sets up the Toplevel window, applies a logo icon (if available),
        and creates a scrollable interface listing all skaters. Each skater is represented
        by a button which, when clicked, triggers the start of a recording.
        """
        self.device = device
        self.db_manager = db_manager
        self.device_tag = self.device.device_tag_name
        self.skaters = self.db_manager.getAllSkaterFromCoach(userConnected)

        self.window = ttkb.Toplevel(title="Confirmation", size=(1400,400), topmost=True)
        self.window.place_window_center()
        try:
            ico = Image.open(f'{sys._MEIPASS}/img/Logo_s2mJUMP_RGB.png')
        except:
            ico = Image.open(f'img/Logo_s2mJUMP_RGB.png')
        photo = ImageTk.PhotoImage(ico)
        self.window.wm_iconphoto(False, photo)
        self.window.grid_rowconfigure(0, weight=0)
        self.window.grid_rowconfigure(1, weight=1)
        self.window.grid_columnconfigure(0, weight=1, pad=20)
        self.window.grid_columnconfigure(1, weight=0)

        self.label = ttkb.Label(self.window, text=f"Lancer un enregistrement sur le capteur {self.device_tag}", font=Font(self.window, size=20, weight=BOLD))
        self.label.grid(row=0,column=0,columnspan=2, pady=20)

        self.canvas = ttkb.Canvas(self.window)
        self.canvas.grid_rowconfigure(0, weight = 1)
        self.canvas.grid_columnconfigure(0, weight = 1)

        self.frame = ttkb.Frame(self.canvas)
        self.frame.grid_rowconfigure(0, weight = 1)
        self.frame.grid_rowconfigure(1, weight = 1)
        self.frame.grid_columnconfigure(0, weight = 1)
        self.frame.grid_columnconfigure(1, weight = 1)
        self.frame.grid_columnconfigure(2, weight = 1)
        self.frame.grid_columnconfigure(3, weight = 1)
        self.frame.grid_columnconfigure(4, weight = 1)

        buttonStyle = ttkb.Style()
        buttonStyle.configure('my.TButton', font=Font(self.frame, size=12, weight=BOLD))
        for i,skater in enumerate(self.skaters):
            button = ttkb.Button(self.frame, text=f"\n{skater.skater_name}\n", style="my.TButton", width=ceil((250-24)/11), command=(lambda x=skater.skater_id,y=skater.skater_name: self.startRecord(x,y)))
            button.grid(row=i//5+1,column=i%5,padx=10,pady=10)
        
        self.frame.bind('<Enter>', self._bound_to_mousewheel)
        self.frame.bind('<Leave>', self._unbound_to_mousewheel)

        self.frame.grid(row=0, column=0, sticky="nswe")
        
        scroll = ttkb.Scrollbar(self.window, orient=VERTICAL, command=self.canvas.yview)
        scroll.grid(row=1,column=1, sticky="ns")

        self.canvas.configure(yscrollcommand=scroll.set)
        self.canvas.bind(
            '<Configure>', lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        self.canvas.create_window((0, 0), window=self.frame, anchor="center")

        self.canvas.grid(row=1,column=0, sticky="nswe", padx=10)

        self.window.grid()

    def startRecord(self, skaterId: str, skaterName: str):
        """
        Start the recording process for a selected skater on the given device.

        This method:
        - Creates a new training data record in the database linked to the current device and skater.
        - Initiates the actual recording process on the device.
        - Updates the UI to provide feedback (e.g., success or error message).
        - Closes the confirmation window after a brief pause.

        Args:
            skaterId (str): The unique identifier of the selected skater.
            skaterName (str): The name of the selected skater.
        """
        deviceId = self.device.device_id
        new_training = TrainingData(0, skaterId, 0, deviceId, [])
        self.db_manager.set_current_record(deviceId, self.db_manager.save_training_data(new_training))
        recordStarted = self.device.start_recording()
        self.canvas.destroy()
        self.label.destroy()
        self.frame = ttkb.Frame(self.window)
        if recordStarted :
            message = f"Enregistrement commencé sur le capteur {self.device_tag} pour {skaterName}"
        else : 
            message = "Erreur durant le lancement, impossible de lancer l'enregistrement"
        label = ttkb.Label(self.frame, text=message, font=Font(self.window, size=20, weight=BOLD))
        label.grid()
        self.frame.grid(row=1,column=0)
        self.window.update()
        time.sleep(1)
        self.canvas.destroy()
        self.window.destroy()
    
    def _bound_to_mousewheel(self, event):
        """
        Bind the mousewheel scrolling event to the canvas when the mouse is over the frame.

        By binding <MouseWheel> events to the entire application (via bind_all),
        the user can scroll the list of skaters by hovering the mouse over the frame.
        """
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def _unbound_to_mousewheel(self, event):
        """
        Unbind the mousewheel scrolling event when the mouse leaves the frame.

        Once the mouse leaves the frame, the user should not be able to scroll
        by using the mousewheel, avoiding unwanted scrolling behavior.
        """
        self.canvas.unbind_all("<MouseWheel>")

    def _on_mousewheel(self, event):
        """
        Handle mousewheel scrolling within the canvas.

        This method translates mousewheel events into vertical scrolling of the canvas.
        The 'event.delta' value gives the scroll direction and magnitude.
        Using 'yview_scroll' we move the view by a certain number of "units".

        Args:
            event: The tkinter mousewheel event containing the scroll direction and magnitude.
        """
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
