import os
import subprocess
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def generate_test_media(output_dir="."):
    """Generates a test MP4 video with AC3 and EAC3 audio tracks using FFmpeg."""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    output_file = os.path.join(output_dir, "test_ac3_eac3.mp4")
    
    if os.path.exists(output_file):
        logging.info(f"Test media file already exists: {output_file}")
        return output_file

    logging.info("Generating multi-track AC3/EAC3 test media file. Please wait...")
    
    # FFmpeg command:
    # - 30 seconds H.264 video test source (1280x720 @ 30fps)
    # - Sine wave audio input 1 (440 Hz)
    # - Sine wave audio input 2 (880 Hz)
    # - Track 1: AC3 format (192 kbps)
    # - Track 2: EAC3 format (224 kbps)
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "testsrc=duration=30:size=1280x720:rate=30",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=30",
        "-f", "lavfi", "-i", "sine=frequency=880:duration=30",
        "-map", "0:v",
        "-map", "1:a",
        "-map", "2:a",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-c:a:0", "ac3",
        "-b:a:0", "192k",
        "-metadata:s:a:0", "title=AC3 Audio (440Hz)",
        "-c:a:1", "eac3",
        "-b:a:1", "224k",
        "-metadata:s:a:1", "title=EAC3 Audio (880Hz)",
        output_file
    ]
    
    try:
        # Run FFmpeg command
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        logging.info(f"Successfully generated: {output_file}")
        return output_file
    except subprocess.CalledProcessError as e:
        logging.error(f"FFmpeg generation failed: {e.stderr}")
        raise e

if __name__ == "__main__":
    generate_test_media()
