import requests
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class XtreamClient:
    def __init__(self, host, username, password):
        # Normalize host URL
        host = host.strip()
        if not host.startswith("http://") and not host.startswith("https://"):
            host = "http://" + host
        self.host = host.rstrip("/")
        
        self.username = username.strip()
        self.password = password.strip()
        
        self.session = requests.Session()
        self.user_info = {}
        self.server_info = {}
        
    def _get_api_url(self, action=None, extra_params=None):
        url = f"{self.host}/player_api.php?username={self.username}&password={self.password}"
        if action:
            url += f"&action={action}"
        if extra_params:
            for k, v in extra_params.items():
                if v is not None:
                    url += f"&{k}={v}"
        return url

    def authenticate(self):
        """Validates credentials. Returns True if successful, False otherwise."""
        url = self._get_api_url()
        try:
            logging.info(f"Authenticating with {self.host}")
            # Use short timeout to avoid UI freeze if server is down
            response = self.session.get(url, timeout=5)
            response.raise_for_status()
            data = response.json()
            
            # Xtream Codes returns a JSON dict with user_info and server_info if valid
            # In case of invalid, user_info might contain status "Expired" or user auth failed
            if "user_info" in data and data["user_info"].get("auth", 1) != 0:
                user_status = data["user_info"].get("status", "Active")
                if user_status.lower() == "active":
                    self.user_info = data["user_info"]
                    self.server_info = data.get("server_info", {})
                    logging.info(f"Authentication successful for user: {self.username}")
                    return True
                else:
                    logging.warning(f"Authentication failed: User account status is {user_status}")
                    return False
            else:
                logging.warning("Authentication failed: Invalid credentials or server error.")
                return False
        except Exception as e:
            logging.error(f"Authentication request failed: {e}")
            return False

    def get_live_categories(self):
        """Fetches Live TV categories."""
        url = self._get_api_url("get_live_categories")
        try:
            res = self.session.get(url, timeout=10)
            res.raise_for_status()
            return res.json()
        except Exception as e:
            logging.error(f"Failed to fetch live categories: {e}")
            return []

    def get_live_streams(self, category_id=None):
        """Fetches Live TV stream lists, optionally filtered by category_id."""
        params = {"category_id": category_id} if category_id else None
        url = self._get_api_url("get_live_streams", params)
        try:
            res = self.session.get(url, timeout=15)
            res.raise_for_status()
            return res.json()
        except Exception as e:
            logging.error(f"Failed to fetch live streams: {e}")
            return []

    def get_vod_categories(self):
        """Fetches Movie (VOD) categories."""
        url = self._get_api_url("get_vod_categories")
        try:
            res = self.session.get(url, timeout=10)
            res.raise_for_status()
            return res.json()
        except Exception as e:
            logging.error(f"Failed to fetch VOD categories: {e}")
            return []

    def get_vod_streams(self, category_id=None):
        """Fetches Movie (VOD) lists, optionally filtered by category_id."""
        params = {"category_id": category_id} if category_id else None
        url = self._get_api_url("get_vod_streams", params)
        try:
            res = self.session.get(url, timeout=15)
            res.raise_for_status()
            return res.json()
        except Exception as e:
            logging.error(f"Failed to fetch VOD streams: {e}")
            return []

    def get_series_categories(self):
        """Fetches Series categories."""
        url = self._get_api_url("get_series_categories")
        try:
            res = self.session.get(url, timeout=10)
            res.raise_for_status()
            return res.json()
        except Exception as e:
            logging.error(f"Failed to fetch series categories: {e}")
            return []

    def get_series(self, category_id=None):
        """Fetches Series lists, optionally filtered by category_id."""
        params = {"category_id": category_id} if category_id else None
        url = self._get_api_url("get_series", params)
        try:
            res = self.session.get(url, timeout=15)
            res.raise_for_status()
            return res.json()
        except Exception as e:
            logging.error(f"Failed to fetch series: {e}")
            return []

    def get_series_info(self, series_id):
        """Fetches seasons and episodes list for a specific series."""
        params = {"series_id": series_id}
        url = self._get_api_url("get_series_info", params)
        try:
            res = self.session.get(url, timeout=10)
            res.raise_for_status()
            return res.json()
        except Exception as e:
            logging.error(f"Failed to fetch series info for {series_id}: {e}")
            return {}

    def get_live_stream_url(self, stream_id, format="ts"):
        """Generates stream URL for Live TV channels."""
        return f"{self.host}/live/{self.username}/{self.password}/{stream_id}.{format}"

    def get_vod_stream_url(self, stream_id, container_extension="mp4"):
        """Generates stream URL for Movie streams."""
        ext = container_extension if container_extension else "mp4"
        return f"{self.host}/movie/{self.username}/{self.password}/{stream_id}.{ext}"

    def get_series_stream_url(self, stream_id, container_extension="mp4"):
        """Generates stream URL for Series Episode streams."""
        ext = container_extension if container_extension else "mp4"
        return f"{self.host}/series/{self.username}/{self.password}/{stream_id}.{ext}"
