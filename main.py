import logging

from synergie import App


# Entry point of the application.
if __name__ == "__main__":
    # Set up the logging configuration.
    logging.basicConfig(level=logging.INFO)

    # Create an instance of the App class with the root window.
    myapp = App()

    # Start the main event loop.
    myapp.run()
