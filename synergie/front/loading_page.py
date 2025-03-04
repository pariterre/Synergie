from tkinter.font import BOLD, Font
import ttkbootstrap as ttkb

from ..core.database.database_manager import DatabaseManager


class LoadingPage:
    """
    The ConnectionPage class represents a login interface where the user enters their email address
    to connect. This page checks if the user is a coach and, if so, allows them to access the rest
    of the application.
    """

    def __init__(self, root: ttkb.Window) -> None:
        # Configure the main window grid
        self._root = root
        self._root.grid_rowconfigure(0, weight=1)
        self._root.grid_columnconfigure(0, weight=1)

        # Create a frame to hold all ConnexionPage widgets.
        self._frame = ttkb.Frame(self._root)
        self._frame.grid_rowconfigure(0, weight=1)
        self._frame.grid_rowconfigure(1, weight=1)
        self._frame.grid_rowconfigure(2, weight=1)
        self._frame.grid_rowconfigure(3, weight=1)
        self._frame.grid_columnconfigure(0, weight=1)

        # A bold font for labels.
        label_font = Font(self._root, size=15, weight=BOLD)
        self._label = ttkb.Label(
            self._frame,
            text="Initialisation de l'application (ceci peut prendre plusieurs minutes)...",
            font=label_font,
        )
        self._label.grid(row=0, column=0, sticky="s")

        # Place the frame in the main window.
        self._frame.grid(sticky="nswe")

        # Force the window to update
        self._root.update()

    def destroy(self):
        self._frame.destroy()
