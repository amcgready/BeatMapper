"""
Audio conversion utilities for BeatMapper application.
"""
import os
import logging
from pydub import AudioSegment

logger = logging.getLogger(__name__)

def mp3_to_ogg(input_path, output_path):
    """
    Convert an MP3 file to OGG format
    
    Args:
        input_path: Path to MP3 file
        output_path: Path to save OGG file
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        logger.info(f"Converting MP3 to OGG: {input_path} -> {output_path}")
        
        if not os.path.exists(input_path):
            logger.error(f"Input file does not exist: {input_path}")
            raise FileNotFoundError(f"MP3 file not found at {input_path}")
        
        # Make sure output directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Load audio file using pydub
        audio = AudioSegment.from_mp3(input_path)
        logger.info(f"MP3 loaded: {len(audio)/1000}s duration")
        
        # Export as OGG
        audio.export(output_path, format="ogg")
        logger.info(f"OGG file saved to {output_path}")
        
        return True
    except Exception as e:
        logger.error(f"Error converting MP3 to OGG: {e}", exc_info=True)
        raise