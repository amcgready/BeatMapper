"""
Standard notes generator that uses audio analysis to detect drum hits and create appropriate patterns.
"""
import os
import csv
import sys
import logging
import warnings
from pathlib import Path
import random
from .utils import format_time, format_bpm, format_percentage, format_safe

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
        
        def median(self, x, *args, **kwargs):
            if not x:
                return 0
            sorted_x = sorted(x)
            mid = len(sorted_x) // 2
            return sorted_x[mid]
            
    np = NumpyStub()

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def extract_midi_beats(midi_path):
    """
    Extract beat timings from a MIDI file.
    
    Args:
        midi_path: Path to the MIDI file
        
    Returns:
        list: List of beat times in seconds
    """
    beats = []
    
    try:
        # Try to import mido for MIDI processing
        import mido
        
        # Open the MIDI file
        mid = mido.MidiFile(midi_path)
        
        # Get the ticks per beat (resolution)
        ticks_per_beat = mid.ticks_per_beat
        
        # Track time and tempo
        current_time = 0  # in ticks
        current_tempo = 500000  # microseconds per beat (default = 120 BPM)
        
        # Process all tracks
        for track in mid.tracks:
            track_time = 0
            
            for msg in track:
                track_time += msg.time
                
                # Check for tempo changes
                if msg.type == 'set_tempo':
                    current_tempo = msg.tempo
                
                # Check for note events (note_on with velocity > 0)
                elif msg.type == 'note_on' and msg.velocity > 0:
                    # Convert ticks to seconds
                    seconds = mido.tick2second(track_time, ticks_per_beat, current_tempo)
                    beats.append(seconds)
        
        # Remove duplicates and sort
        beats = sorted(list(set(beats)))
        
        logger.info(f"Extracted {len(beats)} note events from MIDI file")
        return beats
        
    except ImportError:
        logger.warning("mido library not available for MIDI processing")
        return []
    except Exception as e:
        logger.error(f"Error processing MIDI file: {e}")
        return []

def generate_notes_csv(song_path, midi_path, output_path, target_difficulty=None):
    """
    Generate notes based on audio analysis and beat detection.
    This is the standard generator that balances accuracy and performance.
    
    Args:
        song_path: Path to the audio file
        midi_path: Optional path to a MIDI file for enhanced beat detection
        output_path: Path where the notes.csv will be saved        target_difficulty: Optional target difficulty level ("EASY", "MEDIUM", "HARD", "EXTREME")
                          If provided, note density will be adjusted to match this difficulty
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        logger.info(f"Generating standard drum notes for {os.path.basename(song_path)}")        # Debug logging for target difficulty
        debug_file = "c:/temp/beatmapper_debug.txt"
        try:
            os.makedirs(os.path.dirname(debug_file), exist_ok=True)
            with open(debug_file, "w") as f:  # Clear the file
                f.write(f"=== NOTES GENERATOR DEBUG ===\n")
                f.write(f"Song: {os.path.basename(song_path)}\n")
                f.write(f"Target difficulty received: {target_difficulty}\n")
                f.write(f"Type of target_difficulty: {type(target_difficulty)}\n")
        except:
            pass
          # Use adaptive difficulty system if target difficulty is specified
        if target_difficulty:
            try:
                from .adaptive_notes_simple import generate_adaptive_notes_csv
                
                # Debug logging
                try:
                    with open(debug_file, "a") as f:
                        f.write(f"Using simplified adaptive notes system for: {target_difficulty}\n")
                except:
                    pass
                
                # Use the adaptive system
                success = generate_adaptive_notes_csv(song_path, midi_path, output_path, target_difficulty)
                
                if success:
                    logger.info(f"Successfully generated notes using simplified adaptive system for {target_difficulty}")
                    # Debug logging
                    try:
                        with open(debug_file, "a") as f:
                            f.write(f"Simplified adaptive system completed successfully\n")
                    except:
                        pass
                    return True
                else:
                    logger.warning("Simplified adaptive system failed, falling back to original system")
                    
            except ImportError as e:
                logger.warning(f"Simplified adaptive system not available: {e}")
            except Exception as e:
                logger.error(f"Error in simplified adaptive system: {e}")
                # Fall through to original system
        
        # Check if MIDI file is provided for enhanced detection
        midi_beats = None
        if midi_path and os.path.exists(midi_path):
            logger.info(f"MIDI file provided: {os.path.basename(midi_path)}")
            try:
                midi_beats = extract_midi_beats(midi_path)
                logger.info(f"Extracted {len(midi_beats)} MIDI beats")
            except Exception as e:
                logger.warning(f"Failed to process MIDI file: {e}")
                logger.info("Continuing with audio-only analysis")
        
        # Check if we can use librosa for analysis
        try:
            import librosa
            
            # Suppress warnings from librosa
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                
                # Load the audio file
                y, sr = librosa.load(song_path, sr=None)
                
                # Get song duration
                song_duration = librosa.get_duration(y=y, sr=sr)
                logger.info(f"Song duration: {{format_time(song_duration)}}")
                
                # Detect the tempo
                tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
                logger.info(f"Detected tempo: {{format_bpm(tempo)}}")
                
                # Try to extract drums using spleeter if available
                drums_y = try_extract_drums_with_spleeter(song_path)
                if drums_y is not None:
                    logger.info("Using isolated drum track for better detection")
                    y_for_analysis = drums_y
                else:
                    # If spleeter not available, use percussive component
                    y_harmonic, y_percussive = librosa.effects.hpss(y)
                    y_for_analysis = y_percussive
                
                # Detect bands for multi-band analysis
                optimized_bands = [
                    (20, 120),    # Kick drum
                    (120, 300),   # Low toms
                    (300, 1000),  # Snare/mid toms
                    (1000, 4000), # Hi-hats/cymbals
                    (4000, 8000), # Rides/crashes
                ]                # Generate notes based on detected beats and audio analysis
                # Use MIDI beats if available, otherwise use librosa beats
                if midi_beats and len(midi_beats) > 0:
                    logger.info("Using MIDI beats for enhanced accuracy")
                    # Convert MIDI beat times to frame indices for compatibility
                    midi_beat_frames = librosa.time_to_frames(midi_beats, sr=sr)
                    success = generate_drum_synced_notes(
                        y_for_analysis, sr, song_duration, tempo, midi_beat_frames, 
                        output_path, optimized_bands, use_midi=True, target_difficulty=target_difficulty
                    )
                else:
                    logger.info("Using audio-detected beats")
                    success = generate_drum_synced_notes(
                        y_for_analysis, sr, song_duration, tempo, beats, 
                        output_path, optimized_bands, use_midi=False, target_difficulty=target_difficulty
                    )
                
                if success:
                    logger.info(f"Successfully generated notes.csv at {output_path}")
                    return True
                
        except ImportError:
            logger.warning("Could not import librosa, falling back to adaptive basic pattern")
        except Exception as e:
            logger.error(f"Error with audio analysis: {str(e)}")
        
        # Fallback to adaptive basic pattern
        return generate_adaptive_basic_pattern(song_path, output_path)
        
    except Exception as e:
        logger.error(f"Failed to generate notes.csv: {str(e)}")
        return False

def try_extract_drums_with_spleeter(song_path):
    """
    Try to extract drums from the audio file using spleeter if available.
    Returns isolated drum track or None if not available.
    """
    try:
        # First check if spleeter is installed
        import spleeter
        from spleeter.separator import Separator
        import tempfile
        import librosa
        
        logger.info("Spleeter found, attempting to isolate drums")
        
        # Create temporary directory for spleeter output
        with tempfile.TemporaryDirectory() as temp_dir:
            # Initialize the separator
            separator = Separator('spleeter:4stems')
            
            # Process the audio file
            separator.separate_to_file(song_path, temp_dir)
            
            # Get the base name of the file without extension
            base_name = os.path.splitext(os.path.basename(song_path))[0]
            
            # Load the isolated drums
            drums_path = os.path.join(temp_dir, base_name, 'drums.wav')
            if os.path.exists(drums_path):
                drums_y, sr = librosa.load(drums_path, sr=None)
                logger.info("Successfully isolated drum track")
                return drums_y
        
        logger.warning("Failed to isolate drums with spleeter")
        return None
        
    except ImportError:
        logger.info("Spleeter not available, using full mix for analysis")
        return None
    except Exception as e:
        logger.warning(f"Error using spleeter: {str(e)}")
        return None

def generate_drum_synced_notes(y, sr, song_duration, tempo, beats, output_path, optimized_bands=None, use_midi=False, target_difficulty=None):
    """
    Generate notes based on detected beats and multi-band analysis.
    This is the main algorithm for the standard generator.
    
    Args:
        use_midi: Whether the beats come from MIDI (True) or audio analysis (False)
        target_difficulty: Target difficulty level to adjust note density
    """
    try:
        import librosa
        
        # Convert beats from frames to time
        if use_midi:
            # If using MIDI, beats are already frame indices from time conversion
            beat_times = librosa.frames_to_time(beats, sr=sr)
            logger.info(f"Using {len(beat_times)} MIDI-derived beat times")
        else:
            # Audio-detected beats are frame indices
            beat_times = librosa.frames_to_time(beats, sr=sr)
            logger.info(f"Using {len(beat_times)} audio-detected beat times")
        
        # Get seconds per beat
        spb = 60 / tempo
          # Detect onsets with multiple band approach
        onsets_by_band = multi_band_onset_detection(y, sr, optimized_bands, base_threshold=threshold)
        
        # Calculate adaptive spacing between notes based on tempo        
        min_spacing = calculate_adaptive_beat_spacing(tempo)
        
        # Apply original difficulty-based adjustments as fallback
        if target_difficulty:
            # Debug logging setup
            debug_file = "c:/temp/beatmapper_debug.txt"
            try:
                os.makedirs(os.path.dirname(debug_file), exist_ok=True)
                with open(debug_file, "a") as f:
                    f.write(f"Using original difficulty system for: {target_difficulty}\n")
            except:
                pass
                
            difficulty_multipliers = {
                "EASY": 8.0,      # 8x spacing = 1/8th the notes  
                "MEDIUM": 1.4,    # 40% more spacing
                "HARD": 0.8,      # 20% less spacing = more notes
                "EXTREME": 0.5    # Half spacing = double the notes
            }
            
            multiplier = difficulty_multipliers.get(target_difficulty, 1.0)
            original_spacing = min_spacing
            min_spacing *= multiplier
            
            # Debug logging
            try:
                with open(debug_file, "a") as f:
                    f.write(f"Original system - Spacing: {original_spacing:.3f} -> {min_spacing:.3f} (multiplier: {multiplier})\n")
            except:
                pass            
            logger.info(f"Using original difficulty system: {target_difficulty} (spacing multiplier: {multiplier})")

        # Calculate adaptive thresholds based on audio characteristics
        threshold = calculate_adaptive_threshold(y, sr, tempo)
        
        # Apply difficulty-based threshold adjustments
        if target_difficulty:
            threshold_adjustments = {
                "EASY": 5.0,      # Much higher threshold = far fewer notes
                "MEDIUM": 1.2,    # Slightly higher threshold
                "HARD": 0.8,      # Lower threshold = more notes  
                "EXTREME": 0.6    # Much lower threshold = many notes
            }
            
            threshold_multiplier = threshold_adjustments.get(target_difficulty, 1.0)
            original_threshold = threshold
            threshold *= threshold_multiplier
            
            # Debug logging
            try:
                with open(debug_file, "a") as f:
                    f.write(f"Threshold: {original_threshold:.3f} -> {threshold:.3f} (multiplier: {threshold_multiplier})\n")
            except:
                pass
            
            logger.info(f"Adjusted threshold for {target_difficulty}: {threshold:.3f}")
        
        # Prepare to write CSV
        with open(output_path, 'w', newline='') as f:
            writer = csv.writer(f)
            
            # Header row
            writer.writerow(["Time [s]", "Enemy Type", "Aux Color 1", "Aux Color 2", "Nº Enemies", "interval", "Aux"])
            
            # Start at 3.0s to match MIDI reference
            start_offset = 3.0
            
            # Track last note time by band to avoid overcrowding
            last_note_time = {i: 0 for i in range(len(optimized_bands))}
            
            # For each band, add notes based on onsets
            for band_idx, band_onsets in enumerate(onsets_by_band):
                # Define note characteristics based on frequency band
                if band_idx == 0:  # Kick drum (lowest band)
                    enemy_type, color1, color2, aux = 1, 2, 2, 7
                elif band_idx == 1:  # Low toms
                    enemy_type, color1, color2, aux = 1, 3, 3, 7
                elif band_idx == 2:  # Snare/mid toms
                    enemy_type, color1, color2, aux = 1, 2, 2, 7
                elif band_idx == 3:  # Hi-hats/cymbals
                    enemy_type, color1, color2, aux = 1, 1, 1, 6
                else:  # Rides/crashes (highest band)
                    enemy_type, color1, color2, aux = 2, 5, 6, 5
                
                # Process onsets for this band
                for onset_time in band_onsets:
                    # Only add if after start_offset
                    if onset_time >= start_offset:
                        # Check if we should add a note here (respect minimum spacing)
                        if onset_time - last_note_time[band_idx] >= min_spacing:
                            # Round to 2 decimal places for consistent timing
                            note_time = round(onset_time, 2)
                            
                            # Write the note to CSV
                            writer.writerow([
                                f"{note_time:.2f}",
                                str(enemy_type),
                                str(color1),
                                str(color2),
                                "1",
                                "",
                                str(aux)
                            ])
                            
                            # Update last note time for this band
                            last_note_time[band_idx] = onset_time
            
            # Add occasional crashes at downbeats (first beat of measure)
            measure_length = 4 * spb  # 4 beats per measure
            current_measure = 0
            measure_start = start_offset
            
            while measure_start < song_duration:
                # Add crash at beginning and every 8 measures
                if current_measure % 8 == 0:
                    writer.writerow([
                        f"{measure_start:.2f}",
                        "2",  # Crash type
                        "5",  # Crash color 1
                        "6",  # Crash color 2
                        "1",
                        "",
                        "5"   # Crash aux
                    ])
                
                # Move to next measure
                measure_start += measure_length
                current_measure += 1
            
            # Log the total number of notes generated
            with open(output_path, 'r') as f:
                note_count = sum(1 for _ in f) - 1  # Subtract 1 for header
                logger.info(f"Generated {note_count} notes")
        
        return True
    
    except Exception as e:
        logger.error(f"Error in drum-synced note generation: {str(e)}")
        return False

def multi_band_onset_detection(y, sr, bands=None, base_threshold=0.3):
    """
    Detect onsets in multiple frequency bands for more accurate drum hit detection.
    Returns a list of onset times for each frequency band.
    
    Args:
        base_threshold: Base threshold for onset detection (can be adjusted by difficulty)
    """
    try:
        import librosa
        
        if bands is None:
            bands = [
                (20, 120),    # Kick drum
                (120, 300),   # Low toms
                (300, 1000),  # Snare/mid toms
                (1000, 4000), # Hi-hats/cymbals
                (4000, 8000)  # Rides/crashes
            ]
        
        onsets_by_band = []
        
        for low_freq, high_freq in bands:
            # Filter the audio to the band
            y_band = librosa.effects.remix(y, intervals=librosa.frequency_bands.frequency_filter(
                y, sr, low_freq, high_freq))
            
            # Compute onset envelope for this band
            onset_env = librosa.onset.onset_strength(y=y_band, sr=sr)
              # Adaptive threshold based on the band and base threshold
            # Lower bands (kick, bass) need higher thresholds
            if low_freq < 150:
                threshold = base_threshold * 1.33  # 0.4 default
            elif low_freq < 300:
                threshold = base_threshold * 1.17  # 0.35 default
            elif low_freq < 1000:
                threshold = base_threshold * 1.0   # 0.3 default
            else:
                threshold = base_threshold * 0.83  # 0.25 default
            
            # Detect onsets
            onset_frames = librosa.onset.onset_detect(
                onset_envelope=onset_env, sr=sr,
                threshold=threshold,
                pre_max=0.03*sr//512,
                post_max=0.03*sr//512,
                pre_avg=0.08*sr//512,
                post_avg=0.08*sr//512
            )
            
            # Convert to time
            onset_times = librosa.frames_to_time(onset_frames, sr=sr)
            onsets_by_band.append(onset_times)
        
        return onsets_by_band
        
    except Exception as e:
        logger.error(f"Error in multi-band onset detection: {str(e)}")
        return []

def calculate_adaptive_threshold(y, sr, tempo):
    """
    Calculate adaptive threshold for onset detection based on audio characteristics.
    """
    try:
        import librosa
        
        # Calculate overall RMS energy
        rms = np.mean(librosa.feature.rms(y=y)[0])
        
        # Calculate spectral flatness (measure of noisiness)
        flatness = np.mean(librosa.feature.spectral_flatness(y=y)[0])
        
        # More percussive = lower threshold needed
        y_harmonic, y_percussive = librosa.effects.hpss(y)
        perc_ratio = np.sum(y_percussive**2) / (np.sum(y_harmonic**2) + 1e-10)
        
        # Base threshold adjusted by audio characteristics
        base_threshold = 0.3
        
        # Adjust for energy level
        energy_factor = 0.1 * (1 - min(rms * 10, 0.9))
        
        # Adjust for percussiveness
        perc_factor = 0.1 * (1 - min(perc_ratio, 0.9))
        
        # Adjust for tempo - faster tempo needs higher threshold to avoid too many notes
        tempo_factor = 0.05 * (tempo / 120.0)
        
        # Combine factors
        threshold = base_threshold + energy_factor + perc_factor + tempo_factor
        
        # Ensure threshold is within reasonable bounds
        threshold = max(0.15, min(threshold, 0.5))
        
        logger.info(f"Calculated adaptive threshold: {{format_safe(threshold)}}")
        return threshold
        
    except Exception as e:
        logger.warning(f"Error calculating adaptive threshold: {str(e)}")
        return 0.3  # Default threshold

def calculate_adaptive_beat_spacing(tempo):
    """
    Calculate adaptive spacing between notes based on tempo.
    Faster tempos need larger spacing to avoid notes being too close together.
    """
    # Base spacing in seconds
    base_spacing = 0.15
    
    # Adjust for tempo
    if tempo < 80:
        # Slow tempo - can have closer notes
        return base_spacing * 0.8
    elif tempo < 120:
        # Medium tempo - normal spacing
        return base_spacing
    elif tempo < 160:
        # Fast tempo - slightly larger spacing
        return base_spacing * 1.2
    else:
        # Very fast tempo - even larger spacing
        return base_spacing * 1.5

def generate_adaptive_basic_pattern(song_path, output_path, song_duration=180.0):
    """
    Generate a basic pattern but with adaptive parameters based on song analysis.
    Used as a fallback when detailed analysis fails.
    """
    try:
        # Estimate duration and tempo if possible
        try:
            import librosa
            y, sr = librosa.load(song_path, sr=None)
            song_duration = librosa.get_duration(y=y, sr=sr)
            
            # Try to detect tempo
            tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
            
            # Analyze energy level
            rms = librosa.feature.rms(y=y)[0].mean()
            
            # Adjust pattern density based on energy
            if rms > 0.1:
                pattern_type = "dense"
            else:
                pattern_type = "normal"
                
        except:
            tempo = 120  # Default tempo
            pattern_type = "normal"  # Default pattern type
        
        # Get seconds per beat
        spb = 60 / tempo
        
        with open(output_path, 'w', newline='') as f:
            writer = csv.writer(f)
            
            # Header row
            writer.writerow(["Time [s]", "Enemy Type", "Aux Color 1", "Aux Color 2", "Nº Enemies", "interval", "Aux"])
            
            # Start at 3.0s to match MIDI reference
            current_time = 3.0
            
            # Generate beats until the end of the song
            beat_count = 0
            measure = 0
            
            # Use 16th note spacing for dense patterns, 8th for normal
            note_divisor = 4 if pattern_type == "dense" else 2
            note_spacing = spb / note_divisor
            
            while current_time < song_duration:
                # Calculate position in measure
                beat_in_measure = beat_count % 4
                
                # On main beats (quarter notes)
                if beat_count % note_divisor == 0:
                    # Beat 1 and 3: kick + hihat
                    if beat_in_measure == 0 or beat_in_measure == 2:
                        writer.writerow([f"{current_time:.2f}", "1", "2", "2", "1", "", "7"])  # Kick
                        writer.writerow([f"{current_time:.2f}", "1", "1", "1", "1", "", "6"])  # Hihat
                    # Beat 2 and 4: snare + hihat
                    else:
                        writer.writerow([f"{current_time:.2f}", "1", "2", "2", "1", "", "7"])  # Snare
                        writer.writerow([f"{current_time:.2f}", "1", "1", "1", "1", "", "6"])  # Hihat
                
                # For dense patterns, add hihat on 16th notes
                elif pattern_type == "dense":
                    writer.writerow([f"{current_time:.2f}", "1", "1", "1", "1", "", "6"])  # Hihat
                
                # Add crash at start of each 8-beat phrase
                if beat_count % 8 == 0:
                    writer.writerow([f"{current_time:.2f}", "2", "5", "6", "1", "", "5"])  # Crash
                
                # Move to next note time
                current_time += note_spacing
                beat_count += 1
                
                # Every 4 beats is a measure
                if beat_count % 4 == 0:
                    measure += 1
        
        logger.info(f"Generated adaptive basic pattern at {output_path}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to generate adaptive basic pattern: {str(e)}")
        
        # Attempt a fixed pattern as last resort
        try:
            return generate_fixed_basic_notes_csv(output_path, song_duration)
        except:
            return False

def generate_basic_notes_csv(song_path, output_path, song_duration=180.0):
    """
    Generate a very basic notes.csv file as a last resort fallback.
    """
    try:
        # Estimate duration if possible
        try:
            import librosa
            y, sr = librosa.load(song_path, sr=None)
            song_duration = librosa.get_duration(y=y, sr=sr)
            
            # Try to detect tempo
            tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
        except:
            tempo = 120  # Default tempo
        
        # Get seconds per beat
        spb = 60 / tempo
        
        with open(output_path, 'w', newline='') as f:
            writer = csv.writer(f)
            
            # Header row
            writer.writerow(["Time [s]", "Enemy Type", "Aux Color 1", "Aux Color 2", "Nº Enemies", "interval", "Aux"])
            
            # Use 16th note spacing (~0.22s) to match MIDI
            sixteenth_note = spb / 4
            
            # Start at 3.0s to match MIDI reference
            current_time = 3.0
            
            # Generate beats until the end of the song
            beat_count = 0
            
            while current_time < song_duration:
                # On main beats (quarter notes)
                if beat_count % 4 == 0:
                    # Alternate between kick and snare
                    if (beat_count // 4) % 2 == 0:
                        writer.writerow([f"{current_time:.2f}", "1", "2", "2", "1", "", "7"])  # Kick
                    else:
                        writer.writerow([f"{current_time:.2f}", "1", "2", "2", "1", "", "7"])  # Snare
                    
                    # Add hihat on every beat
                    writer.writerow([f"{current_time:.2f}", "1", "1", "1", "1", "", "6"])  # Hihat
                    
                    # Add crash every 8 beats
                    if beat_count % 8 == 0:
                        writer.writerow([f"{current_time:.2f}", "2", "5", "6", "1", "", "5"])  # Crash
                
                # Move to next 16th note
                current_time += sixteenth_note
                beat_count += 1
        
        logger.info(f"Generated basic pattern at {output_path}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to generate basic notes.csv: {str(e)}")
        return False

def generate_fixed_basic_notes_csv(output_path, song_duration=180.0):
    """
    Generate a fixed pattern with no external dependencies as a last resort.
    """
    try:
        with open(output_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["Time [s]", "Enemy Type", "Aux Color 1", "Aux Color 2", "Nº Enemies", "interval", "Aux"])
            
            # Generate a very simple fixed pattern
            time_increment = 0.5  # Half-second notes
            current_time = 3.0    # Start at 3 seconds
            
            while current_time < song_duration:
                # Alternate between different note types
                tick = int((current_time - 3.0) / time_increment)
                
                if tick % 4 == 0:
                    # Every 2 seconds: kick + hihat
                    writer.writerow([f"{current_time:.2f}", "1", "2", "2", "1", "", "7"])  # Kick 
                    writer.writerow([f"{current_time:.2f}", "1", "1", "1", "1", "", "6"])  # Hihat
                elif tick % 4 == 2:
                    # Every 2 seconds offset by 1: snare + hihat
                    writer.writerow([f"{current_time:.2f}", "1", "2", "2", "1", "", "7"])  # Snare
                    writer.writerow([f"{current_time:.2f}", "1", "1", "1", "1", "", "6"])  # Hihat
                else:
                    # Just hihat on other beats
                    writer.writerow([f"{current_time:.2f}", "1", "1", "1", "1", "", "6"])  # Hihat
                
                # Add crash every 8 seconds
                if tick % 16 == 0:
                    writer.writerow([f"{current_time:.2f}", "2", "5", "6", "1", "", "5"])  # Crash
                
                current_time += time_increment
        
        logger.info(f"Generated fixed basic pattern at {output_path}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to generate fixed basic pattern: {str(e)}")
        return False

def add_enhanced_pattern_variation(base_pattern, tempo):
    """
    Add more natural variations to patterns like those found in MIDI files
    """
    varied_pattern = []
    
    # Common MIDI patterns
    midi_like_variations = [
        # Fill variations
        [1, 0, 1, 0, 1, 1, 0, 1],  # Typical 8th note fill
        [1, 0, 1, 1, 1, 0, 1, 1],  # Dense fill
        # Hihat variations
        [1, 0, 1, 0, 1, 0, 1, 0],  # Standard 8th notes
        [1, 1, 1, 1, 1, 1, 1, 1],  # 16th notes
        # Kick patterns
        [1, 0, 0, 0, 1, 0, 0, 0],  # Basic kick on 1
        [1, 0, 0, 1, 1, 0, 0, 1],  # Kick on 1 and 3 with syncopation
    ]
    
    # Use pattern variations based on section of song
    section_length = int(len(base_pattern) / 4)
    for i in range(0, len(base_pattern), section_length):
        section = base_pattern[i:i+section_length]
        
        # Apply different variations to each drum element
        if random.random() < 0.3:
            # Add or remove notes based on MIDI-like patterns
            var_index = random.randint(0, len(midi_like_variations)-1)
            variation = midi_like_variations[var_index]
            
            for j, (time, note_type) in enumerate(section):
                if j % 8 < len(variation) and variation[j % 8] == 0:
                    # Skip this note based on variation pattern
                    continue
                varied_pattern.append((time, note_type))
        else:
            varied_pattern.extend(section)
    
    return varied_pattern

# Define some typical drum patterns for reference and pattern recognition
typical_patterns = [
    # Basic rock pattern
    [(0, "hihat"), (0, "kick"), 
     (0.25, "hihat"), 
     (0.5, "hihat"), (0.5, "snare"), 
     (0.75, "hihat")]
]

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 2:
        generate_notes_csv(sys.argv[1], None, sys.argv[2])
    else:
        print("Usage: python notes_generator.py song_path output_path")