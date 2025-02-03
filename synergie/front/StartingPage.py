from math import ceil
import time

from PIL import Image, ImageTk
from tkinter import VERTICAL
from tkinter.font import BOLD, Font
import ttkbootstrap as ttkb

from .img import logo_s2mjump_rgb_png_path
from ..core.utils.DotDevice import DotDevice
from ..core.database.DatabaseManager import DatabaseManager, TrainingData


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
        self._device = device
        self._database_manager = db_manager
        self._device_tag = self._device.device_tag_name

        self._window = ttkb.Toplevel(title="Confirmation", size=(1400,400), topmost=True)
        self._window.place_window_center()
        
        ico = Image.open(logo_s2mjump_rgb_png_path)
        photo = ImageTk.PhotoImage(ico)
        self._window.wm_iconphoto(False, photo)
        self._window.grid_rowconfigure(0, weight=0)
        self._window.grid_rowconfigure(1, weight=1)
        self._window.grid_columnconfigure(0, weight=1, pad=20)
        self._window.grid_columnconfigure(1, weight=0)

        self._label = ttkb.Label(self._window, text=f"Lancer un enregistrement sur le capteur {self._device_tag}", font=Font(self._window, size=20, weight=BOLD))
        self._label.grid(row=0,column=0,columnspan=2, pady=20)

        self._canvas = ttkb.Canvas(self._window)
        self._canvas.grid_rowconfigure(0, weight = 1)
        self._canvas.grid_columnconfigure(0, weight = 1)

        self._frame = ttkb.Frame(self._canvas)
        self._frame.grid_rowconfigure(0, weight = 1)
        self._frame.grid_rowconfigure(1, weight = 1)
        self._frame.grid_columnconfigure(0, weight = 1)
        self._frame.grid_columnconfigure(1, weight = 1)
        self._frame.grid_columnconfigure(2, weight = 1)
        self._frame.grid_columnconfigure(3, weight = 1)
        self._frame.grid_columnconfigure(4, weight = 1)

        skaters = self._database_manager.getAllSkaterFromCoach(userConnected)
        buttonStyle = ttkb.Style()
        buttonStyle.configure("my.TButton", font=Font(self._frame, size=12, weight=BOLD))
        for i,skater in enumerate(skaters):
            button = ttkb.Button(
                self._frame, 
                text=f"\n{skater.skater_name}\n", 
                style="my.TButton", width=ceil((250-24)/11), 
                # TODO using partial?
                command=(lambda x=skater.skater_id, y=skater.skater_name: self._start_record(x, y))
            )
            button.grid(row=i//5+1,column=i%5,padx=10,pady=10)
        
        self._frame.bind("<Enter>", self._bound_to_mousewheel)
        self._frame.bind("<Leave>", self._unbound_to_mousewheel)

        self._frame.grid(row=0, column=0, sticky="nswe")
        
        scroll = ttkb.Scrollbar(self._window, orient=VERTICAL, command=self._canvas.yview)
        scroll.grid(row=1,column=1, sticky="ns")

        self._canvas.configure(yscrollcommand=scroll.set)
        self._canvas.bind(
            "<Configure>", lambda e: self._canvas.configure(scrollregion=self._canvas.bbox("all"))
        )
        self._canvas.create_window((0, 0), window=self._frame, anchor="center")

        self._canvas.grid(row=1,column=0, sticky="nswe", padx=10)

        self._window.grid()

    def _start_record(self, skaterId: str, skaterName: str):
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
        deviceId = self._device.device_id
        new_training = TrainingData(0, skaterId, 0, deviceId, [])
        self._database_manager.set_current_record(deviceId, self._database_manager.save_training_data(new_training))
        recordStarted = self._device.start_recording()
        self._canvas.destroy()
        self._label.destroy()
        self._frame = ttkb.Frame(self._window)
        if recordStarted :
            message = f"Enregistrement commencé sur le capteur {self._device_tag} pour {skaterName}"
        else : 
            message = "Erreur durant le lancement, impossible de lancer l'enregistrement"
        label = ttkb.Label(self._frame, text=message, font=Font(self._window, size=20, weight=BOLD))
        label.grid()
        self._frame.grid(row=1,column=0)
        self._window.update()
        time.sleep(1)
        self._canvas.destroy()
        self._window.destroy()
    
    def _bound_to_mousewheel(self, event):
        """
        Bind the mousewheel scrolling event to the canvas when the mouse is over the frame.

        By binding <MouseWheel> events to the entire application (via bind_all),
        the user can scroll the list of skaters by hovering the mouse over the frame.
        """
        self._canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def _unbound_to_mousewheel(self, event):
        """
        Unbind the mousewheel scrolling event when the mouse leaves the frame.

        Once the mouse leaves the frame, the user should not be able to scroll
        by using the mousewheel, avoiding unwanted scrolling behavior.
        """
        self._canvas.unbind_all("<MouseWheel>")

    def _on_mousewheel(self, event):
        """
        Handle mousewheel scrolling within the canvas.

        This method translates mousewheel events into vertical scrolling of the canvas.
        The "event.delta" value gives the scroll direction and magnitude.
        Using "yview_scroll" we move the view by a certain number of "units".

        Args:
            event: The tkinter mousewheel event containing the scroll direction and magnitude.
        """
        self._canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
