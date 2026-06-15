from PyQt6.QtCore import QThread, pyqtSignal
from xtream_client import XtreamClient
import logging

class LoginWorker(QThread):
    # Signals: success status, message
    finished = pyqtSignal(bool, str)

    def __init__(self, host, username, password):
        super().__init__()
        self.host = host
        self.username = username
        self.password = password
        self.client = None

    def run(self):
        try:
            self.client = XtreamClient(self.host, self.username, self.password)
            success = self.client.authenticate()
            if success:
                self.finished.emit(True, "Authentication successful")
            else:
                self.finished.emit(False, "Invalid username, password, or server error.")
        except Exception as e:
            self.finished.emit(False, f"Connection error: {str(e)}")


class FetchCategoriesWorker(QThread):
    # Signals: list of categories
    finished = pyqtSignal(list)

    def __init__(self, client, mode):
        super().__init__()
        self.client = client
        self.mode = mode  # "live", "vod", or "series"

    def run(self):
        categories = []
        try:
            if self.mode == "live":
                categories = self.client.get_live_categories()
            elif self.mode == "vod":
                categories = self.client.get_vod_categories()
            elif self.mode == "series":
                categories = self.client.get_series_categories()
        except Exception as e:
            logging.error(f"Worker failed to fetch {self.mode} categories: {e}")
        self.finished.emit(categories)


class FetchStreamsWorker(QThread):
    # Signals: list of streams
    finished = pyqtSignal(list)

    def __init__(self, client, mode, category_id=None):
        super().__init__()
        self.client = client
        self.mode = mode  # "live", "vod", or "series"
        self.category_id = category_id

    def run(self):
        streams = []
        try:
            if self.mode == "live":
                streams = self.client.get_live_streams(self.category_id)
            elif self.mode == "vod":
                streams = self.client.get_vod_streams(self.category_id)
            elif self.mode == "series":
                streams = self.client.get_series(self.category_id)
        except Exception as e:
            logging.error(f"Worker failed to fetch {self.mode} streams for cat={self.category_id}: {e}")
        self.finished.emit(streams)


class FetchSeriesInfoWorker(QThread):
    # Signals: series detailed info dictionary
    finished = pyqtSignal(dict)

    def __init__(self, client, series_id):
        super().__init__()
        self.client = client
        self.series_id = series_id

    def run(self):
        info = {}
        try:
            info = self.client.get_series_info(self.series_id)
        except Exception as e:
            logging.error(f"Worker failed to fetch series info for series_id={self.series_id}: {e}")
        self.finished.emit(info)
