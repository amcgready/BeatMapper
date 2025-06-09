import os
import logging
from pydub import AudioSegment

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
        
        # Calculate the best position for the preview
        # Use the first 15 seconds after 30 seconds from the start,
        # or the start of the song if it's too short
        if len(audio) < start_ms + duration_ms:
            if len(audio) < duration_ms:
                # If the song is shorter than the preview duration,
                # just use the whole song
                preview = audio
                logging.info(f"Song is shorter than preview duration, using entire song")
            else:
                # If the song is shorter than start_ms + duration_ms,
                # start from the beginning
                preview = audio[:duration_ms]
                logging.info(f"Song is too short for preview at {start_ms}ms, using first {duration_ms}ms")
        else:
            preview = audio[start_ms:start_ms + duration_ms]
            logging.info(f"Using preview from {start_ms}ms to {start_ms + duration_ms}ms")
        
        preview.export(preview_path, format="ogg")
        logging.info(f"Preview generated at {preview_path}")
        return True
    except Exception as e:
        logging.error(f"Failed to generate preview: {e}")
        
        # Try a fallback approach using a different method if available
        try:
            # Simple fallback to just convert the original file
            if os.path.exists(mp3_path):
                audio = AudioSegment.from_mp3(mp3_path)
                # Just take first few seconds
                preview = audio[:min(len(audio), 10000)]
                preview.export(preview_path, format="ogg")
                logging.info(f"Preview generated using fallback method at {preview_path}")
                return True
        except Exception as fallback_error:
            logging.error(f"Fallback preview generation also failed: {fallback_error}")
            
        return False