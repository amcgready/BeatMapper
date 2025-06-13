"""
MIDI-aligned beat matching generator for precise rhythm game note generation.
Prioritizes exact alignment with detected beats and applies common drum patterns.
"""
import os
import csv
import logging
import random
import math
import numpy as np
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Try to import optional libraries
try:
    import librosa
    LIBROSA_AVAILABLE = True
except ImportError:
    logger.warning("librosa library not available, falling back to basic beat detection")
    LIBROSA_AVAILABLE = False

# Note type constants for game
NOTE_KICK = ["1", "1", "1", "1", "", "6"]
NOTE_SNARE = ["1", "2", "2", "1", "", "7"]
NOTE_HIHAT = ["1", "3", "3", "1", "", "8"]
NOTE_CRASH = ["2", "5", "6", "1", "", "5"]
NOTE_TOM = ["1", "4", "4", "1", "", "9"]

def generate_notes_csv(song_path, template_path, output_path, midi_reference=None):
    """
    Generate a notes.csv file with precise beat-matched MIDI-like patterns
    
    Args:
        song_path: Path to the audio file
        template_path: Path to a template file (optional)
        output_path: Path to save the notes.csv file
        midi_reference: Path to a MIDI reference file (optional)
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Extract filename without extension for logging
        filename = Path(song_path).stem
        logger.info(f"Generating MIDI-aligned beat-matched notes for {filename}")
        
        # Create output directory if it doesn't exist
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Step 1: Load song and detect beats
        tempo, beat_times, duration = detect_beats_and_tempo(song_path)
        
        # Step 2: Generate notes based on beats and tempo
        notes = create_midi_style_pattern(beat_times, tempo, duration)
        
        # Step 3: Write notes to CSV
        with open(output_path, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["time", "note_type", "enemy_type", "color1", "color2", "interval", "aux"])
            writer.writerows(notes)
        
        logger.info(f"Generated {len(notes)} MIDI-aligned notes at {output_path}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to generate MIDI-aligned notes: {e}")
        return False

def detect_beats_and_tempo(song_path):
    """
    Detect beats and tempo from an audio file with high precision
    
    Returns:
        tuple: (tempo, beat_times, duration)
    """
    if LIBROSA_AVAILABLE:
        try:
            # Load audio
            y, sr = librosa.load(song_path, sr=None)
            duration = librosa.get_duration(y=y, sr=sr)
            
            # Extract percussive component for better beat detection
            y_harmonic, y_percussive = librosa.effects.hpss(y)
            
            # Create onset envelope with stronger emphasis on transients
            onset_env = librosa.onset.onset_strength(
                y=y_percussive, 
                sr=sr,
                aggregate=np.max,    # Use max aggregation for sharper peaks
                hop_length=512,      # Higher time precision
                fmax=8000            # Extend frequency range for cymbals
            )
            
            # Detect tempo with higher accuracy
            tempo = librosa.beat.tempo(
                onset_envelope=onset_env,
                sr=sr,
                hop_length=512,
                aggregate=None
            )[0]
            
            # Round tempo to nearest 0.5 BPM (typical in MIDI)
            tempo = round(tempo * 2) / 2
            
            # Detect beats using dynamic programming with the tempo constraint
            _, beats = librosa.beat.beat_track(
                onset_envelope=onset_env,
                sr=sr,
                hop_length=512,
                start_bpm=tempo,
                tightness=300,       # Stronger adherence to start_bpm
                trim=False
            )
            
            # Convert frames to time
            beat_times = librosa.frames_to_time(beats, sr=sr, hop_length=512)
            
            # Snap beats to exact tempo grid
            beat_times = snap_beats_to_grid(beat_times, tempo)
            
            logger.info(f"Detected tempo: {tempo:.1f} BPM with {len(beat_times)} beats")
            return tempo, beat_times, duration
            
        except Exception as e:
            logger.warning(f"Error in librosa beat detection: {e}")
            # Fall back to estimated beats
            
    # Calculate duration if possible or use default
    duration = 180.0  # Default 3 minutes
    try:
        from pydub import AudioSegment
        audio = AudioSegment.from_file(song_path)
        duration = len(audio) / 1000.0
        logger.info(f"Got duration from pydub: {duration}s")
    except:
        logger.warning("Couldn't determine audio duration, using default")
    
    # Use default 120 BPM
    tempo = 120.0
    
    # Generate evenly spaced beats
    beat_duration = 60.0 / tempo
    num_beats = int(duration / beat_duration) - 6  # Leave margin at end
    beat_times = [3.0 + (i * beat_duration) for i in range(num_beats)]  # Start at 3.0s
    
    logger.info(f"Using generated beats at {tempo:.1f} BPM ({len(beat_times)} beats)")
    return tempo, np.array(beat_times), duration

def snap_beats_to_grid(beat_times, tempo):
    """Snap detected beats to a perfect tempo grid to ensure rhythmic accuracy"""
    beat_duration = 60.0 / tempo
    
    # Find first beat after 3 seconds (standard start time)
    start_idx = 0
    while start_idx < len(beat_times) and beat_times[start_idx] < 3.0:
        start_idx += 1
    
    if start_idx >= len(beat_times):
        return beat_times
        
    # Create a perfect grid starting at the first beat after 3.0s
    first_beat_time = beat_times[start_idx]
    perfect_grid = []
    
    # Generate perfect grid backwards to catch any early beats
    current_time = first_beat_time
    while current_time >= 0:
        perfect_grid.insert(0, current_time)
        current_time -= beat_duration
    
    # Generate perfect grid forward
    current_time = first_beat_time + beat_duration
    while current_time <= beat_times[-1] + beat_duration:
        perfect_grid.append(current_time)
        current_time += beat_duration
        
    # Snap each detected beat to nearest grid position
    snapped_beats = []
    for beat in beat_times:
        # Find closest grid position
        closest_idx = np.argmin(np.abs(np.array(perfect_grid) - beat))
        snapped_beats.append(perfect_grid[closest_idx])
    
    return np.array(snapped_beats)

def create_midi_style_pattern(beat_times, tempo, duration):
    """
    Create a MIDI-style drum pattern based on detected beats
    
    Args:
        beat_times: Array of beat times
        tempo: Tempo in BPM
        duration: Song duration in seconds
        
    Returns:
        list: List of note rows for CSV
    """
    notes = []
    
    # Calculate beat duration and measure length (assuming 4/4 time)
    beat_duration = 60.0 / tempo
    beats_per_measure = 4
    measure_duration = beat_duration * beats_per_measure
    
    # Determine structure
    intro_measures = 4
    verse_measures = 8
    chorus_measures = 8
    bridge_measures = 4
    outro_measures = 4
    
    # Calculate number of measures total
    total_measures = int(duration / measure_duration)
    
    # Create song structure (typical arrangement)
    song_structure = []
    current_measure = 0
    
    # Intro
    for i in range(min(intro_measures, total_measures - current_measure)):
        song_structure.append(("intro", current_measure))
        current_measure += 1
        
    # Verse 1
    for i in range(min(verse_measures, total_measures - current_measure)):
        song_structure.append(("verse", current_measure))
        current_measure += 1
        
    # Chorus 1
    for i in range(min(chorus_measures, total_measures - current_measure)):
        song_structure.append(("chorus", current_measure))
        current_measure += 1
        
    # Verse 2
    for i in range(min(verse_measures, total_measures - current_measure)):
        song_structure.append(("verse", current_measure))
        current_measure += 1
        
    # Chorus 2
    for i in range(min(chorus_measures, total_measures - current_measure)):
        song_structure.append(("chorus", current_measure))
        current_measure += 1
        
    # Bridge
    for i in range(min(bridge_measures, total_measures - current_measure)):
        song_structure.append(("bridge", current_measure))
        current_measure += 1
        
    # Final Chorus
    for i in range(min(chorus_measures, total_measures - current_measure)):
        song_structure.append(("chorus", current_measure))
        current_measure += 1
        
    # Outro
    for i in range(min(outro_measures, total_measures - current_measure)):
        song_structure.append(("outro", current_measure))
        current_measure += 1
        
    # Fill remaining measures
    while current_measure < total_measures:
        song_structure.append(("verse", current_measure))
        current_measure += 1
        
    # Process each beat
    for i, beat_time in enumerate(beat_times):
        # Calculate measure and beat in measure
        measure = i // beats_per_measure
        beat_in_measure = i % beats_per_measure
        
        # Get section type for this measure
        section_type = "verse"  # Default
        measure_index = None
        
        for section, m_idx in song_structure:
            if m_idx == measure:
                section_type = section
                measure_index = m_idx
                break
                
        # Apply appropriate pattern based on section
        apply_pattern_at_beat(notes, beat_time, beat_in_measure, beat_duration, 
                             section_type, measure, measure_index)
        
        # Add eighth notes between beats (for hi-hats)
        if i < len(beat_times) - 1:
            next_beat = beat_times[i+1]
            eighth_note = (beat_time + next_beat) / 2
            
            # Only add if reasonable spacing (avoid odd time signatures)
            if next_beat - beat_time > beat_duration * 0.7:
                # Usually hi-hats on eighth notes
                notes.append([f"{eighth_note:.2f}"] + NOTE_HIHAT)
    
    # Add fills at appropriate positions
    notes = add_drum_fills(notes, beat_times, tempo, song_structure)
    
    # Sort by time
    notes.sort(key=lambda x: float(x[0]))
    
    # Add micro-timing variations to make it feel more human
    notes = add_human_timing(notes)
    
    return notes

def apply_pattern_at_beat(notes, beat_time, beat_in_measure, beat_duration, section_type, measure, measure_index):
    """Apply the appropriate pattern at the given beat position"""
    
    # Format beat time to 2 decimal places
    beat_time_str = f"{beat_time:.2f}"
    
    # Always add crash at the start of certain sections
    if beat_in_measure == 0:
        if section_type in ["intro", "chorus"] or measure % 8 == 0:
            notes.append([beat_time_str] + NOTE_CRASH)
    
    # Add notes based on common MIDI patterns
    if section_type == "intro":
        # Simpler pattern for intro
        if beat_in_measure == 0:  # Beat 1
            notes.append([beat_time_str] + NOTE_KICK)
            notes.append([beat_time_str] + NOTE_HIHAT)
        elif beat_in_measure == 1:  # Beat 2
            notes.append([beat_time_str] + NOTE_SNARE)
            notes.append([beat_time_str] + NOTE_HIHAT)
        elif beat_in_measure == 2:  # Beat 3
            notes.append([beat_time_str] + NOTE_KICK)
            notes.append([beat_time_str] + NOTE_HIHAT)
        else:  # Beat 4
            notes.append([beat_time_str] + NOTE_SNARE)
            notes.append([beat_time_str] + NOTE_HIHAT)
    
    elif section_type == "verse":
        # Standard rock beat with some variations
        if beat_in_measure == 0:  # Beat 1
            notes.append([beat_time_str] + NOTE_KICK)
            notes.append([beat_time_str] + NOTE_HIHAT)
            # Occasional double kick
            if measure % 4 == 2:
                eighth_note = beat_time + beat_duration * 0.25
                notes.append([f"{eighth_note:.2f}"] + NOTE_KICK)
        elif beat_in_measure == 1:  # Beat 2
            notes.append([beat_time_str] + NOTE_SNARE)
            notes.append([beat_time_str] + NOTE_HIHAT)
            # Ghost note occasionally
            if measure % 4 == 3:
                eighth_note = beat_time + beat_duration * 0.25
                notes.append([f"{eighth_note:.2f}"] + NOTE_SNARE)
        elif beat_in_measure == 2:  # Beat 3
            notes.append([beat_time_str] + NOTE_KICK)
            notes.append([beat_time_str] + NOTE_HIHAT)
        else:  # Beat 4
            notes.append([beat_time_str] + NOTE_SNARE)
            notes.append([beat_time_str] + NOTE_HIHAT)
            # Occasional syncopation
            if measure % 4 == 0:
                eighth_note = beat_time + beat_duration * 0.75
                notes.append([f"{eighth_note:.2f}"] + NOTE_KICK)
    
    elif section_type == "chorus":
        # More energetic pattern for chorus
        if beat_in_measure == 0:  # Beat 1
            notes.append([beat_time_str] + NOTE_KICK)
            notes.append([beat_time_str] + NOTE_HIHAT)
            if measure % 2 == 0:
                notes.append([beat_time_str] + NOTE_CRASH)
        elif beat_in_measure == 1:  # Beat 2
            notes.append([beat_time_str] + NOTE_SNARE)
            notes.append([beat_time_str] + NOTE_HIHAT)
            # Add double snare occasionally
            if measure % 4 == 1:
                notes.append([beat_time_str] + NOTE_SNARE)
        elif beat_in_measure == 2:  # Beat 3
            notes.append([beat_time_str] + NOTE_KICK)
            notes.append([beat_time_str] + NOTE_HIHAT)
        else:  # Beat 4
            notes.append([beat_time_str] + NOTE_SNARE)
            notes.append([beat_time_str] + NOTE_HIHAT)
            # Sometimes add kick on last eighth note
            if measure % 2 == 1:
                eighth_note = beat_time + beat_duration * 0.5
                notes.append([f"{eighth_note:.2f}"] + NOTE_KICK)
    
    elif section_type == "bridge":
        # Distinctive pattern for bridge
        if beat_in_measure == 0:  # Beat 1
            notes.append([beat_time_str] + NOTE_KICK)
            notes.append([beat_time_str] + NOTE_SNARE)
        elif beat_in_measure == 1:  # Beat 2
            notes.append([beat_time_str] + NOTE_KICK)
            notes.append([beat_time_str] + NOTE_SNARE)
        elif beat_in_measure == 2:  # Beat 3
            notes.append([beat_time_str] + NOTE_KICK)
            notes.append([beat_time_str] + NOTE_SNARE)
        else:  # Beat 4
            notes.append([beat_time_str] + NOTE_KICK)
            notes.append([beat_time_str] + NOTE_SNARE)
            # Lead-in to next section
            if measure % 4 == 3:
                notes.append([beat_time_str] + NOTE_CRASH)
    
    else:  # outro or default
        # Simpler pattern again
        if beat_in_measure == 0:  # Beat 1
            notes.append([beat_time_str] + NOTE_KICK)
            notes.append([beat_time_str] + NOTE_HIHAT)
        elif beat_in_measure == 1:  # Beat 2
            notes.append([beat_time_str] + NOTE_SNARE)
            notes.append([beat_time_str] + NOTE_HIHAT)
        elif beat_in_measure == 2:  # Beat 3
            notes.append([beat_time_str] + NOTE_KICK)
            notes.append([beat_time_str] + NOTE_HIHAT)
        else:  # Beat 4
            notes.append([beat_time_str] + NOTE_SNARE)
            notes.append([beat_time_str] + NOTE_HIHAT)

def add_drum_fills(notes, beat_times, tempo, song_structure):
    """Add drum fills at appropriate positions in the song"""
    # Beat duration
    beat_duration = 60.0 / tempo
    
    # Identify fill locations (typically end of 4 or 8 bar phrases)
    fill_locations = []
    
    for i in range(len(song_structure)-1):
        current_section, current_measure = song_structure[i]
        next_section, next_measure = song_structure[i+1]
        
        # Add fill at section transitions
        if current_section != next_section:
            fill_locations.append(current_measure)
        
        # Add fills within longer sections
        elif current_section == next_section and current_measure % 4 == 3:
            # Add fill every 4 bars in verses and choruses
            if current_section in ["verse", "chorus"]:
                fill_locations.append(current_measure)
    
    # Define some typical fills
    fills = [
        # Simple snare fill (4 16th notes)
        [
            (0.00, NOTE_SNARE),
            (0.25, NOTE_SNARE),
            (0.50, NOTE_SNARE),
            (0.75, NOTE_SNARE)
        ],
        # Tom fill
        [
            (0.00, NOTE_KICK),
            (0.25, NOTE_TOM),
            (0.50, NOTE_TOM),
            (0.75, NOTE_SNARE)
        ],
        # Syncopated fill
        [
            (0.00, NOTE_SNARE),
            (0.33, NOTE_SNARE),
            (0.66, NOTE_SNARE)
        ],
        # Double-time fill
        [
            (0.00, NOTE_SNARE),
            (0.125, NOTE_SNARE),
            (0.25, NOTE_SNARE),
            (0.375, NOTE_SNARE),
            (0.50, NOTE_SNARE),
            (0.625, NOTE_SNARE),
            (0.75, NOTE_SNARE),
            (0.875, NOTE_SNARE)
        ],
    ]
    
    # Add fills
    for fill_measure in fill_locations:
        # Find the last beat of the fill measure
        fill_beat_idx = (fill_measure + 1) * 4 - 1
        
        if fill_beat_idx < len(beat_times):
            fill_start_time = beat_times[fill_beat_idx]
            
            # Choose a fill
            fill = random.choice(fills)
            
            # Apply the fill
            for offset, note_type in fill:
                note_time = fill_start_time + (offset * beat_duration)
                notes.append([f"{note_time:.2f}"] + note_type)
            
            # Add crash on downbeat after fill
            if fill_beat_idx + 1 < len(beat_times):
                downbeat_time = beat_times[fill_beat_idx + 1]
                notes.append([f"{downbeat_time:.2f}"] + NOTE_CRASH)
    
    return notes

def add_human_timing(notes):
    """Add subtle timing variations to make the pattern feel more human"""
    # Maximum variation in seconds
    max_variation = 0.02  # 20ms
    
    varied_notes = []
    
    for note in notes:
        time_str = note[0]
        time_val = float(time_str)
        
        # Add subtle random variation
        variation = random.uniform(-max_variation, max_variation)
        varied_time = time_val + variation
        
        # Ensure we don't go negative
        varied_time = max(0, varied_time)
        
        # Format to 2 decimal places like the MIDI reference
        varied_note = note.copy()
        varied_note[0] = f"{varied_time:.2f}"
        varied_notes.append(varied_note)
    
    # Sort by time
    varied_notes.sort(key=lambda x: float(x[0]))
    
    # Make sure no two notes are too close together
    min_spacing = 0.03  # 30ms minimum spacing
    for i in range(1, len(varied_notes)):
        curr_time = float(varied_notes[i][0])
        prev_time = float(varied_notes[i-1][0])
        
        if curr_time - prev_time < min_spacing:
            # Just use the same time as the previous note for simultaneous hits
            varied_notes[i][0] = varied_notes[i-1][0]
    
    return varied_notes

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate MIDI-aligned beat-matched notes")
    parser.add_argument("song_path", help="Path to audio file")
    parser.add_argument("output_path", help="Path to save notes.csv")
    parser.add_argument("--template", help="Optional template file")
    parser.add_argument("--midi-ref", help="Optional MIDI reference file")
    
    args = parser.parse_args()
    
    if generate_notes_csv(args.song_path, args.template, args.output_path, args.midi_ref):
        print(f"Successfully generated notes at {args.output_path}")
    else:
        print("Failed to generate notes")