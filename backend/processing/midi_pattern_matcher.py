"""
Specialized module for creating note patterns that closely match MIDI reference files.
"""
import os
import csv
import logging
import random
import numpy as np
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def extract_midi_patterns(midi_path):
    """Extract repeating patterns from MIDI reference file"""
    patterns = []
    
    try:
        # Load MIDI notes
        notes = []
        with open(midi_path, 'r') as f:
            reader = csv.reader(f)
            header = next(reader)
            for row in reader:
                if len(row) >= 6:
                    notes.append(row)
        
        # Extract timing
        times = [float(note[0]) for note in notes]
        if not times:
            return []
            
        # Find pattern start times (usually around 3.0s)
        pattern_start = min(times)
        if pattern_start < 2.0:
            pattern_start = 3.0
            
        # Sort notes by time
        notes.sort(key=lambda n: float(n[0]))
        
        # Detect measure length (assuming 4/4 time)
        # Try to find repeating patterns by looking at first 16 beats
        measured_intervals = []
        last_time = None
        
        for time in times[:32]:
            if last_time is not None:
                interval = time - last_time
                if 0.2 < interval < 0.3:  # Typical 8th note at 120 BPM is ~0.25s
                    measured_intervals.append(interval)
            last_time = time
            
        # Calculate average 8th note duration
        if measured_intervals:
            eighth_note = sum(measured_intervals) / len(measured_intervals)
            quarter_note = eighth_note * 2
            measure = quarter_note * 4
        else:
            # Default to 120 BPM
            quarter_note = 0.5  # 120 BPM = 0.5s per quarter note
            measure = 2.0       # 4 beats per measure
            
        logger.info(f"Detected measure length: {measure:.2f}s")
        
        # Extract 1-measure patterns
        current_pos = pattern_start
        while current_pos + measure <= max(times):
            # Get notes in this measure
            measure_notes = [n for n in notes if current_pos <= float(n[0]) < current_pos + measure]
            
            if measure_notes:
                # Store the pattern with relative timing
                pattern = []
                for note in measure_notes:
                    # Convert to relative position within measure
                    rel_pos = (float(note[0]) - current_pos) / measure
                    pattern.append((rel_pos, note[1], note[2], note[3], note[4], note[5]))
                    
                patterns.append(pattern)
                
            current_pos += measure
            
        logger.info(f"Extracted {len(patterns)} patterns from MIDI")
        return patterns
        
    except Exception as e:
        logger.error(f"Error extracting MIDI patterns: {e}")
        return []

def apply_midi_patterns(audio_path, midi_path, output_path):
    """
    Generate notes for an audio file using patterns from a MIDI reference
    
    Args:
        audio_path: Path to audio file
        midi_path: Path to MIDI reference CSV
        output_path: Path to save generated notes
        
    Returns:
        bool: Success or failure
    """
    try:
        # Extract patterns from MIDI
        patterns = extract_midi_patterns(midi_path)
        if not patterns:
            logger.error("No patterns extracted from MIDI reference")
            return False
            
        # Detect tempo and beats from audio
        tempo, beat_times = detect_audio_tempo(audio_path)
        
        # Generate notes using detected beats and MIDI patterns
        notes = generate_notes_from_patterns(patterns, beat_times, tempo)
        
        # Write notes to CSV
        with open(output_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["Time [s]", "Enemy Type", "Aux Color 1", "Aux Color 2", "Nº Enemies", "interval", "Aux"])
            writer.writerows(notes)
            
        logger.info(f"Generated {len(notes)} MIDI-patterned notes")
        return True
        
    except Exception as e:
        logger.error(f"Error applying MIDI patterns: {e}")
        return False

def detect_audio_tempo(audio_path):
    """Detect tempo and beat times from audio file"""
    try:
        import librosa
        
        # Load audio file
        y, sr = librosa.load(audio_path, sr=None)
        
        # Detect tempo and beats
        onset_env = librosa.onset.onset_strength(y=y, sr=sr)
        tempo, beats = librosa.beat.beat_track(onset_envelope=onset_env, sr=sr)
        
        # Convert frames to times
        beat_times = librosa.frames_to_time(beats, sr=sr)
        
        logger.info(f"Detected tempo: {tempo:.1f} BPM with {len(beat_times)} beats")
        return tempo, beat_times
        
    except Exception as e:
        logger.error(f"Error detecting tempo: {e}")
        # Default to 120 BPM and estimated beats
        tempo = 120.0
        beat_duration = 60.0 / tempo
        
        # Get audio duration
        try:
            from pydub import AudioSegment
            audio = AudioSegment.from_file(audio_path)
            duration = len(audio) / 1000.0
        except:
            duration = 180.0  # Default 3 minutes
            
        # Generate beats starting at 3.0s
        num_beats = int((duration - 3.0) / beat_duration)
        beat_times = [3.0 + i * beat_duration for i in range(num_beats)]
        
        logger.info(f"Using default tempo: {tempo:.1f} BPM with {len(beat_times)} beats")
        return tempo, beat_times

def generate_notes_from_patterns(patterns, beat_times, tempo):
    """
    Generate notes using MIDI patterns and detected beats
    
    Args:
        patterns: List of extracted MIDI patterns
        beat_times: List of beat times from audio
        tempo: Detected tempo in BPM
        
    Returns:
        list: Generated notes
    """
    notes = []
    
    # Skip very early beats (before 3.0s)
    start_idx = 0
    while start_idx < len(beat_times) and beat_times[start_idx] < 3.0:
        start_idx += 1
        
    if start_idx >= len(beat_times):
        return []
        
    # Calculate beat duration and measure length
    beat_duration = 60.0 / tempo
    measure_length = beat_duration * 4
    
    # Process beats in measures
    current_measure = 0
    
    for i in range(start_idx, len(beat_times), 4):
        if i + 3 >= len(beat_times):
            break  # Not enough beats for a full measure
            
        # Get first beat of this measure
        measure_start = beat_times[i]
        
        # Choose a pattern (create variations)
        if current_measure % 8 == 0:
            # Every 8 measures, use a special pattern
            pattern_idx = current_measure % len(patterns)
        else:
            # Other measures use patterns that match their position
            pattern_idx = current_measure % len(patterns)
            
        pattern = patterns[pattern_idx]
        
        # Apply the pattern
        for rel_pos, note_type, enemy_type, color1, color2, aux in pattern:
            # Calculate absolute time
            time = measure_start + (rel_pos * measure_length)
            # Format to 2 decimal places like MIDI reference
            time_str = f"{time:.2f}"
            
            # Add the note
            notes.append([time_str, note_type, enemy_type, color1, color2, "", aux])
            
        current_measure += 1
    
    # Sort by time
    notes.sort(key=lambda x: float(x[0]))
    return notes

# Command-line interface
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate notes using MIDI patterns")
    parser.add_argument("audio", help="Path to audio file")
    parser.add_argument("midi", help="Path to MIDI reference CSV")
    parser.add_argument("output", help="Path to save generated notes")
    
    args = parser.parse_args()
    
    if apply_midi_patterns(args.audio, args.midi, args.output):
        print(f"Successfully generated notes at {args.output}")
    else:
        print("Failed to generate notes")