"""
High-density notes generator for creating intense, challenging patterns.
Produces significantly more notes than the standard generator.
"""
import os
import csv
import sys
import logging
import warnings
import random
from pathlib import Path

try:
    import numpy as np
except ImportError:
    logging.warning("NumPy not available - falling back to basic pattern")
    # Define minimal numpy functionality needed
    class NumpyStub:
        def ceil(self, x):
            return int(x) + (1 if x > int(x) else 0)
        
        def mean(self, x, *args, **kwargs):
            if not x:
                return 0
            return sum(x) / len(x)
        
        def where(self, condition, x, y):
            # Simple implementation of np.where
            result = []
            for i in range(len(condition)):
                if condition[i]:
                    result.append(x[i] if hasattr(x, '__getitem__') else x)
                else:
                    result.append(y[i] if hasattr(y, '__getitem__') else y)
            return result
            
    np = NumpyStub()

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def generate_notes_csv(song_path, template_path, output_path):
    """Generate extremely dense notes based on minimal filtering and pattern infilling"""
    try:
        logger.info(f"Generating HIGH DENSITY drum notes for {os.path.basename(song_path)}")
        
        # Try to use librosa for analysis
        try:
            import librosa
            
            # Suppress warnings from librosa
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                
                # Load the audio file
                y, sr = librosa.load(song_path, sr=None)
                
                # Get song duration
                song_duration = librosa.get_duration(y=y, sr=sr)
                logger.info(f"Song duration: {song_duration:.2f} seconds")
                
                # Detect the tempo
                tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
                logger.info(f"Detected tempo: {tempo:.2f} BPM")
                
                # Generate high-density events
                events = generate_high_density_events(y, sr, tempo, song_duration)
                
                # Write these events to CSV
                success = write_high_density_notes_csv(events, song_duration, tempo, output_path)
                
                if success:
                    logger.info(f"Successfully generated high-density notes.csv at {output_path}")
                    return True
                
        except ImportError:
            logger.warning("Could not import librosa, falling back to dense pattern")
        except Exception as e:
            logger.error(f"Error with analysis: {str(e)}")
        
        # Fallback to dense pattern
        return generate_dense_pattern_csv(song_path, output_path)
        
    except Exception as e:
        logger.error(f"Failed to generate high-density notes.csv: {str(e)}")
        return False

def generate_high_density_events(y, sr, tempo, song_duration):
    """Generate extremely dense note events using multiple detection methods"""
    
    events = []
    
    # Calculate time between 16th notes (common in drum patterns)
    beat_duration = 60 / tempo
    sixteenth_duration = beat_duration / 4
    
    try:
        import librosa
        
        # 1. EXTREMELY LOW THRESHOLD ONSET DETECTION
        # Extract percussive component
        y_harmonic, y_percussive = librosa.effects.hpss(y)
        
        # Use an absurdly low threshold to catch nearly everything
        onset_env = librosa.onset.onset_strength(y=y_percussive, sr=sr)
        
        # Use multiple thresholds to get different levels of sensitivity
        for threshold in [0.15, 0.25, 0.4]:  # From extremely sensitive to more moderate
            onset_frames = librosa.onset.onset_detect(
                onset_envelope=onset_env,
                sr=sr,
                threshold=threshold,
                pre_max=0.02*sr//512,  # Shorter pre_max for more sensitivity
                post_max=0.02*sr//512, # Shorter post_max for more sensitivity
                pre_avg=0.05*sr//512,  # Shorter pre_avg for more sensitivity
                post_avg=0.05*sr//512  # Shorter post_avg for more sensitivity
            )
            
            onset_times = librosa.frames_to_time(onset_frames, sr=sr)
            
            # Add these onsets to our events, with different types based on threshold
            for t in onset_times:
                # Low threshold = likely hihat or subtle sound
                if threshold == 0.15:
                    events.append((t, 'hihat'))
                # Medium threshold = likely snare or mid-level hit
                elif threshold == 0.25:
                    events.append((t, 'snare'))
                # Higher threshold = likely kick or strong hit
                else:
                    events.append((t, 'kick'))
        
        # 2. MULTI-BAND DETECTION FOR DIFFERENT DRUM ELEMENTS
        # Define frequency bands for different drum elements
        bands = [
            (20, 150),     # Kick drum
            (150, 300),    # Low toms
            (300, 800),    # Snare
            (800, 1500),   # Mid toms
            (1500, 4000),  # Hi-hats
            (4000, 8000),  # Crashes/rides
        ]
        
        # For each band, detect onsets and add them
        for i, (low_freq, high_freq) in enumerate(bands):
            # Filter to this frequency band
            y_band = librosa.effects.remix(y, intervals=librosa.frequency_bands.frequency_filter(
                y, sr, low_freq, high_freq))
            
            # Get onsets in this band with appropriate threshold
            # Lower bands (kick) need higher thresholds
            if i == 0:
                threshold = 0.3
            elif i == 1 or i == 2:
                threshold = 0.25
            else:
                threshold = 0.2
                
            # Detect onsets
            band_onset_env = librosa.onset.onset_strength(y=y_band, sr=sr)
            band_onset_frames = librosa.onset.onset_detect(
                onset_envelope=band_onset_env,
                sr=sr,
                threshold=threshold
            )
            
            band_onset_times = librosa.frames_to_time(band_onset_frames, sr=sr)
            
            # Map band index to drum element type
            if i == 0:
                element_type = 'kick'
            elif i == 1:
                element_type = 'low_tom'
            elif i == 2:
                element_type = 'snare'
            elif i == 3:
                element_type = 'mid_tom'
            elif i == 4:
                element_type = 'hihat'
            else:
                element_type = 'crash'
                
            # Add these events
            for t in band_onset_times:
                events.append((t, element_type))
        
        # 3. BEAT-SYNCED GRID FILLING
        # Find the beats
        _, beat_frames = librosa.beat.beat_track(y=y, sr=sr, trim=False)
        beat_times = librosa.frames_to_time(beat_frames, sr=sr)
        
        # For each beat, add notes on the grid
        for beat_time in beat_times:
            # Add on-beat note (usually kick or snare)
            if beat_time % (beat_duration * 2) < beat_duration:
                events.append((beat_time, 'kick'))
            else:
                events.append((beat_time, 'snare'))
            
            # Add 8th note hihat
            events.append((beat_time, 'hihat'))
            events.append((beat_time + beat_duration/2, 'hihat'))
            
            # Add some 16th note hihat
            events.append((beat_time + sixteenth_duration, 'hihat'))
            events.append((beat_time + sixteenth_duration*3, 'hihat'))
        
        # 4. ADD CRASH CYMBALS AT KEY POINTS
        # Usually crashes happen every 8 or 16 beats (every 2 or 4 measures)
        for i, beat_time in enumerate(beat_times):
            if i % 16 == 0:  # Every 4 measures
                events.append((beat_time, 'crash'))
        
        # 5. ADD OCCASIONAL DOUBLE-KICKS AND GHOST NOTES
        # For each kick, sometimes add another kick shortly after
        for time, type in list(events):
            if type == 'kick':
                # 20% chance of double kick
                if random.random() < 0.2:
                    events.append((time + sixteenth_duration/2, 'kick'))
            
            # For each snare, sometimes add ghost note before
            if type == 'snare':
                # 15% chance of ghost note
                if random.random() < 0.15:
                    events.append((time - sixteenth_duration/2, 'snare'))
        
        # Sort all events by time
        events.sort(key=lambda x: x[0])
        
        logger.info(f"Generated {len(events)} high-density events")
        return events
        
    except Exception as e:
        logger.error(f"Error generating high-density events: {e}")
        # Return fallback pattern using beat_duration if calculated
        try:
            fallback_events = []
            # Generate a simple 16th note grid pattern
            current_time = 3.0  # Start at 3 seconds
            while current_time < song_duration:
                tick = int((current_time - 3.0) / sixteenth_duration)
                
                # Every beat (every 4 16th notes)
                if tick % 4 == 0:
                    if (tick // 4) % 2 == 0:
                        fallback_events.append((current_time, 'kick'))
                    else:
                        fallback_events.append((current_time, 'snare'))
                    fallback_events.append((current_time, 'hihat'))
                else:
                    # Off beats
                    fallback_events.append((current_time, 'hihat'))
                    
                    # Sometimes add extra elements
                    if tick % 4 == 2:
                        # Add kick on the "and" of the beat sometimes
                        if (tick // 4) % 4 == 0 or (tick // 4) % 4 == 2:
                            fallback_events.append((current_time, 'kick'))
                            
                current_time += sixteenth_duration
                
            return fallback_events
        except:
            # If all else fails, return empty and let the CSV writer handle it
            return []

def write_high_density_notes_csv(events, song_duration, tempo, output_path):
    """
    Write the generated high density events to a notes.csv file.
    Handles note spacing, color assignment, and making sure output is playable.
    """
    try:
        # Start writing CSV
        with open(output_path, 'w', newline='') as f:
            writer = csv.writer(f)
            
            # Header row
            writer.writerow(["Time [s]", "Enemy Type", "Aux Color 1", "Aux Color 2", "Nº Enemies", "interval", "Aux"])
            
            # The minimum spacing between consecutive notes
            # This is to ensure playability - notes that are too close are difficult to hit
            min_spacing = 0.08  # 80ms minimum spacing
            
            # Start at 3.0s to match MIDI reference
            start_offset = 3.0
            
            # Previous note time for spacing check
            prev_note_time = 0
            
            # Keep track of written notes
            note_count = 0
            
            # For empty events list, generate a basic dense pattern
            if not events:
                beat_duration = 60 / tempo 
                sixteenth_duration = beat_duration / 4
                
                current_time = start_offset
                while current_time < song_duration:
                    writer.writerow([
                        f"{current_time:.2f}",
                        "1",
                        "1",
                        "1", 
                        "1",
                        "",
                        "6"
                    ])
                    note_count += 1
                    current_time += sixteenth_duration
                    
                logger.warning("Using fallback 16th note grid pattern")
                logger.info(f"Generated {note_count} notes")
                return True
            
            # Process events
            for time, element_type in events:
                # Only use events after start_offset
                if time >= start_offset and time < song_duration:
                    # Check if we have enough spacing to add this note
                    if time - prev_note_time >= min_spacing:
                        # Map element type to note properties
                        if element_type == 'kick':
                            enemy_type, color1, color2, aux = 1, 2, 2, 7
                        elif element_type == 'snare':
                            enemy_type, color1, color2, aux = 1, 2, 2, 7
                        elif element_type == 'hihat':
                            enemy_type, color1, color2, aux = 1, 1, 1, 6
                        elif element_type == 'crash':
                            enemy_type, color1, color2, aux = 2, 5, 6, 5
                        elif element_type == 'low_tom':
                            enemy_type, color1, color2, aux = 1, 3, 3, 7
                        elif element_type == 'mid_tom':
                            enemy_type, color1, color2, aux = 1, 4, 4, 7
                        else:  # Default to hihat for unknown types
                            enemy_type, color1, color2, aux = 1, 1, 1, 6
                        
                        # Round time to 2 decimal places for consistency
                        rounded_time = round(time, 2)
                        
                        # Write the note
                        writer.writerow([
                            f"{rounded_time:.2f}",
                            str(enemy_type),
                            str(color1),
                            str(color2),
                            "1",
                            "",
                            str(aux)
                        ])
                        
                        # Update previous note time for spacing check
                        prev_note_time = time
                        note_count += 1
            
            # If we somehow didn't generate any notes, add a basic pattern
            if note_count == 0:
                logger.warning("No valid events generated, using basic pattern")
                beat_duration = 60 / tempo
                current_time = start_offset
                
                while current_time < song_duration:
                    writer.writerow([f"{current_time:.2f}", "1", "1", "1", "1", "", "6"])  # Hihat
                    current_time += beat_duration / 2  # 8th notes
                    note_count += 1
            
            logger.info(f"Generated {note_count} high-density notes")
        
        return True
        
    except Exception as e:
        logger.error(f"Error writing high-density notes CSV: {str(e)}")
        return False

def generate_dense_pattern_csv(song_path, output_path, song_duration=180.0):
    """
    Generate a dense pattern without detailed audio analysis.
    Used as a fallback when librosa is not available or analysis fails.
    """
    try:
        # Estimate duration and tempo if possible
        try:
            import librosa
            y, sr = librosa.load(song_path, sr=None)
            song_duration = librosa.get_duration(y=y, sr=sr)
            
            # Try to detect tempo
            tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
        except:
            tempo = 120  # Default tempo
        
        # Get time between beats
        beat_duration = 60 / tempo
        
        # For high density, use 16th notes 
        note_spacing = beat_duration / 4
        
        with open(output_path, 'w', newline='') as f:
            writer = csv.writer(f)
            
            # Header row
            writer.writerow(["Time [s]", "Enemy Type", "Aux Color 1", "Aux Color 2", "Nº Enemies", "interval", "Aux"])
            
            # Start at 3.0s to match MIDI reference
            current_time = 3.0
            
            # Generate beats until the end of the song
            beat_count = 0
            measure = 0
            note_count = 0
            
            while current_time < song_duration:
                # Calculate position in measure (0-15 for 16th notes in a 4/4 measure)
                pos_in_measure = beat_count % 16
                
                # On quarter notes (every 4 16th notes)
                if pos_in_measure % 4 == 0:
                    # Beat 1 and 3: kick + hihat + sometimes crash
                    if pos_in_measure == 0 or pos_in_measure == 8:
                        writer.writerow([f"{current_time:.2f}", "1", "2", "2", "1", "", "7"])  # Kick
                        writer.writerow([f"{current_time:.2f}", "1", "1", "1", "1", "", "6"])  # Hihat
                        note_count += 2
                        
                        # Add crash at start of each 2-measure phrase
                        if pos_in_measure == 0 and measure % 2 == 0:
                            writer.writerow([f"{current_time:.2f}", "2", "5", "6", "1", "", "5"])  # Crash
                            note_count += 1
                    
                    # Beat 2 and 4: snare + hihat
                    else:
                        writer.writerow([f"{current_time:.2f}", "1", "2", "2", "1", "", "7"])  # Snare
                        writer.writerow([f"{current_time:.2f}", "1", "1", "1", "1", "", "6"])  # Hihat
                        note_count += 2
                
                # On 8th notes (every 2 16th notes) 
                elif pos_in_measure % 2 == 0:
                    writer.writerow([f"{current_time:.2f}", "1", "1", "1", "1", "", "6"])  # Hihat
                    
                    # Sometimes add kick drum on "and" of beat 1 or 3
                    if pos_in_measure == 4 or pos_in_measure == 12:
                        # 50% chance
                        if beat_count % 4 == 0:
                            writer.writerow([f"{current_time:.2f}", "1", "2", "2", "1", "", "7"])  # Kick
                            note_count += 1
                    
                    note_count += 1
                
                # On 16th notes (all other positions)
                else:
                    # Add hihat on every 16th note for high density
                    writer.writerow([f"{current_time:.2f}", "1", "1", "1", "1", "", "6"])  # Hihat
                    note_count += 1
                    
                    # Occasionally add ghost snare notes
                    if pos_in_measure == 7 or pos_in_measure == 15:
                        # 30% chance
                        if beat_count % 3 == 0:
                            writer.writerow([f"{current_time:.2f}", "1", "2", "2", "1", "", "7"])  # Ghost Snare
                            note_count += 1
                
                # Move to next 16th note
                current_time += note_spacing
                beat_count += 1
                
                # Every 16 16th-notes is a measure
                if beat_count % 16 == 0:
                    measure += 1
        
        logger.info(f"Generated dense pattern with {note_count} notes at {output_path}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to generate dense pattern CSV: {str(e)}")
        return False

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 2:
        generate_notes_csv(sys.argv[1], None, sys.argv[2])
    else:
        print("Usage: python high_density_notes_generator.py song_path output_path")