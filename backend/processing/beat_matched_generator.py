"""
Advanced beat-matching note generator that creates MIDI-like drum patterns
synchronized to the audio's actual beat and tempo.
"""
import os
import logging
import csv
import numpy as np
from pathlib import Path

# Import common utilities
from .utils import format_safe

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import optional libraries
try:
    import librosa
    LIBROSA_AVAILABLE = True
except ImportError:
    logger.warning("librosa library not available, falling back to basic beat matching")
    LIBROSA_AVAILABLE = False

def generate_notes_csv(song_path, template_path, output_path):
    """
    Generate a notes.csv file with advanced beat matching
    
    Args:
        song_path: Path to the audio file
        template_path: Path to a template file (optional)
        output_path: Path to save the notes.csv file
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Extract filename without extension for logging
        filename = Path(song_path).stem
        logger.info(f"Generating beat-matched notes for {filename}")
        
        # Create output directory if it doesn't exist
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Load audio file if librosa is available
        if LIBROSA_AVAILABLE:
            try:
                y, sr = librosa.load(song_path, sr=None)
                duration = librosa.get_duration(y=y, sr=sr)
                logger.info(f"Song duration: {format_safe(duration, '.2f')} seconds")
                
                # Beat detection
                tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
                beat_times = librosa.frames_to_time(beat_frames, sr=sr)
                
                # Log detected tempo (fixed format issue)
                logger.info(f"Detected tempo: {format_safe(tempo, '.2f')} BPM")
                logger.info(f"Found {len(beat_times)} beats")
                
                # Use beats to generate notes
                notes = generate_notes_from_beats(beat_times, duration)
                
                # Write to CSV
                with open(output_path, 'w', newline='') as csvfile:
                    writer = csv.writer(csvfile)
                    writer.writerow(["Time [s]", "Enemy Type", "Aux Color 1", "Aux Color 2", "Nº Enemies", "interval", "Aux"])
                    writer.writerows(notes)
                
                logger.info(f"Generated {len(notes)} beat-matched notes")
                return True
                
            except Exception as e:
                logger.error(f"Error generating beat-matched notes: {e}")
                # Continue to fallback
        
        # Fallback to basic beat matching without audio analysis
        logger.info("Using basic beat matching without audio analysis")
        return generate_basic_beat_pattern(song_path, output_path)
        
    except Exception as e:
        logger.error(f"Failed to generate beat-matched notes: {e}")
        return False

def generate_notes_from_beats(beat_times, duration):
    """
    Generate drum notes based on detected beats
    
    Args:
        beat_times: Array of beat times in seconds
        duration: Total duration of the song
        
    Returns:
        list: List of note rows for CSV
    """
    notes = []
    
    # Minimum beat time (avoid very early beats which may be analysis artifacts)
    min_time = 2.5  # Skip first 2.5 seconds
    
    # Process each beat
    for i, beat_time in enumerate(beat_times):
        # Skip early beats
        if beat_time < min_time:
            continue
            
        # Beat position in measure (assuming 4/4 time)
        beat_in_measure = i % 4
        measure_number = i // 4
        
        # Basic drum pattern: kick on 1 and 3, snare on 2 and 4
        if beat_in_measure == 0:  # Beat 1 - kick
            notes.append([format_safe(beat_time, '.2f'), "1", "1", "1", "1", "", "6"])
            
        elif beat_in_measure == 2:  # Beat 3 - kick
            notes.append([format_safe(beat_time, '.2f'), "1", "1", "1", "1", "", "6"])
            
        elif beat_in_measure == 1 or beat_in_measure == 3:  # Beats 2 & 4 - snare
            notes.append([format_safe(beat_time, '.2f'), "1", "2", "2", "1", "", "7"])
            
        # Add hi-hat on every beat
        notes.append([format_safe(beat_time, '.2f'), "1", "3", "3", "1", "", "8"])
        
        # Add crash cymbal at start of every 4th measure
        if beat_in_measure == 0 and measure_number % 4 == 0:
            notes.append([format_safe(beat_time, '.2f'), "2", "5", "6", "1", "", "5"])
    
    # Add subdivisions (8th notes) between beats
    subdivisions = []
    for i in range(len(beat_times) - 1):
        beat_time = beat_times[i]
        next_beat = beat_times[i + 1]
        
        # Calculate midpoint - 8th note
        eighth_note = (beat_time + next_beat) / 2
        
        # Add hi-hat on 8th notes
        subdivisions.append([format_safe(eighth_note, '.2f'), "1", "3", "3", "1", "", "8"])
    
    # Combine and sort all notes by time
    all_notes = notes + subdivisions
    all_notes.sort(key=lambda x: float(x[0]))
    
    return all_notes

def generate_basic_beat_pattern(song_path, output_path):
    """
    Generate a basic beat pattern without audio analysis
    as a fallback when beat detection fails
    
    Args:
        song_path: Path to the audio file
        output_path: Path to save the notes.csv file
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Try to get song duration if librosa is available
        if LIBROSA_AVAILABLE:
            try:
                y, sr = librosa.load(song_path, sr=None)
                duration = librosa.get_duration(y=y, sr=sr)
            except Exception:
                # Fallback to a default duration if needed
                duration = 180  # Default 3 minutes
        else:
            # Try to get duration from other sources
            try:
                from .audio_converter import get_audio_duration
                duration = get_audio_duration(song_path)
            except Exception:
                duration = 180  # Default 3 minutes
        
        # Estimate beats assuming 120 BPM (0.5 seconds per beat)
        beat_interval = 0.5  # seconds per beat
        
        # Generate pattern
        notes = []
        
        # Start at 3 seconds (skip intro)
        current_time = 3.0
        measure = 0
        
        while current_time < duration - 3.0:  # Stop 3 seconds before end
            for beat in range(4):  # 4 beats per measure
                beat_time = current_time + beat * beat_interval
                
                # Basic drum pattern: kick on 1 and 3, snare on 2 and 4
                if beat == 0:  # Beat 1 - kick
                    notes.append([f"{beat_time:.2f}", "1", "1", "1", "1", "", "6"])
                    
                    # Add crash every 4 measures
                    if measure % 4 == 0:
                        notes.append([f"{beat_time:.2f}", "2", "5", "6", "1", "", "5"])
                        
                elif beat == 2:  # Beat 3 - kick
                    notes.append([f"{beat_time:.2f}", "1", "1", "1", "1", "", "6"])
                    
                elif beat == 1 or beat == 3:  # Beats 2 & 4 - snare
                    notes.append([f"{beat_time:.2f}", "1", "2", "2", "1", "", "7"])
                    
                # Add hi-hat on every beat
                notes.append([f"{beat_time:.2f}", "1", "3", "3", "1", "", "8"])
                
                # Add hi-hat on 8th notes
                eighth_note = beat_time + beat_interval / 2
                if eighth_note < duration - 3.0:
                    notes.append([f"{eighth_note:.2f}", "1", "3", "3", "1", "", "8"])
            
            # Next measure
            current_time += 4 * beat_interval
            measure += 1
        
        # Write to CSV
        with open(output_path, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["Time [s]", "Enemy Type", "Aux Color 1", "Aux Color 2", "Nº Enemies", "interval", "Aux"])
            writer.writerows(notes)
        
        logger.info(f"Generated {len(notes)} notes using basic beat pattern")
        return True
        
    except Exception as e:
        logger.error(f"Failed to generate basic beat pattern: {e}")
        return False

def get_tempo_from_audio(audio_path):
    """
    Extract tempo from audio file using librosa
    
    Args:
        audio_path: Path to audio file
        
    Returns:
        float: Tempo in BPM (or None if detection fails)
    """
    if not LIBROSA_AVAILABLE:
        return None
        
    try:
        # Load audio with librosa
        y, sr = librosa.load(audio_path, sr=None)
        
        # Calculate onset envelope
        onset_env = librosa.onset.onset_strength(y=y, sr=sr)
        
        # Estimate tempo
        dtempo = librosa.beat.tempo(onset_envelope=onset_env, sr=sr)
        
        # Convert numpy value to regular float and round
        if isinstance(dtempo, (np.ndarray, np.number)):
            tempo = float(dtempo.item())
        else:
            tempo = float(dtempo)
            
        return round(tempo, 2)
        
    except Exception as e:
        logger.warning(f"Failed to detect tempo: {e}")
        return None

def enhance_with_fills(notes, duration):
    """
    Add drum fills at regular intervals
    
    Args:
        notes: List of note rows
        duration: Song duration in seconds
        
    Returns:
        list: Enhanced notes with fills
    """
    # TODO: Implement fill generation
    return notes