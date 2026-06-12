import sys
import json
import socket
from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEngineProfile, QWebEnginePage

# Try importing python-vlc. We will provide helpful diagnostics if it fails.
try:
    import vlc
except ImportError:
    print("Error: python-vlc is not installed. Please run: pip install python-vlc")
    sys.exit(1)

class VLCPlayerWidget(QtWidgets.QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background-color: black;")
        
        # VLC Player initialization
        # Load VLC Instance with options (e.g. no-video-title-show to prevent annoying text overlay)
        self.instance = vlc.Instance("--no-video-title-show")
        self.player = self.instance.media_player_new()
        
        # Set the window handle for video output based on OS
        if sys.platform == "win32":
            self.player.set_hwnd(self.winId())
        elif sys.platform == "darwin":
            self.player.set_nsobject(self.winId())
        else:
            self.player.set_xwindow(self.winId())
            
    def play_url(self, url):
        print(f"VLC playing: {url}")
        media = self.instance.media_new(url)
        self.player.set_media(media)
        self.player.play()
        
    def stop(self):
        print("VLC stopping")
        self.player.stop()
        
    def set_volume(self, vol_percent):
        vol = int(vol_percent * 100)
        print(f"VLC setting volume: {vol}%")
        self.player.audio_set_volume(vol)
        
    def set_mute(self, is_muted):
        print(f"VLC setting mute: {is_muted}")
        self.player.audio_set_mute(is_muted)
        
    def get_stream_stats(self):
        if not self.player.is_playing():
            return None
            
        media = self.player.get_media()
        if not media:
            return None
            
        width = self.player.video_get_width()
        height = self.player.video_get_height()
        fps = self.player.video_get_fps()
        
        # Determine resolution label
        res_label = ""
        if height > 0:
            if height >= 2160: res_label = "4K"
            elif height >= 1080: res_label = "1080p"
            elif height >= 720: res_label = "720p"
            elif height >= 480: res_label = "480p"
            else: res_label = f"{height}p"
            
        video_codec = ""
        audio_codec = ""
        audio_channels = ""
        
        # Parse track info to get audio/video codecs
        try:
            tracks = media.tracks_get()
            if tracks:
                for i in range(tracks.count):
                    track = tracks[i]
                    if track.type == vlc.TrackType.video:
                        codec_fourcc = track.codec
                        fourcc_chars = []
                        for j in range(4):
                            b = (codec_fourcc >> (8 * j)) & 0xFF
                            if 32 <= b <= 126:
                                fourcc_chars.append(chr(b))
                        fourcc_str = "".join(fourcc_chars).strip().lower()
                        if "h264" in fourcc_str or "avc" in fourcc_str:
                            video_codec = "H264"
                        elif "h265" in fourcc_str or "hevc" in fourcc_str:
                            video_codec = "HEVC"
                        else:
                            video_codec = fourcc_str.upper()
                    elif track.type == vlc.TrackType.audio:
                        codec_fourcc = track.codec
                        fourcc_chars = []
                        for j in range(4):
                            b = (codec_fourcc >> (8 * j)) & 0xFF
                            if 32 <= b <= 126:
                                fourcc_chars.append(chr(b))
                        fourcc_str = "".join(fourcc_chars).strip().lower()
                        if "aac" in fourcc_str:
                            audio_codec = "AAC"
                        elif "ac3" in fourcc_str or "ac-3" in fourcc_str:
                            audio_codec = "AC3"
                        elif "eac3" in fourcc_str or "ec-3" in fourcc_str:
                            audio_codec = "EAC3"
                        elif "mp3" in fourcc_str:
                            audio_codec = "MP3"
                        else:
                            audio_codec = fourcc_str.upper()
                            
                        # Audio channels
                        channels = track.u.audio.channels
                        if channels == 6:
                            audio_channels = "5.1"
                        elif channels > 0:
                            audio_channels = f"{channels}.0"
        except Exception as e:
            # Fallback if tracks_get is not supported
            pass
            
        stats = {}
        if res_label: stats["resolution"] = res_label
        if fps > 0: stats["fps"] = f"{int(fps)} fps"
        if video_codec: stats["videoCodec"] = video_codec
        if audio_codec: stats["audioCodec"] = audio_codec
        if audio_channels: stats["audioChannels"] = audio_channels
        stats["format"] = "VLC Native"
        
        return stats

class CustomWebPage(QWebEnginePage):
    def __init__(self, profile, parent=None, console_callback=None):
        super().__init__(profile, parent)
        self.console_callback = console_callback
        
    def javaScriptConsoleMessage(self, level, message, line_number, source_id):
        if self.console_callback:
            self.console_callback(message)
        # Pass through to stdout
        sys.stdout.write(f"JS: {message}\n")
        sys.stdout.flush()

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, app_url):
        super().__init__()
        self.setWindowTitle("Super Stream Player")
        self.resize(1280, 720)
        
        # Central layout
        self.central_widget = QtWidgets.QWidget(self)
        self.setCentralWidget(self.central_widget)
        
        # Create VLC widget first (so it sits behind web_view in paint order if needed, 
        # but since we position absolutely and keep web_view transparent, paint order is key).
        # In Qt, child widgets are painted in the order they are created. 
        # First created widget is painted first (at the back). 
        # QWebEngineView created second will sit on top of the VLC widget!
        self.vlc_widget = VLCPlayerWidget(self.central_widget)
        self.vlc_widget.setGeometry(0, 0, 0, 0)
        self.vlc_widget.hide()
        
        # Create QWebEngineView
        self.web_view = QWebEngineView(self.central_widget)
        
        # Make the webview transparent so the VLC video underneath can shine through
        self.web_view.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        self.web_view.setStyleSheet("background: transparent;")
        self.web_view.page().setBackgroundColor(QtCore.Qt.transparent)
        
        # Set User Agent to let the web app detect it's running inside the Windows app
        profile = QWebEngineProfile.defaultProfile()
        profile.setHttpUserAgent(profile.httpUserAgent() + " SuperStreamWindowsApp")
        
        # Use our CustomWebPage to intercept console messages
        self.web_page = CustomWebPage(profile, self, console_callback=self.handle_console_message)
        self.web_view.setPage(self.web_page)
        
        # Load the URL
        self.web_view.load(QtCore.QUrl(app_url))
        
        # Timer for polling VLC player statistics
        self.stats_timer = QtCore.QTimer(self)
        self.stats_timer.timeout.connect(self.poll_vlc_stats)
        
    def resizeEvent(self, event):
        # Always expand webview to fill the entire window
        self.web_view.setGeometry(0, 0, self.central_widget.width(), self.central_widget.height())
        super().resizeEvent(event)
        
    def handle_console_message(self, message):
        if message.startswith("APP_BRIDGE_PLAY:"):
            try:
                data_str = message[len("APP_BRIDGE_PLAY:"):]
                data = json.loads(data_str)
                url = data.get("url")
                self.vlc_widget.play_url(url)
                self.stats_timer.start(1000) # Poll stats every 1 second
            except Exception as e:
                print("Error playing stream:", e)
                
        elif message == "APP_BRIDGE_STOP":
            self.vlc_widget.stop()
            self.vlc_widget.hide()
            self.stats_timer.stop()
            
        elif message.startswith("APP_BRIDGE_VOLUME:"):
            try:
                vol = float(message[len("APP_BRIDGE_VOLUME:"):])
                self.vlc_widget.set_volume(vol)
            except Exception as e:
                print("Error parsing volume:", e)
                
        elif message.startswith("APP_BRIDGE_MUTE:"):
            try:
                muted = message[len("APP_BRIDGE_MUTE:"):].lower() == "true"
                self.vlc_widget.set_mute(muted)
            except Exception as e:
                print("Error parsing mute:", e)
                
        elif message.startswith("APP_BRIDGE_RESIZE:"):
            rect_str = message[len("APP_BRIDGE_RESIZE:"):]
            if rect_str == "hide":
                self.vlc_widget.hide()
            else:
                try:
                    parts = rect_str.split(",")
                    if len(parts) == 4:
                        x = int(float(parts[0]))
                        y = int(float(parts[1]))
                        w = int(float(parts[2]))
                        h = int(float(parts[3]))
                        
                        # Position and resize the native player underneath
                        self.vlc_widget.setGeometry(x, y, w, h)
                        if self.vlc_widget.isHidden():
                            self.vlc_widget.show()
                            # Lower VLC widget below the webview just to ensure it stays behind
                            self.vlc_widget.lower()
                except Exception as e:
                    print("Error parsing resize coordinates:", e)
                    
    def poll_vlc_stats(self):
        stats = self.vlc_widget.get_stream_stats()
        if stats:
            stats_json = json.dumps(stats)
            # Send stats back to the React UI
            js_code = f"if (window.updateNativePlayerBadges) {{ window.updateNativePlayerBadges({stats_json}); }}"
            self.web_view.page().runJavaScript(js_code)
            
    def closeEvent(self, event):
        # Clean up VLC when closing the window
        self.vlc_widget.stop()
        super().closeEvent(event)

def is_local_dev_running(port=5173):
    for host in ["localhost", "127.0.0.1", "::1"]:
        try:
            with socket.create_connection((host, port), timeout=0.2) as s:
                return True
        except:
            continue
    return False


def main():
    # Disable web security to bypass CORS and mixed-content blocking
    sys.argv.append("--disable-web-security")
    
    app = QtWidgets.QApplication(sys.argv)
    
    # Determine the URL to load
    app_url = "http://107.174.178.52" # Default to Ubuntu production server
    
    if len(sys.argv) > 1 and sys.argv[1].startswith("http"):
        app_url = sys.argv[1]
    elif is_local_dev_running(5173):
        app_url = "http://localhost:5173"
        print("Detected local dev server running on port 5173. Loading localhost...")
        
    print(f"Loading Super Stream IPTV Player from: {app_url}")
    
    window = MainWindow(app_url)
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
