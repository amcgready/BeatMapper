from pydub import AudioSegment
import logging
import os

logging.basicConfig(level=logging.INFO)

def generate_preview(mp3_path, preview_path, start_ms=30000, duration_ms=15000):
    """
    Generates a preview OGG clip from the MP3 file.
    Args:
        mp3_path (str): Path to the input MP3 file.
        preview_path (str): Path to save the output OGG preview.
        start_ms (int): Start time in milliseconds for the preview.
        duration_ms (int): Duration of the preview in milliseconds.
    Returns:
        bool: True if successful, False otherwise.
    """
    try:
        if not os.path.exists(mp3_path):
            logging.error(f"Input MP3 file does not exist: {mp3_path}")
            return False
        audio = AudioSegment.from_mp3(mp3_path)
        if len(audio) < start_ms + duration_ms:
            # If the song is too short, take the last duration_ms segment
            if len(audio) > duration_ms:
                preview = audio[-duration_ms:]
                logging.warning("Song shorter than preview window; using last segment.")
            else:
                preview = audio
                logging.warning("Song shorter than preview duration; using full song.")
        else:
            preview = audio[start_ms:start_ms+duration_ms]
        preview.export(preview_path, format="ogg")
        logging.info(f"Preview generated at {preview_path}")
        return True
    except Exception as e:
        logging.error(f"Failed to generate preview: {e}")
        return False