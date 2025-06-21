"""
Audio conversion utilities for BeatMapper application.
Supports conversion between MP3, FLAC, WAV, and OGG formats.
"""
import os
import logging
import shutil
from pydub import AudioSegment

logger = logging.getLogger(__name__)

def convert_to_mp3(input_path, output_path):
    """
    Convert any supported audio file to MP3 format
    
    Args:
        input_path: Path to input audio file (MP3, FLAC, WAV, OGG)
        output_path: Path to save MP3 file
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        logger.info(f"Converting audio to MP3: {input_path} -> {output_path}")
        
        if not os.path.exists(input_path):
            logger.error(f"Input file does not exist: {input_path}")
            raise FileNotFoundError(f"Audio file not found at {input_path}")
        
        # Make sure output directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Detect file format and load accordingly
        file_extension = os.path.splitext(input_path)[1].lower()
        
        if file_extension == '.mp3':
            audio = AudioSegment.from_mp3(input_path)
        elif file_extension == '.flac':
            audio = AudioSegment.from_file(input_path, format="flac")
        elif file_extension == '.wav':
            audio = AudioSegment.from_wav(input_path)
        elif file_extension == '.ogg':
            audio = AudioSegment.from_ogg(input_path)
        else:
            # Try generic file loading
            audio = AudioSegment.from_file(input_path)
        
        logger.info(f"Audio loaded: {len(audio)/1000}s duration, format: {file_extension}")
        
        # Export as MP3
        audio.export(output_path, format="mp3")
        logger.info(f"MP3 file saved to {output_path}")
        
        return True
    except Exception as e:
        logger.error(f"Error converting audio to MP3: {e}", exc_info=True)
        raise

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

def audio_to_ogg(input_path, output_path):
    """
    Convert any supported audio file to OGG format
    
    Args:
        input_path: Path to input audio file (MP3, FLAC, WAV, OGG)
        output_path: Path to save OGG file
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        logger.info(f"Converting audio to OGG: {input_path} -> {output_path}")
        
        if not os.path.exists(input_path):
            logger.error(f"Input file does not exist: {input_path}")
            raise FileNotFoundError(f"Audio file not found at {input_path}")
        
        # Make sure output directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Detect file format and load accordingly
        file_extension = os.path.splitext(input_path)[1].lower()        
        if file_extension == '.mp3':
            audio = AudioSegment.from_mp3(input_path)
        elif file_extension == '.flac':
            audio = AudioSegment.from_file(input_path, format="flac")
        elif file_extension == '.wav':
            audio = AudioSegment.from_wav(input_path)
        elif file_extension == '.ogg':
            # If already OGG, just copy
            shutil.copy2(input_path, output_path)
            logger.info(f"OGG file copied to {output_path}")
            return True
        else:
            # Try generic file loading
            audio = AudioSegment.from_file(input_path)
        
        logger.info(f"Audio loaded: {len(audio)/1000}s duration, format: {file_extension}")
        
        # Export as OGG
        audio.export(output_path, format="ogg")
        logger.info(f"OGG file saved to {output_path}")
        
        return True
    except Exception as e:
        logger.error(f"Error converting audio to OGG: {e}", exc_info=True)
        raise