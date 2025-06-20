import csv
import logging
import os
import librosa

logging.basicConfig(level=logging.INFO)

INFO_HEADER = ["Song Name", "Author Name", "Difficulty", "Song Duration", "Song Map"]

# Difficulty mapping
DIFFICULTY_MAP = {
    "EASY": 0,
    "MEDIUM": 1, 
    "HARD": 2
}

# Song map mapping
SONG_MAP_MAP = {
    "VULCAN": 0,
    "DESERT": 1,
    "STORM": 2
}

def get_audio_duration(audio_path):
    """
    Get the duration of an audio file in seconds.
    Returns duration as float, or 0 if unable to determine.
    """
    try:
        if os.path.exists(audio_path):
            duration = librosa.get_duration(filename=audio_path)
            return round(duration, 2)
        else:
            logging.warning(f"Audio file not found: {audio_path}")
            return 0
    except Exception as e:
        logging.error(f"Failed to get audio duration: {e}")
        return 0

def validate_metadata(song_metadata):
    """
    Validates and sanitizes song metadata for the new format.
    Returns a dict with all required fields.
    """
    validated = {}
    
    # Basic metadata
    validated["title"] = str(song_metadata.get("title", "")).strip()
    validated["artist"] = str(song_metadata.get("artist", "")).strip()
    
    # Difficulty - default to EASY (0) if not specified
    difficulty = song_metadata.get("difficulty", "EASY")
    if isinstance(difficulty, str) and difficulty.upper() in DIFFICULTY_MAP:
        validated["difficulty"] = DIFFICULTY_MAP[difficulty.upper()]
    elif isinstance(difficulty, int) and difficulty in [0, 1, 2]:
        validated["difficulty"] = difficulty
    else:
        logging.warning(f"Invalid difficulty '{difficulty}', defaulting to EASY (0)")
        validated["difficulty"] = 0
    
    # Duration - will be calculated from audio file
    validated["duration"] = song_metadata.get("duration", 0)
    
    # Song Map - default to VULCAN (0) if not specified
    song_map = song_metadata.get("song_map", "VULCAN")
    if isinstance(song_map, str) and song_map.upper() in SONG_MAP_MAP:
        validated["song_map"] = SONG_MAP_MAP[song_map.upper()]
    elif isinstance(song_map, int) and song_map in [0, 1, 2]:
        validated["song_map"] = song_map
    else:
        logging.warning(f"Invalid song map '{song_map}', defaulting to VULCAN (0)")
        validated["song_map"] = 0
    
    return validated

def generate_info_csv(song_metadata, output_path, audio_path=None):
    """
    Writes song metadata to info.csv with the new format and validation.
    Args:
        song_metadata (dict): Metadata with keys title, artist, difficulty, song_map, etc.
        output_path (str): Path to save the info.csv file.
        audio_path (str, optional): Path to audio file to calculate duration.
    Returns:
        bool: True if successful, False otherwise.
    """
    try:
        if not output_path.lower().endswith('.csv'):
            logging.error("Output path must be a .csv file.")
            return False
            
        validated = validate_metadata(song_metadata)
        
        # Get audio duration if audio path is provided
        if audio_path and validated["duration"] == 0:
            validated["duration"] = get_audio_duration(audio_path)
            
        row = [
            validated.get("title", ""),
            validated.get("artist", ""),
            validated.get("difficulty", 0),
            validated.get("duration", 0),
            validated.get("song_map", 0)
        ]
        
        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(INFO_HEADER)
            writer.writerow(row)
            
        logging.info(f"info.csv generated at {output_path}")
        logging.info(f"  Song Name: {validated['title']}")
        logging.info(f"  Author Name: {validated['artist']}")
        logging.info(f"  Difficulty: {validated['difficulty']} ({['EASY', 'MEDIUM', 'HARD'][validated['difficulty']]})")
        logging.info(f"  Duration: {validated['duration']} seconds")
        logging.info(f"  Song Map: {validated['song_map']} ({['VULCAN', 'DESERT', 'STORM'][validated['song_map']]})")
        
        return True
    except Exception as e:
        logging.error(f"Failed to generate info.csv: {e}")
        return False