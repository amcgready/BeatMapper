import os
import csv
import logging
import random
import warnings
import tempfile
import shutil
import subprocess
import sys
import numpy as np
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def generate_notes_csv(song_path, template_path, output_path):
    """
    Generate a notes.csv file with enemy spawns synchronized to the detected beat of the song.
    Maps different drum types to specific lanes.
    """
    try:
        logging.info(f"Generating Drums Rock-compatible notes for {os.path.basename(song_path)}")
        
        # Try drum separation with Spleeter first - IMPROVED
        drum_track = try_extract_drums_with_spleeter(song_path)
        
        # Use the drum track if available, otherwise use original song
        audio_for_analysis = drum_track if drum_track else song_path
        
        # Try advanced beat detection with librosa
        try:
            import librosa
            import numpy as np
                        
            logging.info("Using pattern-based drum analysis")
            
            # Suppress warnings from librosa
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                
                # Load the audio file
                y, sr = librosa.load(audio_for_analysis, sr=None)
                
                # Get song duration
                song_duration = librosa.get_duration(y=y, sr=sr)
                logging.info(f"Song duration: {song_duration:.2f} seconds")
                
                # Detect the tempo
                tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
                logging.info(f"Detected tempo: {tempo:.2f} BPM")
                
                # Use our advanced beat detection with debug info
                logging.info("Starting drum detection...")
                optimized_bands = fine_tune_frequency_bands(audio_for_analysis)
                
                # THIS IS THE CRITICAL LINE - Ensure it's called correctly
                success = generate_drum_synced_notes(y, sr, song_duration, tempo, beats, output_path, optimized_bands)
                
                if not success:
                    logging.warning("Drum detection failed, falling back to basic pattern")
                    return generate_fixed_basic_notes_csv(output_path, song_duration)
                
                return success
            
        except ImportError:
            logging.warning("Librosa not available, falling back to basic tempo estimation")
            return generate_basic_notes_csv(song_path, output_path)
        except Exception as e:
            logging.error(f"Advanced drum detection failed: {str(e)}", exc_info=True)
            logging.warning("Falling back to basic tempo estimation")
            return generate_basic_notes_csv(song_path, output_path)
            
    except Exception as e:
        logging.error(f"Failed to generate notes.csv: {str(e)}", exc_info=True)
        return False

def try_extract_drums_with_spleeter(song_path):
    """
    Try to extract drum track using Spleeter in an isolated environment.
    Returns path to drum track if successful, None otherwise.
    """
    try:
        logging.info("Attempting to extract drums with Spleeter...")
        
        # Create a temporary directory for output
        temp_dir = tempfile.mkdtemp(prefix="spleeter_")
        output_dir = os.path.join(temp_dir, "output")
        os.makedirs(output_dir, exist_ok=True)
        
        # Path for the extracted drum track
        drum_track_path = os.path.join(temp_dir, "drums.wav") 
        
        # IMPROVED: Try direct pip install first as it's more reliable
        try:
            # First check if spleeter is already installed in the current environment
            try:
                subprocess.run(
                    [sys.executable, "-c", "import spleeter"], 
                    check=True, 
                    stderr=subprocess.DEVNULL, 
                    stdout=subprocess.DEVNULL
                )
                spleeter_installed = True
                logging.info("Spleeter is already installed in the current environment")
            except subprocess.SubprocessError:
                spleeter_installed = False
                
            # If not installed, try installing it
            if not spleeter_installed:
                logging.info("Installing Spleeter in current environment...")
                subprocess.run(
                    [sys.executable, "-m", "pip", "install", "spleeter==2.3.0", "--no-cache-dir"],
                    check=True,
                    stdout=subprocess.PIPE
                )
            
            # Run Spleeter directly in current environment
            song_basename = os.path.splitext(os.path.basename(song_path))[0]
            subprocess.run(
                [sys.executable, "-m", "spleeter.separator", "separate", 
                 "-p", "spleeter:5stems", "-o", output_dir, song_path],
                check=True,
                stdout=subprocess.PIPE
            )
            
            # Copy the drum track to our temporary location
            src_drum_path = os.path.join(output_dir, song_basename, "drums.wav")
            if os.path.exists(src_drum_path):
                shutil.copy(src_drum_path, drum_track_path)
                logging.info(f"Drum track extracted to {drum_track_path}")
                return drum_track_path
                
        except Exception as e:
            logging.warning(f"Failed to extract drums with direct pip: {str(e)}")
            
            # Try with conda as fallback
            try:
                # Check if conda is available
                subprocess.run(["conda", "--version"], check=True, capture_output=True)
                
                # Use conda to create an isolated environment for Spleeter
                env_name = "spleeter_env"
                
                # Check if environment already exists
                result = subprocess.run(["conda", "env", "list"], capture_output=True, text=True)
                if env_name not in result.stdout:
                    logging.info("Creating conda environment for Spleeter...")
                    subprocess.run([
                        "conda", "create", "-n", env_name, 
                        "python=3.7", "ffmpeg", "libsndfile", "-y"
                    ], check=True)
                
                # Install Spleeter in the environment
                logging.info("Installing Spleeter...")
                subprocess.run([
                    "conda", "run", "-n", env_name,
                    "pip", "install", "spleeter==2.3.0"
                ], check=True)
                
                # Run Spleeter in the environment
                logging.info("Running Spleeter for drum extraction...")
                subprocess.run([
                    "conda", "run", "-n", env_name,
                    "spleeter", "separate", "-p", "spleeter:5stems", 
                    "-o", output_dir, song_path
                ], check=True)
                
                # Copy the drum track to our temporary location
                song_basename = os.path.splitext(os.path.basename(song_path))[0]
                src_drum_path = os.path.join(output_dir, song_basename, "drums.wav")
                if os.path.exists(src_drum_path):
                    shutil.copy(src_drum_path, drum_track_path)
                    logging.info(f"Drum track extracted to {drum_track_path}")
                    return drum_track_path
                    
            except Exception as conda_err:
                logging.warning(f"Failed to extract drums with conda: {str(conda_err)}")
        
        # Attempt third method - use a Python virtual environment
        try:
            # Create a virtualenv
            venv_dir = os.path.join(temp_dir, "venv")
            subprocess.run([sys.executable, "-m", "venv", venv_dir], check=True)
            
            # Get the pip and python path
            if os.name == 'nt':  # Windows
                pip_path = os.path.join(venv_dir, "Scripts", "pip.exe")
                python_path = os.path.join(venv_dir, "Scripts", "python.exe")
            else:  # Unix/Linux/Mac
                pip_path = os.path.join(venv_dir, "bin", "pip")
                python_path = os.path.join(venv_dir, "bin", "python")
            
            # Install Spleeter
            subprocess.run([pip_path, "install", "spleeter==2.3.0"], check=True)
            
            # Run Spleeter
            subprocess.run([
                python_path, "-m", "spleeter.separator", 
                "separate", "-p", "spleeter:5stems", "-o", output_dir, song_path
            ], check=True)
            
            # Copy the drum track
            song_basename = os.path.splitext(os.path.basename(song_path))[0]
            src_drum_path = os.path.join(output_dir, song_basename, "drums.wav")
            if os.path.exists(src_drum_path):
                shutil.copy(src_drum_path, drum_track_path)
                logging.info(f"Drum track extracted to {drum_track_path}")
                return drum_track_path
                
        except Exception as venv_err:
            logging.warning(f"Failed to extract drums with venv: {str(venv_err)}")
        
        # Clean up if we couldn't extract drums
        try:
            shutil.rmtree(temp_dir)
        except:
            pass
        
        logging.warning("Could not extract drums with Spleeter, continuing with original audio")
        return None
        
    except Exception as e:
        logging.warning(f"Failed to extract drums with Spleeter: {str(e)}")
        return None

def generate_pattern_based_notes(y, sr, tempo, beats, song_duration, output_path):
    """
    Generate notes based on detected patterns rather than individual hits.
    This is a new approach that focuses on pattern recognition.
    """
    try:
        import librosa
        
        # Extract percussive component
        y_harmonic, y_percussive = librosa.effects.hpss(y)
        
        # Get tempo in seconds per beat
        spb = 60 / tempo
        
        # Calculate segment length (2 measures in 4/4 time)
        segment_length = 8 * spb  # 8 beats = 2 measures
        
        # Create drum patterns library
        drum_patterns = create_drum_patterns(spb)
        
        # Segment the song
        num_segments = int(np.ceil(song_duration / segment_length))
        
        # Prepare to write CSV
        with open(output_path, 'w', newline='') as f:
            writer = csv.writer(f)
            
            # Header row
            writer.writerow(["Time [s]", "Enemy Type", "Aux Color 1", "Aux Color 2", "Nº Enemies", "interval", "Aux"])
            
            # Process each segment
            for i in range(num_segments):
                start_time = i * segment_length
                end_time = min(start_time + segment_length, song_duration)
                
                # Analyze this segment
                if start_time < song_duration:
                    # Get segment audio
                    start_sample = int(start_time * sr)
                    end_sample = int(end_time * sr)
                    segment = y_percussive[start_sample:end_sample] if start_sample < len(y_percussive) else np.array([])
                    
                    if len(segment) > 0:
                        # Analyze segment characteristics
                        pattern_type = classify_drum_pattern(segment, sr, tempo)
                        
                        # Apply the pattern
                        pattern = drum_patterns[pattern_type]
                        
                        # Write pattern notes for this segment
                        for note_offset, note_type, enemy_type, color1, color2, aux in pattern:
                            # Only add if within song duration
                            note_time = start_time + note_offset
                            if note_time < song_duration:
                                writer.writerow([
                                    f"{note_time:.2f}",
                                    str(enemy_type),
                                    str(color1),
                                    str(color2),
                                    "1",
                                    "",
                                    str(aux)
                                ])
        
        return True
    
    except Exception as e:
        logging.error(f"Error in pattern-based generation: {str(e)}")
        return generate_fixed_basic_notes_csv(output_path, song_duration)

def create_drum_patterns(spb):
    """
    Create a library of drum patterns at the given tempo (seconds per beat).
    Each pattern is a list of (time_offset, note_type, enemy_type, color1, color2, aux)
    """
    patterns = {}
    
    # Basic rock beat (kick on 1,3; snare on 2,4; hihat on 8ths)
    basic_rock = []
    for measure in range(2):  # 2 measures
        for beat in range(4):  # 4 beats per measure
            beat_time = (measure * 4 + beat) * spb
            
            # Kick on beats 1 and 3
            if beat == 0 or beat == 2:
                basic_rock.append((beat_time, "kick", 1, 2, 2, 7))
                
            # Snare on beats 2 and 4
            if beat == 1 or beat == 3:
                basic_rock.append((beat_time, "snare", 1, 2, 2, 7))
            
            # Hihat on every 8th note
            basic_rock.append((beat_time, "hihat", 1, 1, 1, 6))
            basic_rock.append((beat_time + spb/2, "hihat", 1, 1, 1, 6))
    
    # Add crash at start of pattern
    basic_rock.append((0, "crash", 2, 5, 6, 5))
    
    patterns["basic_rock"] = basic_rock
    
    # Double-time rock beat (faster hihat)
    double_rock = []
    for measure in range(2):
        for beat in range(4):
            beat_time = (measure * 4 + beat) * spb
            
            # Kick on beats 1 and 3
            if beat == 0 or beat == 2:
                double_rock.append((beat_time, "kick", 1, 2, 2, 7))
                
            # Snare on beats 2 and 4
            if beat == 1 or beat == 3:
                double_rock.append((beat_time, "snare", 1, 2, 2, 7))
            
            # Hihat on every 16th note (4 per beat)
            for i in range(4):
                double_rock.append((beat_time + i*spb/4, "hihat", 1, 1, 1, 6))
    
    # Add crash at start of pattern
    double_rock.append((0, "crash", 2, 5, 6, 5))
    
    patterns["double_rock"] = double_rock
    
    # Half-time feel
    half_time = []
    for measure in range(2):
        for beat in range(4):
            beat_time = (measure * 4 + beat) * spb
            
            # Kick on beat 1, snare on 3
            if beat == 0:
                half_time.append((beat_time, "kick", 1, 2, 2, 7))
            if beat == 2:
                half_time.append((beat_time, "snare", 1, 2, 2, 7))
            
            # Hihat on every beat
            half_time.append((beat_time, "hihat", 1, 1, 1, 6))
    
    # Add crash at start
    half_time.append((0, "crash", 2, 5, 6, 5))
    
    patterns["half_time"] = half_time
    
    # Metal/fast beat
    metal_beat = []
    for measure in range(2):
        for beat in range(4):
            beat_time = (measure * 4 + beat) * spb
            
            # Double kick pattern
            metal_beat.append((beat_time, "kick", 1, 2, 2, 7))
            metal_beat.append((beat_time + spb/4, "kick", 1, 2, 2, 7))
            
            # Snare on beats 2 and 4
            if beat == 1 or beat == 3:
                metal_beat.append((beat_time, "snare", 1, 2, 2, 7))
            
            # Ride cymbal on every 8th
            metal_beat.append((beat_time, "ride", 3, 2, 4, 5))
            metal_beat.append((beat_time + spb/2, "ride", 3, 2, 4, 5))
    
    # Add crash at start
    metal_beat.append((0, "crash", 2, 5, 6, 5))
    
    patterns["metal"] = metal_beat

    # Add crash-heavy pattern for chorus sections
    crash_heavy = []
    for measure in range(2):  # 2 measures
        for beat in range(4):  # 4 beats per measure
            beat_time = (measure * 4 + beat) * spb
            
            # Kick on every beat
            crash_heavy.append((beat_time, "kick", 1, 2, 2, 7))
                
            # Snare on beats 2 and 4
            if beat == 1 or beat == 3:
                crash_heavy.append((beat_time, "snare", 1, 2, 2, 7))
            
            # Crash on every beat for emphasis
            if beat == 0 or beat == 2:  # Crashes on 1 and 3
                crash_heavy.append((beat_time, "crash", 2, 5, 6, 5))
            
            # Hihat on every 8th note
            crash_heavy.append((beat_time, "hihat", 1, 1, 1, 6))
            crash_heavy.append((beat_time + spb/2, "hihat", 1, 1, 1, 6))
    
    patterns["crash_heavy"] = crash_heavy
    
    return patterns

def classify_drum_pattern(segment, sr, tempo):
    """
    Classify the drum pattern in the audio segment.
    Returns a pattern type from our library.
    """
    try:
        import librosa
        
        # Extract features
        # RMS energy
        rms = np.mean(librosa.feature.rms(y=segment)[0])
        
        # Spectral centroid (brightness)
        centroid = np.mean(librosa.feature.spectral_centroid(y=segment, sr=sr)[0])
        
        # Onset strength
        onset_env = librosa.onset.onset_strength(y=segment, sr=sr)
        mean_onset = np.mean(onset_env)
        
        # Simple decision tree for pattern classification
        if rms > 0.15:  # High energy
            if mean_onset > 0.5:  # Many onsets
                if centroid > 5000:  # Bright sound
                    return "metal"  # Fast/metal pattern
                else:
                    return "double_rock"  # Double-time rock
            else:
                if centroid > 3000:  # Brighter sound with crashes
                    return "crash_heavy"  # Emphasize crashes
                else:
                    return "basic_rock"  # Basic rock pattern
        else:  # Lower energy
            return "half_time"  # Half-time feel
            
    except Exception as e:
        logging.error(f"Error in pattern classification: {str(e)}")
        # Default to basic rock if analysis fails
        return "basic_rock"

def calculate_adaptive_threshold(y, sr, tempo):
    """Calculate an adaptive threshold based on audio characteristics"""
    # Lower the base threshold dramatically
    base_threshold = 0.0001  # Previously 0.0005
    
    # Calculate RMS energy
    rms = np.sqrt(np.mean(y**2))
    
    # Adjust threshold based on RMS energy - lower for quieter tracks
    if rms < 0.05:
        threshold = base_threshold * 0.5
    elif rms < 0.1:
        threshold = base_threshold * 0.8
    else:
        threshold = base_threshold
    
    return threshold

def calculate_adaptive_beat_spacing(tempo):
    """Calculate adaptive minimum beat spacing based on song tempo"""
    # Base spacing at 120 BPM would be 60/120 = 0.5 seconds
    base_spacing = 60 / tempo
    
    # IMPROVED: Use smaller fractions to catch more beats
    # Current spacing values are still too large
    if tempo > 160:
        return base_spacing * 0.01  # Much smaller
    elif tempo > 120:
        return base_spacing * 0.01  # Much smaller
    else:
        return base_spacing * 0.005  # Much smaller

def multi_band_onset_detection(y, sr, bands=None):
    """
    Detect onsets in multiple frequency bands to better identify different drum types.
    Returns a list of (time, drum_type) tuples.
    """
    import librosa
    
    if bands is None:
        # Use more targeted frequency bands
        bands = {
            'kick': (30, 100),     # Narrower low-end focus
            'snare': (200, 350),   # More focused snare band
            'hihat': (7000, 12000) # Higher frequencies for hihat
        }
    
    events = []
    
    # Process each band separately with MUCH LOWER thresholds
    for name, (low_freq, high_freq) in bands.items():
        # Filter the signal to the band
        y_band = librosa.effects.preemphasis(y)  # Enhance higher frequencies
        y_filter = librosa.filtfilt(b=firwin(
            numtaps=2049, 
            cutoff=[low_freq, high_freq], 
            fs=sr, 
            pass_zero=False
        ), a=[1], x=y_band)
        
        # Detect onsets with a MUCH LOWER threshold
        onset_env = librosa.onset.onset_strength(
            y=y_filter, sr=sr,
            hop_length=512,
            aggregate=np.median
        )
        
        # Use a drastically lower threshold
        threshold = 0.00005  # Previously around 0.0002
        
        onset_frames = librosa.onset.onset_detect(
            onset_envelope=onset_env, 
            sr=sr,
            threshold=threshold,
            pre_max=0.03*sr//512,
            post_max=0.03*sr//512,
            pre_avg=0.1*sr//512,
            post_avg=0.1*sr//512
        )
        
        # Convert frames to times
        onset_times = librosa.frames_to_time(onset_frames, sr=sr)
        
        # Add each onset as an event with the drum type
        for time in onset_times:
            events.append((time, name))
    
    # Sort events by time
    events.sort(key=lambda x: x[0])
    return events

def generate_drum_synced_notes(y, sr, song_duration, tempo, beats, output_path, optimized_bands=None):
    """
    Generate a notes.csv file with events synchronized to the detected drum hits.
    """
    # Calculate minimum spacing between consecutive beats based on tempo
    min_beat_spacing = calculate_adaptive_beat_spacing(tempo)
    
    # Prepare event tracking
    all_events = []
    
    # IMPROVEMENT: Combine multiple onset detection methods
    # Method 1: Multi-band onset detection (frequency-based)
    logging.info("Multi-band onset detection...")
    band_events = multi_band_onset_detection(y, sr, optimized_bands)
    logging.info(f"Detected {len(band_events)} events from multi-band analysis")
    all_events.extend(band_events)
    
    # Method 2: Percussive component onset detection
    y_harmonic, y_percussive = librosa.effects.hpss(y)
    onset_env = librosa.onset.onset_strength(
        y=y_percussive, sr=sr,
        hop_length=512,
        aggregate=np.median
    )
    
    # Use a very low threshold to catch more events
    onset_threshold = 0.0002
    onset_frames = librosa.onset.onset_detect(
        onset_envelope=onset_env, 
        sr=sr,
        threshold=onset_threshold,
        pre_max=0.03*sr//512,
        post_max=0.03*sr//512,
        pre_avg=0.1*sr//512,
        post_avg=0.1*sr//512
    )
    onset_times = librosa.frames_to_time(onset_frames, sr=sr)
    
    # Add each onset as a generic drum event
    for time in onset_times:
        all_events.append((time, "general"))
    
    # Method 3: Spectral flux onset detection (better for percussive sounds)
    onset_flux = librosa.onset.onset_detect(
        y=y_percussive, sr=sr, 
        onset_envelope=librosa.onset.onset_strength(y=y_percussive, sr=sr, feature=librosa.feature.spectral_flux),
        threshold=onset_threshold * 0.75
    )
    onset_times_flux = librosa.frames_to_time(onset_flux)
    
    # Add each onset as a generic drum event
    for time in onset_times_flux:
        all_events.append((time, "general"))
    
    # Group similar timestamps to avoid duplicates but preserve different drum types
    # THIS PART WAS BROKEN - FIX IT
    event_groups = {}
    for time, drum_type in all_events:
        # Use much finer granularity - group within 0.005s
        rounded_time = round(time * 200) / 200  # Round to nearest 0.005s
        if rounded_time not in event_groups:
            event_groups[rounded_time] = []
        event_groups[rounded_time].append(drum_type)
    
    # Process the groups into cleaned events
    cleaned_events = []
    for time, drum_types in sorted(event_groups.items()):
        # Keep one of each unique drum type at this timestamp
        for drum_type in set(drum_types):
            cleaned_events.append((time, drum_type))
    
    logging.info(f"Detected {len(cleaned_events)} drum events")
    
    # Map drum types to enemy types and colors
    drum_to_enemy_type = {
        "kick": 1,
        "snare": 1,
        "hihat": 1,
        "crash": 2,
        "ride": 3,
        "general": 1
    }
    
    drum_to_aux = {
        "kick": 7,
        "snare": 7,
        "hihat": 6,
        "crash": 5,
        "ride": 5,
        "general": 7
    }
    
    drum_to_colors = {
        "kick": (2, 2),
        "snare": (2, 2),
        "hihat": (1, 1),
        "crash": (5, 6),
        "ride": (2, 4),
        "general": (2, 2)
    }
    
    # Create the notes.csv file
    with open(output_path, 'w', newline='') as f:
        writer = csv.writer(f)
        
        # Header row - exactly as in the template
        writer.writerow(["Time [s]", "Enemy Type", "Aux Color 1", "Aux Color 2", "Nº Enemies", "interval", "Aux"])
        
        # Process each drum event - THIS PART WAS MISSING
        for time, drum_type in cleaned_events:
            # Get enemy type and aux (lane) value for this drum type
            enemy_type = drum_to_enemy_type.get(drum_type, 1)
            aux = drum_to_aux.get(drum_type, 7)
            color1, color2 = drum_to_colors.get(drum_type, (2, 2))
            
            # ADD THIS CRITICAL LINE - WRITE TO CSV
            writer.writerow([f"{time:.2f}", str(enemy_type), str(color1), str(color2), "1", "", str(aux)])
    
    # Add extensive debugging to see what's happening
    logging.info(f"Detected {len(all_events)} raw events before grouping")
    logging.info(f"Created {len(event_groups)} event groups")
    logging.info(f"Final cleaned events: {len(cleaned_events)}")
    logging.info(f"First 10 events: {cleaned_events[:10]}")

    # Log the actual CSV writing
    logging.info(f"Writing {len(cleaned_events)} events to CSV at {output_path}")
    
    # After writing all events, log the count
    writer.writerow(["Time [s]", "Enemy Type", "Aux Color 1", "Aux Color 2", "Nº Enemies", "interval", "Aux"])

    events_written = 0
    for time, drum_type in cleaned_events:
        enemy_type = drum_to_enemy_type.get(drum_type, 1)
        aux = drum_to_aux.get(drum_type, 7)
        color1, color2 = drum_to_colors.get(drum_type, (2, 2))
        
        writer.writerow([f"{time:.2f}", str(enemy_type), str(color1), str(color2), "1", "", str(aux)])
        events_written += 1

    logging.info(f"Successfully wrote {events_written} events to {output_path}")
    
    return True
def generate_adaptive_basic_pattern(song_path, output_path, song_duration=180.0):
    """Generate a basic pattern but try to adapt to the song's tempo"""
    try:
        import librosa
        
        # Load the audio file
        y, sr = librosa.load(song_path, sr=None)
        
        # Get song duration
        if song_duration == 180.0:  # If using default
            song_duration = librosa.get_duration(y=y, sr=sr)
            
        # Detect the tempo
        tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
        logging.info(f"Using adaptive basic pattern with detected tempo: {tempo:.2f} BPM")
        
        # Calculate beat duration
        beat_duration = 60 / tempo
        
        # Convert beat frames to times
        beat_times = librosa.frames_to_time(beats, sr=sr)
        
        # Extract percussive component for better analysis
        try:
            y_harmonic, y_percussive = librosa.effects.hpss(y)
            
            # Analyze the song to detect recurring patterns
            mfcc = librosa.feature.mfcc(y=y_percussive, sr=sr, n_mfcc=13)
            beat_sync_mfcc = librosa.util.sync(mfcc, beats)
            
            # Find repeated sections
            S = librosa.segment.recurrence_matrix(beat_sync_mfcc)
        except:
            y_percussive = y
            S = None  # Default if HPSS fails
        
        with open(output_path, 'w', newline='') as f:
            writer = csv.writer(f)
            
            # CORRECT HEADERS FOR DRUMS ROCK
            writer.writerow(["Time [s]", "Enemy Type", "Aux Color 1", "Aux Color 2", "Nº Enemies", "interval", "Aux"])
            
            # IMPROVED: Use actual detected beats rather than evenly spaced beats
            if len(beat_times) > 0:
                # Use actual detected beats but ensure they don't get too dense
                processed_beats = []
                last_beat = -1
                
                for i, beat_time in enumerate(beat_times):
                    # Skip if too close to previous beat
                    if last_beat >= 0 and beat_time - processed_beats[-1] < beat_duration * 0.5:
                        continue
                    
                    processed_beats.append(beat_time)
                    last_beat = beat_time
                    
                    # Basic pattern - place notes on actual beats
                    # Alternate between types
                    if i % 4 == 0:
                        # Downbeat - use type 1, colors 2,2, Aux 7
                        writer.writerow([f"{beat_time:.2f}", "1", "2", "2", "1", "", "7"])
                    elif i % 4 == 2:
                        # Beat 3 - use type 1, colors 2,2, Aux 7
                        writer.writerow([f"{beat_time:.2f}", "1", "2", "2", "1", "", "7"])
                    elif i % 2 == 1:
                        # Other beats - use type 1, colors 1,1, Aux 6
                        writer.writerow([f"{beat_time:.2f}", "1", "1", "1", "1", "", "6"])
                    
                    # Every 8 beats, add a special enemy
                    if i % 8 == 7:
                        # Add a little offset
                        time = beat_time + beat_duration * 0.25
                        writer.writerow([f"{time:.2f}", "2", "5", "6", "1", "", "5"])
                    
                    # Every 16 beats, add a timed sequence
                    if i % 16 == 15:
                        # Add a little offset
                        time = beat_time + beat_duration * 0.5
                        writer.writerow([f"{time:.2f}", "3", "2", "2", "1", "2", "7"])
            else:
                # Fallback to fixed pattern if no beats detected
                return generate_fixed_basic_notes_csv(output_path, song_duration)
                
            # Ensure we have at least one note at the end of the song
            if processed_beats and processed_beats[-1] < song_duration - 10:
                writer.writerow([
                    f"{song_duration - 5:.2f}",
                    "1",
                    "2",
                    "2",
                    "1",
                    "",
                    "7"
                ])
        
        logging.info(f"Generated tempo-adaptive notes.csv at {output_path}")
        return True
    except Exception as e:
        logging.error(f"Error in adaptive pattern generation: {str(e)}")
        return generate_fixed_basic_notes_csv(output_path, song_duration)

def generate_basic_notes_csv(song_path, output_path, song_duration=180.0):
    """Generate notes.csv with basic patterns but try to adapt to song characteristics"""
    logging.info("Using adaptive basic pattern generation")
    
    if song_path and os.path.exists(song_path):
        # Try the adaptive pattern first, which analyzes the song
        return generate_adaptive_basic_pattern(song_path, output_path, song_duration)
    else:
        # If no song path or file doesn't exist, fall back to fixed pattern
        return generate_fixed_basic_notes_csv(output_path, song_duration)


# If all else fails - modify generate_fixed_basic_notes_csv to use MIDI-like spacing
def generate_fixed_basic_notes_csv(output_path, song_duration=180.0):
    """Generate pattern matching typical MIDI spacing as last resort"""
    logging.info("Using MIDI-like pattern generation with 0.22s spacing")
    
    try:
        with open(output_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["Time [s]", "Enemy Type", "Aux Color 1", "Aux Color 2", "Nº Enemies", "interval", "Aux"])
            
            # Use 0.22s spacing like in the MIDI
            current_time = 3.0  # Start at 3s like MIDI
            while current_time < song_duration:
                writer.writerow([f"{current_time:.2f}", "1", "2", "2", "1", "", "7"])
                current_time += 0.22
                
                # Add hihat every other note
                if int(current_time * 10) % 4 == 0:
                    writer.writerow([f"{current_time:.2f}", "1", "1", "1", "1", "", "6"])
                
                # Add crash every 8th note
                if int(current_time * 10) % 20 == 0:
                    writer.writerow([f"{current_time:.2f}", "2", "5", "6", "1", "", "5"])
        
        return True
    except Exception as e:
        logging.error(f"Failed to generate MIDI-like notes: {str(e)}")
        return False

# Add drum pattern templates for better detection
typical_patterns = [
    # Basic rock pattern with hihat, kick and snare
    [(0, "hihat"), (0, "kick"), 
     (0.25, "hihat"), 
     (0.5, "hihat"), (0.5, "snare"), 
     (0.75, "hihat")]
]

# Apply these pattern templates to enhance detection

if __name__ == "__main__":
    # Example usage
    if len(sys.argv) > 2:
        song_path = sys.argv[1]
        output_path = sys.argv[2]
        template_path = sys.argv[3] if len(sys.argv) > 3 else None
        generate_notes_csv(song_path, template_path, output_path)
    else:
        print("Usage: python notes_generator.py song_path output_path [template_path]")