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
    "HARD": 2,
    "EXTREME": 3
}

# Difficulty thresholds (enemies per second)
DIFFICULTY_THRESHOLDS = {
    "EASY": 1.0,
    "MEDIUM": 1.7,
    "HARD": 2.3,
    "EXTREME": 2.9
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
    elif isinstance(difficulty, int) and difficulty in [0, 1, 2, 3]:
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

def generate_info_csv(song_metadata, output_path, audio_path=None, notes_csv_path=None, auto_detect_difficulty=True):
    """
    Writes song metadata to info.csv with the new format and validation.
    Args:
        song_metadata (dict): Metadata with keys title, artist, difficulty, song_map, etc.
        output_path (str): Path to save the info.csv file.
        audio_path (str, optional): Path to audio file to calculate duration.
        notes_csv_path (str, optional): Path to notes.csv file to analyze difficulty from enemies per second.
        auto_detect_difficulty (bool): Whether to automatically detect difficulty from notes analysis.
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
        
        # Auto-detect difficulty from notes.csv if enabled and not already specified
        if auto_detect_difficulty and notes_csv_path and song_metadata.get("difficulty") in [None, "", "EASY"]:
            detected_difficulty = analyze_notes_difficulty(notes_csv_path)
            validated["difficulty"] = DIFFICULTY_MAP[detected_difficulty]
            logging.info(f"Auto-detected difficulty from notes: {detected_difficulty} ({validated['difficulty']})")
        elif auto_detect_difficulty and audio_path and song_metadata.get("difficulty") in [None, "", "EASY"]:
            # Fallback to audio analysis if notes.csv not available
            detected_difficulty = analyze_audio_difficulty(audio_path)
            validated["difficulty"] = DIFFICULTY_MAP[detected_difficulty]
            logging.info(f"Auto-detected difficulty from audio: {detected_difficulty} ({validated['difficulty']})")
        
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
        logging.info(f"  Difficulty: {validated['difficulty']} ({['EASY', 'MEDIUM', 'HARD', 'EXTREME'][validated['difficulty']]})")
        logging.info(f"  Duration: {validated['duration']} seconds")
        logging.info(f"  Song Map: {validated['song_map']} ({['VULCAN', 'DESERT', 'STORM'][validated['song_map']]})")
        
        return True
    except Exception as e:
        logging.error(f"Failed to generate info.csv: {e}")
        return False

def analyze_audio_difficulty(audio_path):
    """
    Analyze audio file to determine appropriate difficulty based on beat density.
    
    Args:
        audio_path (str): Path to the audio file
        
    Returns:
        str: Difficulty level ("EASY", "MEDIUM", "HARD", "EXTREME")
    """
    try:
        if not os.path.exists(audio_path):
            logging.warning(f"Audio file not found for analysis: {audio_path}")
            return "EASY"
            
        # Load audio file
        y, sr = librosa.load(audio_path)
        duration = librosa.get_duration(filename=audio_path)
        
        if duration <= 0:
            logging.warning("Invalid audio duration, defaulting to EASY")
            return "EASY"
        
        # Detect beats and tempo
        tempo, beats = librosa.beat.beat_track(y=y, sr=sr, hop_length=512)
        
        # Calculate beats per second
        beats_per_second = len(beats) / duration
        
        # Also analyze onset strength for additional complexity measure
        onset_frames = librosa.onset.onset_detect(y=y, sr=sr, hop_length=512)
        onsets_per_second = len(onset_frames) / duration
        
        # Calculate average complexity metric (weighted combination)
        # Beats are the primary rhythm, onsets add complexity from other instruments
        complexity_score = (beats_per_second * 0.7) + (onsets_per_second * 0.3)
        
        logging.info(f"Audio analysis results:")
        logging.info(f"  Duration: {duration:.2f} seconds")
        logging.info(f"  Tempo: {tempo:.2f} BPM")
        logging.info(f"  Beats per second: {beats_per_second:.2f}")
        logging.info(f"  Onsets per second: {onsets_per_second:.2f}")
        logging.info(f"  Complexity score: {complexity_score:.2f}")
        
        # Determine difficulty based on complexity score
        if complexity_score >= DIFFICULTY_THRESHOLDS["EXTREME"]:
            difficulty = "EXTREME"
        elif complexity_score >= DIFFICULTY_THRESHOLDS["HARD"]:
            difficulty = "HARD"
        elif complexity_score >= DIFFICULTY_THRESHOLDS["MEDIUM"]:
            difficulty = "MEDIUM"
        else:
            difficulty = "EASY"
            
        logging.info(f"  Determined difficulty: {difficulty} (target: {DIFFICULTY_THRESHOLDS[difficulty]} enemies/sec)")
        
        return difficulty
        
    except Exception as e:
        logging.error(f"Error analyzing audio difficulty: {e}")
        logging.warning("Falling back to EASY difficulty")
        return "EASY"

def analyze_notes_difficulty(notes_csv_path):
    """
    Analyze notes.csv file to determine appropriate difficulty based on enemies per second.
    
    Args:
        notes_csv_path (str): Path to the notes.csv file
        
    Returns:
        str: Difficulty level ("EASY", "MEDIUM", "HARD", "EXTREME")
    """
    try:
        if not os.path.exists(notes_csv_path):
            logging.warning(f"Notes CSV file not found for analysis: {notes_csv_path}")
            return "EASY"
            
        import csv
        
        # Read the notes.csv file
        enemies = []
        with open(notes_csv_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    time = float(row['Time [s]'])
                    enemy_type = int(row['Enemy Type'])
                    enemies.append({'time': time, 'type': enemy_type})
                except (ValueError, KeyError) as e:
                    logging.warning(f"Invalid row in notes.csv: {row} - {e}")
                    continue
        
        if not enemies:
            logging.warning("No valid enemies found in notes.csv, defaulting to EASY")
            return "EASY"
        
        # Calculate time range and enemies per second
        start_time = min(enemy['time'] for enemy in enemies)
        end_time = max(enemy['time'] for enemy in enemies)
        duration = end_time - start_time
        
        if duration <= 0:
            logging.warning("Invalid duration in notes.csv, defaulting to EASY")
            return "EASY"
        
        enemies_per_second = len(enemies) / duration
        
        logging.info(f"Notes analysis results:")
        logging.info(f"  Total enemies: {len(enemies)}")
        logging.info(f"  Time range: {start_time:.2f}s to {end_time:.2f}s")
        logging.info(f"  Active duration: {duration:.2f}s")
        logging.info(f"  Enemies per second: {enemies_per_second:.2f}")
        
        # Determine difficulty based on enemies per second thresholds
        if enemies_per_second >= DIFFICULTY_THRESHOLDS["EXTREME"]:
            difficulty = "EXTREME"
        elif enemies_per_second >= DIFFICULTY_THRESHOLDS["HARD"]:
            difficulty = "HARD"
        elif enemies_per_second >= DIFFICULTY_THRESHOLDS["MEDIUM"]:
            difficulty = "MEDIUM"
        else:
            difficulty = "EASY"
            
        logging.info(f"  Determined difficulty: {difficulty} (threshold: {DIFFICULTY_THRESHOLDS[difficulty]} enemies/sec)")
        
        return difficulty
        
    except Exception as e:
        logging.error(f"Error analyzing notes difficulty: {e}")
        logging.warning("Falling back to EASY difficulty")
        return "EASY"