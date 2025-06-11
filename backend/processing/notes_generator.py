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
                        
            logging.info("Using librosa for advanced drum analysis")
            
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
                
                # Fine-tune frequency bands for this specific song
                optimized_bands = fine_tune_frequency_bands(audio_for_analysis)
                
                # Generate drum-specific beat data with IMPROVED detection
                success = generate_drum_synced_notes(y, sr, song_duration, tempo, beats, output_path, optimized_bands)
                
                # Clean up temporary drum track if it exists
                if drum_track and os.path.exists(drum_track):
                    try:
                        os.remove(drum_track)
                    except:
                        pass
                
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

def calculate_adaptive_threshold(y, sr, tempo):
    """Calculate adaptive onset detection threshold based on audio characteristics"""
    # IMPROVED: Start with a much lower base threshold to catch more subtle drums
    base_threshold = 0.015  # Current value: 0.035
    
    # Analyze overall energy distribution
    rms = librosa.feature.rms(y=y)[0]
    rms_mean = np.mean(rms)
    rms_std = np.std(rms)
    
    # Adjust threshold based on overall dynamics and tempo
    if rms_std < 0.01:  # Very consistent volume
        threshold = base_threshold * 0.7  # Even lower for consistent tracks
    elif rms_std > 0.1:  # Highly variable volume
        threshold = base_threshold * 1.1
    else:
        threshold = base_threshold
        
    # Adjust for tempo
    if tempo < 80:  # Slow songs need lower threshold
        threshold *= 0.85
    elif tempo > 160:  # Fast songs need higher threshold
        threshold *= 1.05
        
    return threshold

def calculate_adaptive_beat_spacing(tempo):
    """Calculate adaptive minimum beat spacing based on song tempo"""
    # Base spacing at 120 BPM would be 60/120 = 0.5 seconds
    base_spacing = 60 / tempo
    
    # IMPROVED: Use smaller fractions to catch more beats
    # Allow much closer spacing between events
    if tempo > 160:
        return base_spacing * 0.1  # Current value: 0.3
    elif tempo > 120:
        return base_spacing * 0.08  # Current value: 0.25
    else:
        return base_spacing * 0.05  # Current value: 0.2

def multi_band_onset_detection(y, sr, bands):
    """
    NEW: Perform onset detection separately for different frequency bands
    to better catch different drum types.
    """
    # Create empty list to store all detected onsets
    all_onsets = []
    
    # Define filter bank for different frequency bands
    for name, (low_freq, high_freq) in bands.items():
        # Filter the signal to specific band
        y_band = librosa.effects.preemphasis(y)  # Pre-emphasize to highlight attacks
        
        # Apply bandpass filter for this frequency range
        y_band = librosa.filters.butter(y_band, sr=sr, freq=None, 
                                       lowpass=high_freq, highpass=low_freq)
        
        # Detect onsets in this band with lower threshold for specific drum types
        if name in ['kick', 'snare']:
            threshold = 0.03  # Lower threshold for important drums
        else:
            threshold = 0.04
            
        onset_env = librosa.onset.onset_strength(y=y_band, sr=sr, aggregate=np.median)
        onset_frames = librosa.onset.onset_detect(onset_envelope=onset_env, sr=sr, 
                                                threshold=threshold,
                                                pre_max=0.03*sr//512, 
                                                post_max=0.03*sr//512)
        
        onset_times = librosa.frames_to_time(onset_frames, sr=sr)
        
        # Add detected onsets with drum type info
        for t in onset_times:
            all_onsets.append((t, name))
    
    # Sort all onsets by time
    all_onsets.sort(key=lambda x: x[0])
    
    return all_onsets

def generate_drum_synced_notes(y, sr, song_duration, tempo, beats, output_path, optimized_bands=None):
    """Generate notes.csv with specialized drum type detection and lane mapping"""
    try:
        import librosa
                
        # Define frequency bands for different drum types
        default_bands = {
            # Snare - mid frequency range
            "snare": (200, 400),
            # Kick - low frequency range
            "kick": (50, 150),
            # Tom High - mid-high frequency range
            "tom_high": (300, 500),
            # Tom Low - mid-low frequency range
            "tom_low": (150, 300),
            # Crash - high frequency range with sharp attack
            "crash": (800, 1600),
            # Ride - high frequency range with sustained components
            "ride": (1500, 4000),
            # Hi-hat - very high frequency range (NEW)
            "hihat": (5000, 10000)
        }
        
        # Use optimized bands if available
        drum_bands = optimized_bands if optimized_bands else default_bands
        
        # Map drum types to enemy types and Aux values for Drums Rock format
        drum_to_enemy_type = {
            "snare": 1,   # Regular enemy
            "kick": 1,    # Regular enemy
            "tom_high": 1, # Regular enemy
            "tom_low": 1,  # Regular enemy
            "crash": 2,    # Special enemy for crash
            "ride": 3,     # Special enemy type for ride
            "hihat": 1     # Regular enemy for hi-hat
        }
        
        # Map drum types to Aux values (lane numbers in Drums Rock)
        # IMPORTANT: Use values that work with Drums Rock
        drum_to_aux = {
            "snare": 7,   # Use values from working example
            "kick": 7,    # Use values from working example
            "tom_high": 6,
            "tom_low": 6,
            "crash": 5,
            "ride": 5,
            "hihat": 6
        }
        
        # Map drum types to color values
        drum_to_colors = {
            "snare": (2, 2),
            "kick": (2, 2),
            "tom_high": (1, 1),
            "tom_low": (1, 1),
            "crash": (5, 6),
            "ride": (2, 4),
            "hihat": (1, 1)
        }
        
        # IMPROVED: Preprocess audio to enhance drum transients
        y_harmonic, y_percussive = librosa.effects.hpss(y)
        
        # IMPROVED: Apply preemphasis to enhance attack transients
        y_percussive = librosa.effects.preemphasis(y_percussive)
        
        # IMPROVED: Run multi-band onset detection for better drum detection
        drum_events_from_bands = multi_band_onset_detection(y_percussive, sr, drum_bands)
        
        # ADAPTIVE PARAMETERS:
        # Calculate adaptive onset detection threshold
        onset_threshold = calculate_adaptive_threshold(y, sr, tempo)
        
        # Calculate adaptive minimum beat spacing
        min_beat_spacing = calculate_adaptive_beat_spacing(tempo)
        
        # IMPROVED: Also detect onsets in the full percussive signal
        onset_env = librosa.onset.onset_strength(
            y=y_percussive, sr=sr,
            hop_length=512,
            aggregate=np.median  # Use median for sharper drum detection
        )
        
        # Detect onsets with adaptive threshold
        onset_frames = librosa.onset.onset_detect(
            onset_envelope=onset_env, 
            sr=sr,
            threshold=onset_threshold,
            pre_max=0.02*sr//512,  # IMPROVED: Shorter window to catch closely spaced drums
            post_max=0.02*sr//512,
            pre_avg=0.1*sr//512,
            post_avg=0.1*sr//512
        )
        onset_times = librosa.frames_to_time(onset_frames, sr=sr)
        
        # IMPROVED: Convert librosa detected beats to times
        beat_times = librosa.frames_to_time(beats, sr=sr)
        
        # IMPROVED: Combine all detected events
        all_events = []
        
        # First add all band-specific detected drums
        for time, drum_type in drum_events_from_bands:
            all_events.append((time, drum_type))
            
        # Then add general onset detection
        for time in onset_times:
            # Analyze which band has most energy at this point
            frame = librosa.time_to_frames(time, sr=sr)
            if frame < len(y):
                # Get a small window around the onset
                y_slice = y[max(0, int(time * sr) - 1024):min(len(y), int(time * sr) + 1024)]
                
                # Detect drum type for this onset
                detected_type = detect_drum_type(y_slice, sr, drum_bands)
                all_events.append((time, detected_type))
        
        # Add beats detected by beat_track as kick drums
        for time in beat_times:
            all_events.append((time, "kick"))
        
        # IMPROVED: Sort and clean up events - remove duplicates within small time windows
        all_events.sort(key=lambda x: x[0])
        
        # Cleaned events will store the final output events
        cleaned_events = []
        
        # Group events by timestamps, allowing multiple hits at the same time
        for i, (time, drum_type) in enumerate(all_events):
            # Add to cleaned events directly
            cleaned_events.append((time, drum_type))
            
        # POST-PROCESSING: Make sure important beats have events
        # If using the beat tracker results, ensure every beat has at least one event
        ensure_events_on_beats(cleaned_events, beat_times, min_beat_spacing * 0.5)
        
        # Final sort
        cleaned_events.sort(key=lambda x: x[0])
        
        # Write the CSV with the CORRECT Drums Rock format
        with open(output_path, 'w', newline='') as f:
            writer = csv.writer(f)
            # CORRECT HEADERS FOR DRUMS ROCK - exact match with working version
            writer.writerow(["Time [s]", "Enemy Type", "Aux Color 1", "Aux Color 2", "Nº Enemies", "interval", "Aux"])
            
            # Process each drum event
            for time, drum_type in cleaned_events:
                # Get enemy type and aux (lane) value for this drum type
                enemy_type = drum_to_enemy_type.get(drum_type, 1)  # Default to regular enemy (1) if unknown
                aux = drum_to_aux.get(drum_type, 7)  # Default to lane 7 if unknown
                color1, color2 = drum_to_colors.get(drum_type, (2, 2))  # Default colors
                
                # Write row in Drums Rock format 
                writer.writerow([
                    f"{time:.2f}",
                    str(enemy_type),
                    str(color1),
                    str(color2),
                    "1",
                    "",
                    str(aux)
                ])
            
            # Make sure we have some notes
            if len(cleaned_events) < 10:
                # Add some basic pattern as fallback
                logging.warning("Not enough events detected, falling back to basic pattern")
                return generate_fixed_basic_notes_csv(output_path, song_duration)
                
            # Ensure enemy data spans the song duration
            if cleaned_events and cleaned_events[-1][0] < song_duration - 10:
                writer.writerow([
                    f"{song_duration - 5:.2f}",
                    "1",
                    "2",
                    "2",
                    "1",
                    "",
                    "7"
                ])
        
        logging.info(f"Generated drum-synced notes.csv at {output_path} with {len(cleaned_events)} total beats")
        return True
        
    except Exception as e:
        logging.error(f"Failed to generate drum-synced notes: {str(e)}", exc_info=True)
        return generate_fixed_basic_notes_csv(output_path, song_duration)

def detect_drum_type(y_slice, sr, drum_bands):
    """
    NEW: Determine the most likely drum type based on spectral energy
    """
    # Compute short-time Fourier transform for frequency analysis
    D = np.abs(librosa.stft(y_slice, n_fft=1024, hop_length=256))
    
    # Check energy in different bands
    band_energies = {}
    
    for drum_type, (low_freq, high_freq) in drum_bands.items():
        # Convert frequencies to bin indices
        low_bin = librosa.core.hz_to_fft_bin(low_freq, sr=sr, n_fft=D.shape[0]*2-1)
        high_bin = librosa.core.hz_to_fft_bin(high_freq, sr=sr, n_fft=D.shape[0]*2-1)
        
        # Bound the bins to valid range
        low_bin = max(0, min(low_bin, D.shape[0]-1))
        high_bin = max(low_bin+1, min(high_bin, D.shape[0]-1))
        
        # Calculate band energy
        band_energies[drum_type] = np.sum(D[low_bin:high_bin, :])
    
    # Find the drum type with highest energy
    if band_energies:
        max_drum = max(band_energies.items(), key=lambda x: x[1])[0]
        return max_drum
    
    # Default to kick drum if we can't determine
    return "kick"

def ensure_events_on_beats(events, beat_times, tolerance):
    """
    NEW: Ensure that every detected beat has at least one event
    """
    # For each beat time, check if there's an event within tolerance
    for beat_time in beat_times:
        # Skip beats at the very beginning (first 1 second)
        if beat_time < 1.0:
            continue
            
        # Check if an event exists near this beat
        has_event = False
        for time, _ in events:
            if abs(time - beat_time) < tolerance:
                has_event = True
                break
                
        # If no event on this beat, add a kick drum
        if not has_event:
            events.append((beat_time, "kick"))

def fine_tune_frequency_bands(song_path):
    """Use spectral analysis to fine-tune frequency bands for the specific song"""
    try:
        import librosa
                
        # Load audio
        y, sr = librosa.load(song_path, sr=None)
        
        # IMPROVED: First separate harmonic and percussive parts
        _, y_percussive = librosa.effects.hpss(y)
        
        # Compute spectrogram with better resolution for drum analysis
        D = np.abs(librosa.stft(y_percussive, n_fft=2048, hop_length=512))
        
        # Compute average spectrum to find peaks
        avg_spectrum = np.mean(D, axis=1)
        
        # Find peaks in different frequency regions
        drum_bands = {
            "kick": (40, 100),
            "snare": (180, 320),
            "tom_low": (100, 300),
            "tom_high": (300, 500),
            "crash": (800, 1600),
            "ride": (1500, 4000),
            "hihat": (8000, 15000)  # NEW: Added hi-hat detection
        }
        
        optimized_bands = {}
        
        # IMPROVED: Use peak-finding algorithm to better locate frequency bands
        for drum_type, (min_freq, max_freq) in drum_bands.items():
            min_bin = librosa.core.hz_to_fft_bin(min_freq, sr=sr, n_fft=D.shape[0]*2-1)
            max_bin = librosa.core.hz_to_fft_bin(max_freq, sr=sr, n_fft=D.shape[0]*2-1)
            
            # Bound the bins to avoid index errors
            min_bin = max(0, min(min_bin, len(avg_spectrum)-1))
            max_bin = max(min_bin+1, min(max_bin, len(avg_spectrum)-1))
            
            region_spectrum = avg_spectrum[min_bin:max_bin]
            
            if len(region_spectrum) > 0:
                # Use librosa peak picking to find multiple peaks
                try:
                    peaks = librosa.util.peak_pick(region_spectrum, 
                                                pre_max=10, post_max=10, 
                                                pre_avg=10, post_avg=10, 
                                                delta=0.5, wait=10)
                    
                    if len(peaks) > 0:
                        # Get the strongest peak
                        strongest_peak = min_bin + peaks[np.argmax(region_spectrum[peaks])]
                        peak_freq = librosa.core.fft_bin_to_hz(strongest_peak, sr=sr, n_fft=D.shape[0]*2-1)
                        
                        # Center the band around the peak with appropriate width
                        band_width = (max_freq - min_freq) * 0.7  # Narrower band around peak
                        optimized_bands[drum_type] = (
                            max(min_freq, peak_freq - band_width/2),
                            min(max_freq, peak_freq + band_width/2)
                        )
                    else:
                        # If no peaks found, use defaults with slightly narrower bands
                        mid_freq = (min_freq + max_freq) / 2
                        band_width = (max_freq - min_freq) * 0.8
                        optimized_bands[drum_type] = (
                            max(min_freq, mid_freq - band_width/2),
                            min(max_freq, mid_freq + band_width/2)
                        )
                except:
                    # If peak picking fails, use default bands
                    optimized_bands[drum_type] = (min_freq, max_freq)
            else:
                optimized_bands[drum_type] = (min_freq, max_freq)
        
        logging.info(f"Optimized frequency bands for {os.path.basename(song_path)}: {optimized_bands}")
        return optimized_bands
        
    except Exception as e:
        logging.error(f"Failed to fine-tune frequency bands: {str(e)}", exc_info=True)
        return None

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


def generate_fixed_basic_notes_csv(output_path, song_duration=180.0):
    """Generate completely fixed pattern as last resort"""
    # Original basic pattern generator code from the working version
    logging.info("Using completely fixed basic pattern generation")
    
    try:
        # Create the notes.csv file with exact format Drums Rock expects
        with open(output_path, 'w', newline='') as f:
            writer = csv.writer(f)
            
            # Header row - exactly as in the template
            writer.writerow(["Time [s]", "Enemy Type", "Aux Color 1", "Aux Color 2", "Nº Enemies", "interval", "Aux"])
            
            # Place enemies every 2.5 seconds for the basic rhythm
            current_time = 0.0
            while current_time < song_duration:
                # Regular enemies (type 1, colors 2,2, Aux 7)
                writer.writerow([f"{current_time:.2f}", "1", "2", "2", "1", "", "7"])
                current_time += 2.5
                
                # Every 10 seconds, add a special enemy (type 2, colors 5,6, Aux 5)
                if int(current_time) % 10 == 0:
                    writer.writerow([f"{current_time:.2f}", "2", "5", "6", "1", "", "5"])
                    current_time += 0.5
                
                # Every 20 seconds, add a sequence of timed enemies (type 3 with interval)
                if int(current_time) % 20 == 0:
                    writer.writerow([f"{current_time:.2f}", "3", "2", "2", "1", "2", "7"])
                    current_time += 2.0
                
                # Add variety with some random enemy types
                if random.random() < 0.3:  # 30% chance
                    writer.writerow([f"{(current_time + 0.63):.2f}", "1", "1", "1", "1", "", "6"])
                
                # Add occasional clusters of enemies
                if random.random() < 0.1 and current_time > 30:  # 10% chance after 30 seconds
                    base = current_time
                    writer.writerow([f"{base:.2f}", "2", "2", "4", "1", "", "7"])
                    writer.writerow([f"{(base + 0.32):.2f}", "2", "2", "4", "1", "", "7"])
                    writer.writerow([f"{(base + 0.63):.2f}", "2", "2", "4", "1", "", "7"])
        
        logging.info(f"Generated Drums Rock compatible notes.csv at {output_path}")
        return True
        
    except Exception as e:
        logging.error(f"Failed to generate fixed basic notes: {str(e)}")
        return False

if __name__ == "__main__":
    # Example usage
    if len(sys.argv) > 2:
        song_path = sys.argv[1]
        output_path = sys.argv[2]
        template_path = sys.argv[3] if len(sys.argv) > 3 else None
        generate_notes_csv(song_path, template_path, output_path)
    else:
        print("Usage: python notes_generator.py song_path output_path [template_path]")