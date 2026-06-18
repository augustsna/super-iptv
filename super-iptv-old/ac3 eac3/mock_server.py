import http.server
import socketserver
import json
import urllib.parse
import threading
import os
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

PORT = 8081
_server_instance = None
_server_thread = None

class XtreamMockHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Override to suppress standard HTTP logging to console unless needed
        pass

    def do_GET(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        query = urllib.parse.parse_qs(parsed_url.query)
        
        # Check if we are fetching a stream
        # Formats:
        # Live: /live/<username>/<password>/<stream_id>.ts
        # Movie: /movie/<username>/<password>/<stream_id>.<ext>
        # Series: /series/<username>/<password>/<stream_id>.<ext>
        parts = path.strip("/").split("/")
        if len(parts) >= 4 and parts[0] in ("live", "movie", "series"):
            stream_id = parts[3].split(".")[0]
            logging.info(f"Mock Server: Streaming request received for stream_id={stream_id} (path={path})")
            self.serve_test_file()
            return

        # Check for player_api.php
        if path == "/player_api.php":
            action = query.get("action", [None])[0]
            self.handle_api_action(action, query)
            return
            
        # Fallback 404
        self.send_response(404)
        self.end_headers()
        self.wfile.write(b"404 Not Found")

    def serve_test_file(self):
        # Locate the generated test video file
        video_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "test_ac3_eac3.mp4"))
        if not os.path.exists(video_path):
            # Fallback in case it's in working directory
            video_path = "test_ac3_eac3.mp4"
            
        if not os.path.exists(video_path):
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Error: test_ac3_eac3.mp4 not found. Run media_generator.py first.")
            logging.error("Mock Server: Requested test video file not found!")
            return

        file_size = os.path.getsize(video_path)
        
        # Simple Range support or standard download
        self.send_response(200)
        self.send_header("Content-Type", "video/mp4")
        self.send_header("Content-Length", str(file_size))
        self.send_header("Accept-Ranges", "bytes")
        self.end_headers()
        
        try:
            with open(video_path, "rb") as f:
                self.wfile.write(f.read())
        except Exception as e:
            logging.error(f"Mock Server: Error writing media data: {e}")

    def handle_api_action(self, action, query):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()

        # Action handlers
        if not action:
            # Authentication / Login check
            response = {
                "user_info": {
                    "username": query.get("username", ["test_user"])[0],
                    "status": "Active",
                    "expiry_date": "1893456000",  # Far future (2030)
                    "is_trial": "0",
                    "active_cons": "0",
                    "max_connections": "2",
                    "allowed_formats": ["ts", "mkv", "mp4"]
                },
                "server_info": {
                    "url": "127.0.0.1",
                    "port": str(PORT),
                    "server_protocol": "http"
                }
            }
        elif action == "get_live_categories":
            response = [
                {"category_id": "1", "category_name": "News & Entertainment", "parent_id": 0},
                {"category_id": "2", "category_name": "Dolby Audio Showcase", "parent_id": 0}
            ]
        elif action == "get_live_streams":
            cat_id = query.get("category_id", [None])[0]
            all_streams = [
                {
                    "num": 1,
                    "name": "Live Channel 1 (AAC Audio)",
                    "stream_id": 101,
                    "stream_icon": "https://img.icons8.com/color/96/television.png",
                    "epg_channel_id": "",
                    "added": "1600000000",
                    "category_id": "1",
                    "custom_sid": "",
                    "tv_archive": 0,
                    "direct_source": "",
                    "tv_archive_duration": 0
                },
                {
                    "num": 2,
                    "name": "Live Channel 2 (Dolby AC3/EAC3 Showcase)",
                    "stream_id": 102,
                    "stream_icon": "https://img.icons8.com/color/96/dolby.png",
                    "epg_channel_id": "",
                    "added": "1600000000",
                    "category_id": "2",
                    "custom_sid": "",
                    "tv_archive": 0,
                    "direct_source": "",
                    "tv_archive_duration": 0
                }
            ]
            if cat_id:
                response = [s for s in all_streams if s["category_id"] == cat_id]
            else:
                response = all_streams

        elif action == "get_vod_categories":
            response = [
                {"category_id": "10", "category_name": "Action Movies", "parent_id": 0},
                {"category_id": "11", "category_name": "Dolby Test Blockbusters", "parent_id": 0}
            ]
        elif action == "get_vod_streams":
            cat_id = query.get("category_id", [None])[0]
            all_streams = [
                {
                    "num": 1,
                    "name": "Generic Movie 1 (AAC Audio)",
                    "stream_id": 201,
                    "stream_icon": "",
                    "added": "1600000000",
                    "category_id": "10",
                    "container_extension": "mp4",
                    "custom_sid": "",
                    "direct_source": "",
                    "rating": "7.2"
                },
                {
                    "num": 2,
                    "name": "Dolby AC3/EAC3 Multi-Track Movie",
                    "stream_id": 202,
                    "stream_icon": "",
                    "added": "1600000000",
                    "category_id": "11",
                    "container_extension": "mp4",
                    "custom_sid": "",
                    "direct_source": "",
                    "rating": "9.8"
                }
            ]
            if cat_id:
                response = [s for s in all_streams if s["category_id"] == cat_id]
            else:
                response = all_streams

        elif action == "get_series_categories":
            response = [
                {"category_id": "20", "category_name": "Mini-Series Showcase", "parent_id": 0}
            ]
        elif action == "get_series":
            cat_id = query.get("category_id", [None])[0]
            all_series = [
                {
                    "num": 1,
                    "name": "Dolby Multi-Audio Series",
                    "series_id": 301,
                    "cover": "",
                    "plot": "A test series containing multi-audio AC3 and EAC3 streams in each episode.",
                    "cast": "FFmpeg Sine Wave Generator",
                    "director": "VLC LibVlc Renderer",
                    "genre": "Tech Demo",
                    "releaseDate": "2026",
                    "last_modified": "1600000000",
                    "rating": "9.5",
                    "rating_5element": 4.8,
                    "category_id": "20"
                }
            ]
            if cat_id:
                response = [s for s in all_series if s["category_id"] == cat_id]
            else:
                response = all_series

        elif action == "get_series_info":
            series_id = query.get("series_id", [None])[0]
            response = {
                "seasons": [
                    {"air_date": "2026-01-01", "episode_count": 2, "id": 1, "name": "Season 1", "overview": "The testing season.", "season_number": 1}
                ],
                "info": {
                    "name": "Dolby Multi-Audio Series",
                    "cover": "",
                    "plot": "A test series containing multi-audio AC3 and EAC3 streams in each episode."
                },
                "episodes": {
                    "1": [
                        {
                            "id": "401",
                            "episode_num": 1,
                            "title": "Episode 1: Dolby AC3 & EAC3 Dual Track",
                            "container_extension": "mp4",
                            "info": {},
                            "season": 1
                        },
                        {
                            "id": "402",
                            "episode_num": 2,
                            "title": "Episode 2: Audio Switching Testbed",
                            "container_extension": "mp4",
                            "info": {},
                            "season": 1
                        }
                    ]
                }
            }
        else:
            response = {"error": f"Action '{action}' not supported by mock server"}

        self.wfile.write(json.dumps(response).encode("utf-8"))

def start_server(port=PORT):
    global _server_instance, _server_thread, PORT
    if _server_instance is not None:
        logging.info("Mock Server: Already running.")
        return
    
    PORT = port
    class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
        allow_reuse_address = True

    try:
        _server_instance = ThreadedTCPServer(("127.0.0.1", PORT), XtreamMockHandler)
        _server_thread = threading.Thread(target=_server_instance.serve_forever)
        _server_thread.daemon = True
        _server_thread.start()
        logging.info(f"Mock Server: Started successfully on http://127.0.0.1:{PORT}")
    except Exception as e:
        logging.error(f"Mock Server: Failed to start server: {e}")
        _server_instance = None
        _server_thread = None

def stop_server():
    global _server_instance, _server_thread
    if _server_instance is not None:
        logging.info("Mock Server: Stopping...")
        _server_instance.shutdown()
        _server_instance.server_close()
        _server_instance = None
        _server_thread = None
        logging.info("Mock Server: Stopped.")

if __name__ == "__main__":
    start_server()
    print(f"Mock Xtream Server is running on port {PORT}. Press Ctrl+C to stop.")
    try:
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        stop_server()
