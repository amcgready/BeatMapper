from pydub import AudioSegment
import logging
import os

logging.basicConfig(level=logging.INFO)

def mp3_to_ogg(mp3_path, ogg_path):
    """
    Converts an MP3 file to OGG format.
    Args:
        mp3_path (str): Path to the input MP3 file.
        ogg_path (str): Path to save the output OGG file.
    Returns:
        bool: True if conversion was successful, False otherwise.
    """
    try:
        if not os.path.exists(mp3_path):
            logging.error(f"Input MP3 file does not exist: {mp3_path}")
            return False
        audio = AudioSegment.from_mp3(mp3_path)
        audio.export(ogg_path, format="ogg")
        logging.info(f"Converted {mp3_path} to {ogg_path}")
        return True
    except Exception as e:
        logging.error(f"Failed to convert {mp3_path} to OGG: {e}")
        return False