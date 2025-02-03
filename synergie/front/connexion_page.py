import logging

from tkinter.font import BOLD, Font
import ttkbootstrap as ttkb

from ..core.database.database_manager import DatabaseManager

_logger = logging.getLogger(__name__)


class ConnexionPage:
    """
    The ConnectionPage class represents a login interface where the user enters their email address
    to connect. This page checks if the user is a coach and, if so, allows them to access the rest
    of the application.
    """

    def __init__(self, root: ttkb.Window, database_manager: DatabaseManager) -> None:
        self._database_manager = database_manager
        self._user_id: str = None

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
        self._label = ttkb.Label(self._frame, text="Veuillez entrer votre adresse mail", font=label_font)
        self._label.grid(row=0, column=0, sticky="s")

        # Entry field for user email input.
        self._account_var = ttkb.StringVar(self._frame, value="")
        self._entry = ttkb.Entry(self._frame, textvariable=self._account_var)
        self._entry.grid(row=1, column=0)

        # Style configuration for the "Se connecter" (Connect) button.
        button_style = ttkb.Style()
        button_style.configure("home.TButton", font=Font(self._frame, size=20, weight=BOLD))

        # Button to trigger the login/verification process.
        self._button = ttkb.Button(
            self._frame,
            text="Se connecter",
            style="home.TButton",
            command=self._register,
        )
        self._button.grid(row=2, column=0, sticky="n")

        # Label to show error messages
        self._error_var = ttkb.StringVar(self._frame, value="")
        self._error_label = ttkb.Label(self._frame, textvariable=self._error_var, font=label_font)
        self._error_label.grid(row=3, column=0)

        # Place the frame in the main window.
        self._frame.grid(sticky="nswe")

    def destroy(self):
        self._frame.destroy()

    @property
    def user_id(self):
        return self._user_id

    def _register(self):
        """
        Attempt to find and authenticate the user by their email.
        Checks internet connectivity before proceeding.
        """
        self._button.config(state="disabled")

        user_email = self._account_var.get().strip()
        if not user_email:
            _logger.warning("Empty email entered.")
            self._error_var.set("Veuillez entrer une adresse email valide.")
            self._button.config(state="normal")
            return

        _logger.info(f"Attempting to find user with email: {user_email}")
        user = self._database_manager.findUserByEmail(user_email)
        if not user:
            _logger.warning(f"User with email {user_email} not found.")
            self._error_var.set("Erreur : cet utilisateur n'existe pas")
            self._button.config(state="normal")
            return

        x = user[0]
        if x.get("role") != "COACH":
            _logger.warning(f"User {user_email} is not a coach.")
            self._error_var.set("Erreur : vous avez besoin d'un compte entraîneur")
            self._button.config(state="normal")
            return

        _logger.info(f"User {user_email} connected.")
        self._user_id = x.id
