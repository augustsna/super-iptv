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


class SyncWorker(QThread):
    # Signals: success status, data dictionary, error/success message
    finished = pyqtSignal(bool, dict, str)

    def __init__(self, config_url="http://107.174.178.52/api/config"):
        super().__init__()
        self.config_url = config_url

    def run(self):
        import urllib.request
        import json
        try:
            logging.info(f"SyncWorker: Fetching config from {self.config_url}")
            req = urllib.request.Request(self.config_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=5) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode('utf-8'))
                    self.finished.emit(True, data, "Sync successful")
                else:
                    self.finished.emit(False, {}, f"Server status code {response.status}")
        except Exception as e:
            logging.error(f"SyncWorker failed: {e}")
            self.finished.emit(False, {}, f"Connection error: {str(e)}")


class AdminAuthWorker(QThread):
    # Signals: success status, config dictionary, message
    finished = pyqtSignal(bool, dict, str)

    def __init__(self, config_url, admin_password):
        super().__init__()
        self.config_url = config_url
        self.admin_password = admin_password

    def run(self):
        import urllib.request
        import urllib.parse
        import json
        try:
            params = urllib.parse.urlencode({"adminPassword": self.admin_password})
            url = f"{self.config_url}?{params}"
            logging.info(f"AdminAuthWorker: Authenticating against {url}")
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=5) as response:
                if response.status == 200:
                    res_data = json.loads(response.read().decode('utf-8'))
                    if res_data.get("authenticated") is True:
                        self.finished.emit(True, res_data.get("config", {}), "Authenticated")
                    else:
                        self.finished.emit(False, {}, "Authentication failed")
                else:
                    self.finished.emit(False, {}, f"Server returned error code {response.status}")
        except urllib.error.HTTPError as e:
            try:
                err_data = json.loads(e.read().decode('utf-8'))
                msg = err_data.get("error", "Incorrect admin password")
            except Exception:
                msg = f"HTTP Error {e.code}"
            self.finished.emit(False, {}, msg)
        except Exception as e:
            self.finished.emit(False, {}, f"Connection error: {str(e)}")


class AdminSaveWorker(QThread):
    # Signals: success status, message
    finished = pyqtSignal(bool, str)

    def __init__(self, config_url, admin_password, xtream_url, username, password):
        super().__init__()
        self.config_url = config_url
        self.admin_password = admin_password
        self.xtream_url = xtream_url
        self.username = username
        self.password = password

    def run(self):
        import urllib.request
        import json
        try:
            payload = {
                "adminPassword": self.admin_password,
                "xtreamUrl": self.xtream_url,
                "username": self.username,
                "password": self.password
            }
            data = json.dumps(payload).encode('utf-8')
            logging.info(f"AdminSaveWorker: Posting config update to {self.config_url}")
            req = urllib.request.Request(
                self.config_url, 
                data=data, 
                headers={
                    'User-Agent': 'Mozilla/5.0',
                    'Content-Type': 'application/json'
                },
                method='POST'
            )
            with urllib.request.urlopen(req, timeout=5) as response:
                if response.status == 200:
                    res_data = json.loads(response.read().decode('utf-8'))
                    if res_data.get("success") is True:
                        self.finished.emit(True, "Configuration saved successfully!")
                    else:
                        self.finished.emit(False, res_data.get("error", "Failed to save configuration"))
                else:
                    self.finished.emit(False, f"Server returned error code {response.status}")
        except urllib.error.HTTPError as e:
            try:
                err_data = json.loads(e.read().decode('utf-8'))
                msg = err_data.get("error", "Save failed")
            except Exception:
                msg = f"HTTP Error {e.code}"
            self.finished.emit(False, msg)
        except Exception as e:
            self.finished.emit(False, f"Connection error: {str(e)}")


