"""
Advanced beat-matching note generator that creates MIDI-like drum patterns
synchronized to the audio's actual beat and tempo.
"""
import os
import csv
import logging
import random
import tempfile
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Try to import audio analysis libraries
try:
    import numpy as np
    import librosa
    AUDIO_ANALYSIS_AVAILABLE = True
except ImportError:
    logger.warning("Audio analysis libraries not available - beat detection will be limited")
    AUDIO_ANALYSIS_AVAILABLE = False

def generate_notes_csv(song_path, template_path, output_path):
    """
    Generate beat-matched notes CSV with MIDI-like characteristics
    
    Args:
        song_path: Path to audio file
        template_path: Path to optional template
        output_path: Where to save the notes.csv
        
    Returns:
        bool: Success or failure
    """
    try:
        logger.info(f"Generating beat-matched notes for {os.path.basename(song_path)}")
        
        # Make sure output directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Check if we can do audio analysis
        if not AUDIO_ANALYSIS_AVAILABLE:
            logger.warning("Advanced audio analysis not available, using estimated tempo")
            return generate_basic_beat_matched_notes(song_path, output_path)
        
        # Load audio file
        y, sr = librosa.load(song_path, sr=None)
        
        # Get song duration
        song_duration = librosa.get_duration(y=y, sr=sr)
        logger.info(f"Song duration: {song_duration:.2f} seconds")
        
        # Analyze tempo and beats using multiple techniques for accuracy
        tempo, beats = detect_beats_accurately(y, sr)
        logger.info(f"Detected tempo: {tempo:.2f} BPM")
        
        # Identify song sections based on audio features
        sections = identify_song_sections(y, sr, tempo)
        logger.info(f"Identified {len(sections)} sections in song")
        
        # Generate beat-matched notes with MIDI-like characteristics
        events = generate_beat_matched_notes(y, sr, tempo, beats, sections, song_duration)
        
        # Write notes to CSV
        success = write_events_to_csv(events, output_path)
        
        # Enhance with micro-timing variations
        if success:
            enhance_with_micro_timing(output_path, tempo)
            
        return success
        
    except Exception as e:
        logger.error(f"Error generating beat-matched notes: {e}", exc_info=True)
        return generate_basic_beat_matched_notes(song_path, output_path)

# Enhanced beat detection with multiple methods
def enhanced_beat_detection(y, sr):
    """Combine multiple beat detection methods for better accuracy"""
    # Method 1: Standard beat tracker
    tempo1, beats1 = librosa.beat.beat_track(y=y, sr=sr, trim=False)
    
    # Method 2: Energy-based beat detection
    onset_env = librosa.onset.onset_strength(y=y, sr=sr)
    tempo2 = librosa.beat.tempo(onset_envelope=onset_env, sr=sr)[0]
    _, beats2 = librosa.beat.beat_track(onset_envelope=onset_env, sr=sr)
    
    # Method 3: Spectral flux for transient detection
    spec_flux = np.diff(librosa.stft(y), axis=1)
    spec_flux = np.maximum(0, spec_flux)
    spec_sum = np.sum(spec_flux, axis=0)
    tempo3, beats3 = librosa.beat.beat_track(onset_envelope=spec_sum, sr=sr)
    
    # Combine results using confidence weighting
    beat_times1 = librosa.frames_to_time(beats1, sr=sr)
    beat_times2 = librosa.frames_to_time(beats2, sr=sr)
    beat_times3 = librosa.frames_to_time(beats3, sr=sr)
    
    # Calculate beat consistency (lower std = more consistent = higher weight)
    std1 = np.std(np.diff(beat_times1)) if len(beat_times1) > 1 else 999
    std2 = np.std(np.diff(beat_times2)) if len(beat_times2) > 1 else 999
    std3 = np.std(np.diff(beat_times3)) if len(beat_times3) > 1 else 999
    
    # Calculate weights (inverse of std, normalized)
    total = (1/std1 + 1/std2 + 1/std3)
    w1 = (1/std1)/total if std1 < 900 else 0
    w2 = (1/std2)/total if std2 < 900 else 0
    w3 = (1/std3)/total if std3 < 900 else 0
    
    # Select tempo using weights
    tempo = tempo1*w1 + tempo2*w2 + tempo3*w3
    
    # Select most consistent beat times
    selected_beats = beat_times1
    if std2 < std1 and std2 < std3:
        selected_beats = beat_times2
    elif std3 < std1 and std3 < std2:
        selected_beats = beat_times3
    
    logger.info(f"Enhanced beat detection: {tempo:.1f} BPM (certainty: {min(std1, std2, std3):.3f})")
    return tempo, librosa.time_to_frames(selected_beats, sr=sr)

def detect_beats_accurately(y, sr):
    """
    Detect beats using multiple methods and validate for accuracy
    
    Returns:
        tuple: (tempo, beat_frames)
    """
    # Method 1: Use librosa's beat tracker
    tempo, beats = librosa.beat.beat_track(y=y, sr=sr, trim=False)
    
    # Method 2: Use dynamic tempo estimation
    onset_env = librosa.onset.onset_strength(y=y, sr=sr)
    dtempo = librosa.beat.tempo(onset_envelope=onset_env, sr=sr)
    
    # Use dynamic tempo if significantly different
    if abs(tempo - dtempo) > 10:
        logger.info(f"Using dynamic tempo {dtempo} instead of {tempo}")
        tempo = dtempo
        
        # Re-track beats with new tempo hint
        beats = librosa.beat.beat_track(y=y, sr=sr, trim=False, start_bpm=tempo)[1]
    
    # Verify beat confidence
    beat_times = librosa.frames_to_time(beats, sr=sr)
    
    # Check if beats are consistent
    if len(beat_times) > 3:
        beat_intervals = np.diff(beat_times)
        beat_consistency = np.std(beat_intervals) / np.mean(beat_intervals)
        
        # If beats are inconsistent, try adjusting
        if beat_consistency > 0.2:  # More than 20% variation
            logger.info(f"Beats have high variation ({beat_consistency:.2f}), adjusting...")
            
            # Try to find a more consistent tempo
            ac = librosa.autocorrelate(onset_env, max_size=sr)
            # Find peaks in autocorrelation
            peaks = librosa.util.peak_pick(ac, 3, 3, 3, 5, 0.5, 10)
            
            if len(peaks) > 0:
                # Convert peaks to BPM
                peak_bpm = 60 * sr / peaks[0:5]
                # Find the peak closest to our tempo estimate
                tempo_idx = np.argmin(np.abs(peak_bpm - tempo))
                new_tempo = peak_bpm[tempo_idx]
                
                # Only update if reasonably close to original
                if 0.66 * tempo <= new_tempo <= 1.5 * tempo:
                    logger.info(f"Adjusted tempo to {new_tempo:.2f} BPM")
                    tempo = new_tempo
                    
                    # Re-track beats with new tempo
                    beats = librosa.beat.beat_track(y=y, sr=sr, trim=False, start_bpm=tempo)[1]
    
    # Final validation
    beat_times = librosa.frames_to_time(beats, sr=sr)
    if len(beat_times) < 10:
        logger.warning("Few beats detected, generating artificial beat grid")
        
        # Create synthetic beat grid based on tempo
        beat_duration = 60.0 / tempo
        duration = librosa.get_duration(y=y, sr=sr)
        beat_times = np.arange(0, duration, beat_duration)
        beats = librosa.time_to_frames(beat_times, sr=sr)
    
    return tempo, beats

def identify_song_sections(y, sr, tempo):
    """
    Identify different sections in the song based on audio features
    
    Returns:
        list: [(start_time, end_time, section_type), ...]
    """
    try:
        # Calculate features for section detection
        
        # 1. Spectral contrast for texture changes
        contrast = np.mean(librosa.feature.spectral_contrast(y=y, sr=sr), axis=0)
        
        # 2. MFCC for timbre changes
        mfcc = np.mean(librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13), axis=0)
        
        # 3. RMS energy for loudness changes
        rms = librosa.feature.rms(y=y)[0]
        
        # 4. Onset strength for rhythmic changes
        onset_env = librosa.onset.onset_strength(y=y, sr=sr)
        
        # Combine features
        features = np.vstack([
            librosa.util.normalize(contrast),
            librosa.util.normalize(np.mean(mfcc, axis=0)),
            librosa.util.normalize(rms)
        ])
        
        # Detect boundaries based on feature changes
        bound_frames = librosa.segment.agglomerative(features, 8)
        bound_times = librosa.frames_to_time(bound_frames, sr=sr)
        
        # Align boundaries to nearest downbeat
        beat_duration = 60.0 / tempo
        measure_duration = beat_duration * 4  # Assume 4/4 time
        
        aligned_bounds = []
        for bound in bound_times:
            # Round to nearest measure
            measure_idx = round(bound / measure_duration)
            aligned_bound = measure_idx * measure_duration
            aligned_bounds.append(aligned_bound)
        
        # Remove duplicates and sort
        aligned_bounds = sorted(set(aligned_bounds))
        
        # Create sections
        sections = []
        for i in range(len(aligned_bounds) - 1):
            start = aligned_bounds[i]
            end = aligned_bounds[i + 1]
            
            # Analyze section characteristics
            section_start_frame = librosa.time_to_frames(start, sr=sr)
            section_end_frame = librosa.time_to_frames(end, sr=sr)
            
            # Calculate section features
            if section_end_frame > section_start_frame:
                section_rms = np.mean(rms[section_start_frame:section_end_frame])
                section_contrast = np.mean(contrast[section_start_frame:section_end_frame])
                section_onsets = np.mean(onset_env[section_start_frame:section_end_frame])
                
                # Classify section type
                if section_rms > np.mean(rms) * 1.2:
                    section_type = "high_intensity"
                elif section_onsets > np.mean(onset_env) * 1.2:
                    section_type = "rhythmic"
                elif section_contrast > np.mean(contrast) * 1.2:
                    section_type = "varied"
                else:
                    section_type = "standard"
                
                sections.append((start, end, section_type))
        
        # If no sections were found or too few, create default sections
        if len(sections) < 3:
            duration = librosa.get_duration(y=y, sr=sr)
            # Create sections of 16 measures each (64 beats in 4/4)
            section_duration = measure_duration * 16
            
            sections = []
            start = 0
            while start < duration:
                end = min(start + section_duration, duration)
                section_type = "standard"
                sections.append((start, end, section_type))
                start = end
        
        return sections
        
    except Exception as e:
        logger.error(f"Error identifying song sections: {e}")
        
        # Create default sections if analysis fails
        duration = librosa.get_duration(y=y, sr=sr)
        beat_duration = 60.0 / tempo
        measure_duration = beat_duration * 4
        section_duration = measure_duration * 16
        
        sections = []
        start = 0
        while start < duration:
            end = min(start + section_duration, duration)
            section_type = "standard"
            sections.append((start, end, section_type))
            start = end
        
        return sections

def generate_beat_matched_notes(y, sr, tempo, beats, sections, song_duration):
    """
    Generate drum notes aligned with the detected beats, including variations
    
    Returns:
        list: [(time, note_type, values), ...]
    """
    beat_times = librosa.frames_to_time(beats, sr=sr)
    
    # Calculate musical time values
    beat_duration = 60.0 / tempo
    measure_duration = beat_duration * 4  # Assume 4/4 time
    eighth_duration = beat_duration / 2
    sixteenth_duration = beat_duration / 4
    
    # Store all drum events
    events = []
    
    # Track measures for pattern variations
    current_measure = 0
    
    # Map section types to patterns
    section_patterns = {
        "standard": "basic_rock",
        "high_intensity": "high_energy",
        "rhythmic": "funk",
        "varied": "complex"
    }
    
    # Process each beat
    for i, beat_time in enumerate(beat_times):
        # Skip very early beats (before typical song start)
        if beat_time < 2.5:
            continue
            
        # Determine which measure and beat within measure we're on
        # In 4/4 time, each measure has 4 beats
        beat_in_measure = i % 4
        if beat_in_measure == 0:
            current_measure += 1
        
        # Find which section we're in
        current_section = None
        section_type = "standard"
        for start, end, type in sections:
            if start <= beat_time < end:
                current_section = (start, end)
                section_type = type
                break
        
        # Get pattern type based on section
        pattern = section_patterns.get(section_type, "basic_rock")
        
        # Add notes based on pattern and position
        add_pattern_notes(events, beat_time, beat_in_measure, current_measure, pattern)
        
        # Add variations for realistic feeling
        if pattern == "basic_rock":
            # Add eighth notes
            events.append((beat_time, "hihat", ["1", "1", "1", "1", "", "6"]))
            events.append((beat_time + eighth_duration, "hihat", ["1", "1", "1", "1", "", "6"]))
        elif pattern == "high_energy":
            # Add sixteenth notes for high energy
            events.append((beat_time, "hihat", ["1", "1", "1", "1", "", "6"]))
            events.append((beat_time + sixteenth_duration, "hihat", ["1", "1", "1", "1", "", "6"]))
            events.append((beat_time + 2*sixteenth_duration, "hihat", ["1", "1", "1", "1", "", "6"]))
            events.append((beat_time + 3*sixteenth_duration, "hihat", ["1", "1", "1", "1", "", "6"]))
        elif pattern == "funk":
            # Add syncopated rhythm
            events.append((beat_time, "hihat", ["1", "1", "1", "1", "", "6"]))
            if beat_in_measure % 2 == 0:  # On beats 1 and 3
                events.append((beat_time + eighth_duration * 0.66, "hihat", ["1", "1", "1", "1", "", "6"]))
            else:
                events.append((beat_time + eighth_duration * 0.75, "hihat", ["1", "1", "1", "1", "", "6"]))
        
        # Add fills at the end of sections
        if current_section:
            section_start, section_end, _ = current_section
            # If we're near the end of a section (within 2 measures)
            if section_end - beat_time < measure_duration * 2 and beat_time > section_end - measure_duration:
                # Add a fill if we're at the right beat
                if beat_in_measure == 2:  # On beat 3
                    add_drum_fill(events, beat_time, beat_duration, section_end)
    
    # Sort all events by time
    events.sort(key=lambda x: x[0])
    
    # Add section transitions with crash cymbals
    add_section_transitions(events, sections)
    
    # Add random variations for humanization
    add_random_variations(events, sixteenth_duration)
    
    return events

def add_pattern_notes(events, beat_time, beat_in_measure, current_measure, pattern):
    """Add notes based on the selected pattern and beat position"""
    
    # Basic rock pattern (kick on 1,3, snare on 2,4)
    if pattern == "basic_rock":
        if beat_in_measure == 0 or beat_in_measure == 2:  # Beats 1 and 3
            events.append((beat_time, "kick", ["1", "2", "2", "1", "", "7"]))
        else:  # Beats 2 and 4
            events.append((beat_time, "snare", ["1", "2", "2", "1", "", "7"]))
            
    # High energy pattern (kick on every beat, snare on 2,4)
    elif pattern == "high_energy":
        events.append((beat_time, "kick", ["1", "2", "2", "1", "", "7"]))
        if beat_in_measure == 1 or beat_in_measure == 3:  # Beats 2 and 4
            events.append((beat_time, "snare", ["1", "2", "2", "1", "", "7"]))
    
    # Funk pattern (syncopated kicks, snare on 2,4)
    elif pattern == "funk":
        if beat_in_measure == 0:  # Beat 1
            events.append((beat_time, "kick", ["1", "2", "2", "1", "", "7"]))
        elif beat_in_measure == 1 or beat_in_measure == 3:  # Beats 2 and 4
            events.append((beat_time, "snare", ["1", "2", "2", "1", "", "7"]))
        elif beat_in_measure == 2:  # Beat 3
            # Syncopation - sometimes skip the kick on 3
            if current_measure % 2 == 1:
                events.append((beat_time, "kick", ["1", "2", "2", "1", "", "7"]))
    
    # Complex pattern (varied kicks, snare on 2,4)
    elif pattern == "complex":
        if beat_in_measure == 0:  # Beat 1
            events.append((beat_time, "kick", ["1", "2", "2", "1", "", "7"]))
        elif beat_in_measure == 1:  # Beat 2
            events.append((beat_time, "snare", ["1", "2", "2", "1", "", "7"]))
        elif beat_in_measure == 2:  # Beat 3
            # Complex kick pattern based on measure number
            if current_measure % 4 == 0 or current_measure % 4 == 2:
                events.append((beat_time, "kick", ["1", "2", "2", "1", "", "7"]))
        elif beat_in_measure == 3:  # Beat 4
            events.append((beat_time, "snare", ["1", "2", "2", "1", "", "7"]))
            # Sometimes add an extra kick right before beat 1
            if current_measure % 4 == 3:
                events.append((beat_time + 0.9 * 60/tempo, "kick", ["1", "2", "2", "1", "", "7"]))
    
    # Add crash cymbal at section beginnings and every 8 measures
    if beat_in_measure == 0 and current_measure % 8 == 1:
        events.append((beat_time, "crash", ["2", "5", "6", "1", "", "5"]))

def add_drum_fill(events, start_time, beat_duration, end_time):
    """Add a drum fill leading to a section transition"""
    # Determine fill length and density
    fill_duration = min(beat_duration * 2, end_time - start_time)
    
    # Different fill types
    fill_types = ["basic", "dense", "syncopated", "tom_based"]
    fill_type = random.choice(fill_types)
    
    if fill_type == "basic":
        # Simple fill - eighth note snares
        for i in range(4):
            time = start_time + i * beat_duration / 2
            events.append((time, "snare", ["1", "2", "2", "1", "", "7"]))
    
    elif fill_type == "dense":
        # Sixteenth notes
        for i in range(8):
            time = start_time + i * beat_duration / 4
            if i % 2 == 0:
                events.append((time, "snare", ["1", "2", "2", "1", "", "7"]))
            else:
                events.append((time, "kick", ["1", "2", "2", "1", "", "7"]))
    
    elif fill_type == "syncopated":
        # Triplet feel
        for i in range(6):
            time = start_time + i * beat_duration / 3
            events.append((time, "snare", ["1", "2", "2", "1", "", "7"]))
    
    elif fill_type == "tom_based":
        # Tom fill using different colors for toms
        tom_colors = [["1", "3", "3", "1", "", "7"], 
                      ["1", "3", "4", "1", "", "7"],
                      ["1", "4", "4", "1", "", "7"]]
        
        for i in range(4):
            time = start_time + i * beat_duration / 2
            tom = tom_colors[i % len(tom_colors)]
            events.append((time, "tom", tom))
    
    # Always end with a crash at the section transition
    events.append((end_time, "crash", ["2", "5", "6", "1", "", "5"]))

def add_section_transitions(events, sections):
    """Add crash cymbals and transition elements at section boundaries"""
    for i, (start, end, section_type) in enumerate(sections):
        if i > 0:  # Skip first section start
            # Add crash at section start
            existing_crash = False
            for time, note_type, values in events:
                if abs(time - start) < 0.1 and note_type == "crash":
                    existing_crash = True
                    break
            
            if not existing_crash:
                events.append((start, "crash", ["2", "5", "6", "1", "", "5"]))

def add_random_variations(events, sixteenth_duration):
    """Add humanization and random variations to make patterns less mechanical"""
    # Group events by approximate time points (within 30ms window)
    time_groups = {}
    for time, note_type, values in events:
        # Round time to nearest 10ms for grouping
        rounded_time = round(time * 100) / 100
        if rounded_time not in time_groups:
            time_groups[rounded_time] = []
        time_groups[rounded_time].append((time, note_type, values))
    
    # Add ghost notes and extra hits
    extra_notes = []
    for time_group, notes in time_groups.items():
        # Add ghost note (soft snare hit) before some snare hits
        for time, note_type, values in notes:
            if note_type == "snare" and random.random() < 0.15:
                # Add ghost note before main snare
                ghost_time = time - sixteenth_duration * random.uniform(0.8, 1.2)
                ghost_values = ["1", "2", "2", "1", "", "7"]  # Using same values but will be quieter
                extra_notes.append((ghost_time, "ghost_snare", ghost_values))
            
            # Add double kick
            if note_type == "kick" and random.random() < 0.1:
                # Add quick double kick
                second_kick_time = time + sixteenth_duration * random.uniform(0.4, 0.6)
                extra_notes.append((second_kick_time, "kick", ["1", "2", "2", "1", "", "7"]))
    
    # Add extra notes to events
    for time, note_type, values in extra_notes:
        events.append((time, note_type, values))
    
    # Sort all events
    events.sort(key=lambda x: x[0])
    
    return events

def write_events_to_csv(events, output_path):
    """Write events to the CSV format needed by the game"""
    try:
        with open(output_path, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["Time [s]", "Enemy Type", "Aux Color 1", "Aux Color 2", "Nº Enemies", "interval", "Aux"])
            
            # Track previous time to ensure proper spacing
            prev_time = 0
            
            for time, note_type, values in events:
                # Ensure minimum time spacing of 50ms
                if prev_time > 0 and time - prev_time < 0.05:
                    time = prev_time + 0.05
                
                # Format time to 2 decimal places
                formatted_time = f"{time:.2f}"
                
                # Write the row
                writer.writerow([formatted_time] + values)
                
                prev_time = time
        
        logger.info(f"Wrote {len(events)} notes to {output_path}")
        return True
        
    except Exception as e:
        logger.error(f"Error writing events to CSV: {e}")
        return False

def enhance_with_micro_timing(output_path, tempo):
    """
    Apply micro-timing variations for human feel
    """
    try:
        # Read all notes
        all_rows = []
        with open(output_path, 'r') as f:
            reader = csv.reader(f)
            header = next(reader)
            all_rows = list(reader)
        
        # Calculate swing factor based on tempo
        # Faster tempos usually have less swing
        if tempo < 100:
            swing_factor = 0.2  # More swing for slower tempos
        elif tempo < 130:
            swing_factor = 0.1  # Medium swing for medium tempos
        else:
            swing_factor = 0.05  # Less swing for faster tempos
        
        # Apply micro-timing variations
        for i, row in enumerate(all_rows):
            if len(row) > 0:
                try:
                    time_val = float(row[0])
                    
                    # Skip very early notes (intro)
                    if time_val < 3.0:
                        continue
                    
                    # Apply micro timing
                    variation = random.uniform(-0.03, 0.03)  # ±30ms random variation
                    
                    # Apply swing feel to offbeats
                    beat_position = (time_val * tempo / 60) % 1.0
                    if 0.4 < beat_position < 0.6:  # Close to offbeat eighth
                        variation += swing_factor  # Push offbeats later for swing
                    
                    new_time = time_val + variation
                    row[0] = f"{new_time:.2f}"
                except (ValueError, IndexError):
                    pass
        
        # Sort by time
        all_rows.sort(key=lambda row: float(row[0]) if row and len(row) > 0 else 0)
        
        # Make sure no notes are too close together
        for i in range(1, len(all_rows)):
            if len(all_rows[i]) > 0 and len(all_rows[i-1]) > 0:
                current_time = float(all_rows[i][0])
                prev_time = float(all_rows[i-1][0])
                
                # If notes are too close, shift the current note
                if current_time - prev_time < 0.05:  # 50ms minimum
                    new_time = prev_time + 0.05
                    all_rows[i][0] = f"{new_time:.2f}"
        
        # Write back
        with open(output_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(header)
            writer.writerows(all_rows)
        
        logger.info(f"Applied micro-timing variations to {len(all_rows)} notes")
        return True
    
    except Exception as e:
        logger.error(f"Error applying micro-timing: {e}")
        return False

def generate_basic_beat_matched_notes(song_path, output_path):
    """
    Fallback generator when audio analysis fails
    """
    try:
        logger.info("Using basic beat matching without audio analysis")
        
        # Try to get some basic info about the song
        song_duration = 180.0  # Default 3 minutes
        
        try:
            import subprocess
            from mutagen.mp3 import MP3
            from mutagen.oggvorbis import OggVorbis
            
            # Try to get duration based on file type
            if song_path.lower().endswith('.mp3'):
                audio = MP3(song_path)
                song_duration = audio.info.length
            elif song_path.lower().endswith('.ogg'):
                audio = OggVorbis(song_path)
                song_duration = audio.info.length
        except:
            pass
        
        # Assume 120 BPM if we can't analyze
        tempo = 120.0
        
        # Generate a simple beat-matched pattern
        with open(output_path, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["Time [s]", "Enemy Type", "Aux Color 1", "Aux Color 2", "Nº Enemies", "interval", "Aux"])
            
            # Calculate timing 
            beat_duration = 60.0 / tempo  # seconds per beat
            
            # Start at 3 seconds (typical offset)
            current_time = 3.0
            end_time = min(song_duration - 5.0, 180.0)  # Stop 5 seconds before end
            
            # Keep track of measure for pattern variation
            measure = 0
            beat_in_measure = 0
            
            # Generate pattern
            while current_time < end_time:
                # Every 4 beats starts a new measure
                if beat_in_measure == 0:
                    measure += 1
                
                # Add crash every 8 measures on beat 1
                if beat_in_measure == 0 and measure % 8 == 1:
                    writer.writerow([f"{current_time:.2f}", "2", "5", "6", "1", "", "5"])
                
                # Basic rock pattern
                if beat_in_measure == 0 or beat_in_measure == 2:  # Beats 1 & 3
                    # Kick drum
                    writer.writerow([f"{current_time:.2f}", "1", "2", "2", "1", "", "7"])
                else:  # Beats 2 & 4
                    # Snare drum
                    writer.writerow([f"{current_time:.2f}", "1", "2", "2", "1", "", "7"])
                
                # Add hihat on every beat and eighth notes
                writer.writerow([f"{current_time:.2f}", "1", "1", "1", "1", "", "6"])
                writer.writerow([f"{current_time+beat_duration/2:.2f}", "1", "1", "1", "1", "", "6"])
                
                # Update time and beat counter
                current_time += beat_duration
                beat_in_measure = (beat_in_measure + 1) % 4
            
        return True
        
    except Exception as e:
        logger.error(f"Error in basic beat matcher: {e}")
        return False

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate beat-matched drum notes")
    parser.add_argument("song_path", help="Path to audio file")
    parser.add_argument("output_path", help="Path for output CSV file")
    
    args = parser.parse_args()
    
    success = generate_notes_csv(args.song_path, None, args.output_path)
    
    if success:
        print(f"Successfully generated notes at {args.output_path}")
    else:
        print("Failed to generate notes")