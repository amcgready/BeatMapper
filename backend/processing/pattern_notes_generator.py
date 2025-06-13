"""
Note generator that uses pattern recognition instead of individual hit detection.
"""
import os
import csv
import logging
import numpy as np
from pathlib import Path

# Try to import librosa
try:
    import librosa
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False

# Import safe formatter
from .utils import format_safe

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def generate_notes_csv(song_path, template_path, output_path):
    """
    Generate a notes.csv file using pattern recognition
    
    Args:
        song_path: Path to the song file to analyze
        template_path: Optional template path to base patterns on
        output_path: Path to save the generated notes.csv
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Get file name for logging
        filename = Path(song_path).stem
        logger.info(f"Generating pattern-based drum notes for {filename}")
        
        # Create output directory if it doesn't exist
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        if not LIBROSA_AVAILABLE:
            logger.warning("librosa not available, generating basic pattern")
            return generate_basic_pattern(song_path, output_path)
        
        # Load audio
        try:
            y, sr = librosa.load(song_path, sr=None)
            duration = librosa.get_duration(y=y, sr=sr)
            logger.info(f"Song duration: {format_safe(duration, '.2f')} seconds")
            
            # Beat detection
            onset_env = librosa.onset.onset_strength(y=y, sr=sr)
            tempo, beats = librosa.beat.beat_track(onset_envelope=onset_env, sr=sr)
            
            # Convert to beat times
            beat_times = librosa.frames_to_time(beats, sr=sr)
            
            # Log extracted info
            logger.info(f"Detected tempo: {format_safe(tempo, '.2f')} BPM")
            logger.info(f"Found {len(beat_times)} beats")
            
            # Extract segments for pattern analysis
            segments = analyze_segments(y, sr, onset_env, beat_times)
            
            # Generate notes
            notes = generate_notes_from_patterns(beat_times, segments, duration)
            
            # Write notes to CSV
            write_notes_to_csv(notes, output_path)
            
            logger.info(f"Generated {len(notes)} notes at {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error with analysis: {e}")
            return generate_basic_pattern(song_path, output_path)
            
    except Exception as e:
        logger.error(f"Failed to generate basic notes.csv: {e}")
        return False

def analyze_segments(y, sr, onset_env, beat_times):
    """
    Analyze audio for repeating segments and patterns
    
    Args:
        y: Audio time series
        sr: Sample rate
        onset_env: Onset strength envelope
        beat_times: Array of detected beat times
        
    Returns:
        list: Segment information [(start, end, pattern_type), ...]
    """
    try:
        # Calculate MFCC features
        mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
        
        # Use agglomerative clustering to find segments
        S = librosa.segment.recurrence_matrix(mfcc, mode='affinity')
        
        # Estimate number of segments based on song duration
        duration = float(librosa.get_duration(y=y, sr=sr))
        n_segments = max(3, min(8, int(duration / 30)))
        
        bounds = librosa.segment.agglomerative(S, n_segments)
        bound_times = librosa.frames_to_time(bounds, sr=sr)
        
        # Convert to segments with pattern types
        segments = []
        for i in range(len(bound_times) - 1):
            start = float(bound_times[i])
            end = float(bound_times[i + 1])
            
            # Simple alternating pattern types
            pattern_type = "A" if i % 2 == 0 else "B"
            
            segments.append((start, end, pattern_type))
            
        return segments
        
    except Exception as e:
        logger.warning(f"Failed to analyze segments: {e}")
        
        # Fallback to basic segments
        duration = float(librosa.get_duration(y=y, sr=sr))
        segments = []
        
        # Create 4 segments
        segment_duration = duration / 4
        for i in range(4):
            start = i * segment_duration
            end = (i + 1) * segment_duration
            pattern_type = "A" if i % 2 == 0 else "B"
            segments.append((start, end, pattern_type))
            
        return segments

def generate_notes_from_patterns(beat_times, segments, duration):
    """
    Generate drum notes based on beat times and segments
    
    Args:
        beat_times: Array of beat times
        segments: List of segments with pattern types
        duration: Total song duration
        
    Returns:
        list: Generated notes as rows for CSV
    """
    notes = []
    
    pattern_types = {
        "A": [  # Standard rock pattern
            (0, ["1", "1", "1", "1", "", "6"]),  # Kick on 1
            (0, ["1", "3", "3", "1", "", "8"]),  # Hi-hat on 1
            (1, ["1", "2", "2", "1", "", "7"]),  # Snare on 2
            (1, ["1", "3", "3", "1", "", "8"]),  # Hi-hat on 2
            (2, ["1", "1", "1", "1", "", "6"]),  # Kick on 3
            (2, ["1", "3", "3", "1", "", "8"]),  # Hi-hat on 3
            (3, ["1", "2", "2", "1", "", "7"]),  # Snare on 4
            (3, ["1", "3", "3", "1", "", "8"]),  # Hi-hat on 4
        ],
        "B": [  # Variation with more kicks
            (0, ["1", "1", "1", "1", "", "6"]),  # Kick on 1
            (0, ["1", "3", "3", "1", "", "8"]),  # Hi-hat on 1
            (1, ["1", "2", "2", "1", "", "7"]),  # Snare on 2
            (1, ["1", "3", "3", "1", "", "8"]),  # Hi-hat on 2
            (2, ["1", "1", "1", "1", "", "6"]),  # Kick on 3
            (2, ["1", "3", "3", "1", "", "8"]),  # Hi-hat on 3
            (3, ["1", "2", "2", "1", "", "7"]),  # Snare on 4
            (3, ["1", "1", "1", "1", "", "6"]),  # Extra kick on 4
            (3, ["1", "3", "3", "1", "", "8"]),  # Hi-hat on 4
        ],
    }
    
    # Convert beat_times to python floats if numpy array
    if hasattr(beat_times, 'tolist'):
        beat_times = beat_times.tolist()
    
    # Process each beat
    for i, beat_time in enumerate(beat_times):
        # Get beat position in measure (assuming 4/4 time)
        beat_in_measure = i % 4
        measure = i // 4
        
        # Determine which segment we're in
        current_segment = None
        for start, end, segment_type in segments:
            if start <= beat_time < end:
                current_segment = segment_type
                break
        
        if not current_segment:
            current_segment = "A"  # Default
        
        # Get pattern for this segment type
        pattern = pattern_types.get(current_segment, pattern_types["A"])
        
        # Add notes based on pattern
        for pattern_beat, values in pattern:
            if pattern_beat == beat_in_measure:
                # Add the note at the beat time
                notes.append([f"{beat_time:.2f}"] + values)
                
                # Add crash on first beat of certain measures
                if beat_in_measure == 0 and measure % 4 == 0:
                    notes.append([f"{beat_time:.2f}", "2", "5", "6", "1", "", "5"])
    
    return notes

def generate_basic_pattern(song_path, output_path):
    """
    Generate a basic pattern without audio analysis
    
    Args:
        song_path: Path to the song file
        output_path: Path to save the notes.csv
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Try to get audio duration
        duration = 180  # Default 3 minutes
        
        if LIBROSA_AVAILABLE:
            try:
                y, sr = librosa.load(song_path, sr=None)
                duration = librosa.get_duration(y=y, sr=sr)
            except:
                pass
        
        # Set a constant tempo (120 BPM = 0.5s per beat)
        beat_interval = 0.5
        
        # Generate basic pattern
        notes = []
        
        # Start at 3 seconds to skip intro
        current_time = 3.0
        measure = 0
        
        while current_time < duration - 5.0:
            for beat in range(4):  # 4/4 time signature
                beat_time = current_time + beat * beat_interval
                
                # Basic rock pattern
                if beat == 0:  # Beat 1
                    notes.append([f"{beat_time:.2f}", "1", "1", "1", "1", "", "6"])  # Kick
                    notes.append([f"{beat_time:.2f}", "1", "3", "3", "1", "", "8"])  # Hi-hat
                    
                    # Add crash at start of some measures
                    if measure % 4 == 0:
                        notes.append([f"{beat_time:.2f}", "2", "5", "6", "1", "", "5"])  # Crash
                        
                elif beat == 1:  # Beat 2
                    notes.append([f"{beat_time:.2f}", "1", "2", "2", "1", "", "7"])  # Snare
                    notes.append([f"{beat_time:.2f}", "1", "3", "3", "1", "", "8"])  # Hi-hat
                    
                elif beat == 2:  # Beat 3
                    notes.append([f"{beat_time:.2f}", "1", "1", "1", "1", "", "6"])  # Kick
                    notes.append([f"{beat_time:.2f}", "1", "3", "3", "1", "", "8"])  # Hi-hat
                    
                else:  # Beat 4
                    notes.append([f"{beat_time:.2f}", "1", "2", "2", "1", "", "7"])  # Snare
                    notes.append([f"{beat_time:.2f}", "1", "3", "3", "1", "", "8"])  # Hi-hat
            
            current_time += 4 * beat_interval
            measure += 1
        
        # Write to CSV
        write_notes_to_csv(notes, output_path)
        
        logger.info(f"Generated {len(notes)} notes using basic pattern")
        return True
        
    except Exception as e:
        logger.error(f"Failed to generate basic pattern: {e}")
        return False

def write_notes_to_csv(notes, output_path):
    """Write notes to CSV file"""
    try:
        with open(output_path, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["Time [s]", "Enemy Type", "Aux Color 1", "Aux Color 2", "Nº Enemies", "interval", "Aux"])
            writer.writerows(notes)
        return True
    except Exception as e:
        logger.error(f"Failed to write notes to CSV: {e}")
        return False

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate pattern-based drum notes")
    parser.add_argument("song_path", help="Path to the song file")
    parser.add_argument("output_path", help="Path to save the notes.csv")
    parser.add_argument("--template", help="Optional template path")
    
    args = parser.parse_args()
    
    if generate_notes_csv(args.song_path, args.template, args.output_path):
        print(f"Successfully generated notes at {args.output_path}")
    else:
        print("Failed to generate notes")