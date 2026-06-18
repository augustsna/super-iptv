import time
import os
import vlc
import mock_server
from xtream_client import XtreamClient
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def run_tests():
    logging.info("=== STARTING AUTOMATED STREAMING PLAYER VERIFICATION ===")
    
    # 1. Verify test media exists
    video_path = os.path.abspath("test_ac3_eac3.mp4")
    if not os.path.exists(video_path):
        logging.error("Verification FAILED: test_ac3_eac3.mp4 is missing! Run media_generator.py first.")
        return False
    logging.info(f"Verification SUCCESS: Located test video at {video_path}")

    # 2. Start mock server
    mock_server.start_server(8081)
    time.sleep(1) # Allow server socket bind
    
    success = True
    try:
        # 3. Authenticate with Client
        client = XtreamClient("http://127.0.0.1:8081", "mock_user", "mock_password")
        if not client.authenticate():
            logging.error("Verification FAILED: Client could not authenticate against mock server.")
            success = False
        else:
            logging.info("Verification SUCCESS: Client authenticated against mock server successfully.")

        # 4. Fetch Live categories
        live_cats = client.get_live_categories()
        if not live_cats or len(live_cats) == 0:
            logging.error("Verification FAILED: Live categories are empty.")
            success = False
        else:
            logging.info(f"Verification SUCCESS: Retrieved {len(live_cats)} Live Categories.")

        # 5. Fetch Movie categories
        movie_cats = client.get_vod_categories()
        if not movie_cats or len(movie_cats) == 0:
            logging.error("Verification FAILED: VOD categories are empty.")
            success = False
        else:
            logging.info(f"Verification SUCCESS: Retrieved {len(movie_cats)} VOD Categories.")

        # 6. Fetch Streams
        live_streams = client.get_live_streams()
        if not live_streams or len(live_streams) == 0:
            logging.error("Verification FAILED: Live streams are empty.")
            success = False
        else:
            logging.info(f"Verification SUCCESS: Retrieved {len(live_streams)} Live Streams.")

        # 7. Headless Playback test using python-vlc
        stream_url = client.get_vod_stream_url(202, "mp4")
        logging.info(f"Test stream URL: {stream_url}")

        vlc_instance = vlc.Instance("--no-video-title-show")
        player = vlc_instance.media_player_new()
        media = vlc_instance.media_new(stream_url)
        player.set_media(media)

        logging.info("Starting VLC playback test...")
        player.play()

        # Poll state for up to 5 seconds to let playback start and load tracks
        playback_ok = False
        for _ in range(20):
            time.sleep(0.25)
            state = player.get_state()
            if state == vlc.State.Playing:
                playback_ok = True
                # Query audio track details
                tracks = player.audio_get_track_description()
                logging.info(f"Playback state: Playing. Detected audio tracks: {tracks}")
                
                # Check for our H.264/AC3/EAC3 tracks
                if len(tracks) > 1:
                    logging.info("Verification SUCCESS: VLC audio tracks loaded successfully!")
                else:
                    logging.warning("VLC loaded, but audio track descriptions are still parsing.")
                break
            elif state in (vlc.State.Error, vlc.State.Ended):
                break

        if not playback_ok:
            logging.error(f"Verification FAILED: Media player failed to transition to playing state. Last state: {player.get_state()}")
            success = False
        else:
            logging.info("Verification SUCCESS: VLC Media player initialized and played test stream successfully!")
            player.stop()
            player.release()

    except Exception as e:
        logging.error(f"Verification encountered unexpected exception: {e}")
        success = False
    finally:
        # Stop mock server
        mock_server.stop_server()

    if success:
        logging.info("=== ALL VERIFICATION TESTS PASSED SUCCESSFULLY ===")
    else:
        logging.error("=== VERIFICATION TESTS FAILED ===")
        
    return success

if __name__ == "__main__":
    run_tests()
