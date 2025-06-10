import os
import csv
import logging
import warnings
import subprocess
import tempfile
import shutil
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
        
        # Try drum separation with Spleeter first
        drum_track = try_extract_drums_with_spleeter(song_path)
        
        # Use the drum track if available, otherwise use original song
        audio_for_analysis = drum_track if drum_track else song_path
        
        # Try advanced beat detection with librosa
        try:
            import numpy as np
            import librosa
            
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
                tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
                logging.info(f"Detected tempo: {tempo:.2f} BPM")
                
                # Fine-tune frequency bands for this specific song
                optimized_bands = fine_tune_frequency_bands(audio_for_analysis)
                
                # Generate drum-specific beat data
                success = generate_drum_synced_notes(y, sr, song_duration, tempo, output_path, optimized_bands)
                
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
        
        # Check if conda is available
        conda_available = False
        try:
            subprocess.run(["conda", "--version"], check=True, capture_output=True)
            conda_available = True
        except (subprocess.SubprocessError, FileNotFoundError):
            logging.info("Conda not found, trying direct pip installation")
        
        if conda_available:
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
            
        else:
            # Try using pip and subprocess directly
            try:
                # Create a virtualenv
                venv_dir = os.path.join(temp_dir, "venv")
                subprocess.run(["python", "-m", "venv", venv_dir], check=True)
                
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
            
            except Exception as e:
                logging.warning(f"Failed to extract drums with pip: {str(e)}")
        
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

def generate_drum_synced_notes(y, sr, song_duration, tempo, output_path, optimized_bands=None):
    """Generate notes.csv with specialized drum type detection and lane mapping"""
    try:
        import numpy as np
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
            "ride": (1500, 4000)
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
            "ride": 1      # Regular enemy
        }
        
        # Map drum types to Aux values (lane numbers in Drums Rock)
        drum_to_aux = {
            "snare": 1,
            "kick": 2,
            "tom_high": 3,
            "tom_low": 4,
            "crash": 5,
            "ride": 6
        }
        
        # ADAPTIVE PARAMETERS:
        # Calculate adaptive onset detection threshold
        onset_threshold = calculate_adaptive_threshold(y, sr, tempo)
        
        # Calculate adaptive minimum beat spacing
        min_beat_spacing = calculate_adaptive_beat_spacing(y, sr, tempo)
        
        # Calculate adaptive energy significance threshold
        energy_significance = calculate_adaptive_energy_threshold(y, sr)
        
        # Generate onset envelope
        onset_env = librosa.onset.onset_strength(
            y=y, sr=sr,
            hop_length=512,
            aggregate=np.median  # Use median for sharper drum detection
        )
        
        # Detect onsets with adaptive threshold
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
        
        # Extract drum events with better detection
        drum_events = []
        
        # Compute STFT for frequency analysis
        D = np.abs(librosa.stft(y, n_fft=2048, hop_length=512))
        
        # Process each onset
        for i, onset_time in enumerate(onset_times):
            if i >= len(onset_frames):
                continue
                
            frame = onset_frames[i]
            
            # Skip if too close to previous beat (adaptive spacing)
            if i > 0 and onset_time - onset_times[i-1] < min_beat_spacing:
                continue
                
            # Check which band has the most energy at this onset
            band_energies = {}
            for drum_type, (low_freq, high_freq) in drum_bands.items():
                # Convert frequencies to bin indices
                low_bin = librosa.core.hz_to_fft_bin(low_freq, sr=sr, n_fft=D.shape[0]*2-1)
                high_bin = librosa.core.hz_to_fft_bin(high_freq, sr=sr, n_fft=D.shape[0]*2-1)
                
                # Bound the bins to valid range
                low_bin = max(0, min(low_bin, D.shape[0]-1))
                high_bin = max(low_bin+1, min(high_bin, D.shape[0]-1))
                
                # Calculate band energy at this frame
                if frame < D.shape[1]:
                    band_energies[drum_type] = np.sum(D[low_bin:high_bin, frame])
            
            # Find the drum type with highest energy
            if band_energies:
                max_drum = max(band_energies.items(), key=lambda x: x[1])[0]
                max_energy = band_energies[max_drum]
                
                # Only include if energy is significant (adaptive threshold)
                avg_energy = np.mean(list(band_energies.values()))
                if max_energy > avg_energy * energy_significance:
                    drum_events.append((onset_time, max_drum))
        
        # Sort events by time
        drum_events.sort(key=lambda x: x[0])
        
        # Write the CSV with the CORRECT Drums Rock format
        with open(output_path, 'w', newline='') as f:
            writer = csv.writer(f)
            # CORRECT HEADERS FOR DRUMS ROCK
            writer.writerow(["Time [s]", "Enemy Type", "Aux Color 1", "Aux Color 2", "N° Enemies", "interval", "Aux"])
            
            # Process each drum event
            for time, drum_type in drum_events:
                # Get enemy type and aux (lane) value for this drum type
                enemy_type = drum_to_enemy_type.get(drum_type, 1)  # Default to regular enemy (1) if unknown
                aux = drum_to_aux.get(drum_type, 1)  # Default to lane 1 if unknown
                
                # All aux values should match for consistency
                aux_color1 = aux
                aux_color2 = aux
                num_enemies = "1"
                interval = ""
                
                # Write row in Drums Rock format
                writer.writerow([
                    f"{time:.2f}",  # Time with 2 decimal places
                    enemy_type,
                    aux_color1,
                    aux_color2,
                    num_enemies,
                    interval,
                    aux
                ])
            
            # Ensure enemy data spans the song duration
            if len(drum_events) == 0 or drum_events[-1][0] < song_duration - 10:
                writer.writerow([
                    f"{song_duration - 5:.2f}",  # Time
                    1,                           # Enemy Type (regular)
                    2,                           # Aux Color 1 (kick lane)
                    2,                           # Aux Color 2 (kick lane)
                    1,                           # Number of Enemies
                    "",                          # interval
                    2                            # Aux (kick lane)
                ])
        
        logging.info(f"Generated drum-synced notes.csv at {output_path} with {len(drum_events)} total beats")
        return True
        
    except Exception as e:
        logging.error(f"Failed to generate drum-synced notes: {str(e)}", exc_info=True)
        return generate_basic_notes_csv(None, output_path, song_duration)

def fine_tune_frequency_bands(song_path):
    """Use spectral analysis to fine-tune frequency bands for the specific song"""
    try:
        import numpy as np
        import librosa
        
        # Load audio
        y, sr = librosa.load(song_path, sr=None)
        
        # Compute spectrogram with better resolution for drum analysis
        D = np.abs(librosa.stft(y, n_fft=2048, hop_length=512))
        
        # Compute average spectrum to find peaks
        avg_spectrum = np.mean(D, axis=1)
        
        # Find peaks in different frequency regions
        drum_bands = {
            "kick": (0, 150),
            "snare": (150, 400),
            "tom_low": (100, 300),
            "tom_high": (300, 500),
            "crash": (800, 1600),
            "ride": (1500, 4000)
        }
        
        optimized_bands = {}
        
        for drum_type, (min_freq, max_freq) in drum_bands.items():
            min_bin = librosa.core.hz_to_fft_bin(min_freq, sr=sr, n_fft=D.shape[0]*2-1)
            max_bin = librosa.core.hz_to_fft_bin(max_freq, sr=sr, n_fft=D.shape[0]*2-1)
            
            # Bound the bins to avoid index errors
            min_bin = max(0, min(min_bin, len(avg_spectrum)-1))
            max_bin = max(min_bin+1, min(max_bin, len(avg_spectrum)-1))
            
            region_spectrum = avg_spectrum[min_bin:max_bin]
            if len(region_spectrum) > 0:
                peak_idx = np.argmax(region_spectrum) + min_bin
                peak_freq = librosa.core.fft_bin_to_hz(peak_idx, sr=sr, n_fft=D.shape[0]*2-1)
                
                # Center the band around the peak
                band_width = (max_freq - min_freq) * 0.7  # Narrower band around peak
                optimized_bands[drum_type] = (
                    max(min_freq, peak_freq - band_width/2),
                    min(max_freq, peak_freq + band_width/2)
                )
            else:
                optimized_bands[drum_type] = (min_freq, max_freq)
        
        logging.info(f"Optimized frequency bands for {os.path.basename(song_path)}: {optimized_bands}")
        return optimized_bands
        
    except Exception as e:
        logging.error(f"Failed to fine-tune frequency bands: {str(e)}", exc_info=True)
        return None

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
    # Original basic pattern generator code
    logging.info("Using completely fixed basic pattern generation")
    
    try:
        # Fixed tempo
        bpm = 120
        beat_duration = 60 / bpm
        
        with open(output_path, 'w', newline='') as f:
            writer = csv.writer(f)
            
            # CORRECT HEADERS FOR DRUMS ROCK
            writer.writerow(["Time [s]", "Enemy Type", "Aux Color 1", "Aux Color 2", "N° Enemies", "interval", "Aux"])
            
            # Generate a simple fixed pattern
            measures = int(song_duration / (4 * beat_duration))
            for measure in range(measures):
                base_time = measure * 4 * beat_duration
                
                # Kick on 1 and 3
                writer.writerow([
                    f"{base_time:.2f}", 1, 2, 2, 1, "", 2  # Kick
                ])
                writer.writerow([
                    f"{base_time + 2 * beat_duration:.2f}", 1, 2, 2, 1, "", 2  # Kick
                ])
                
                # Snare on 2 and 4
                writer.writerow([
                    f"{base_time + beat_duration:.2f}", 1, 1, 1, 1, "", 1  # Snare
                ])
                writer.writerow([
                    f"{base_time + 3 * beat_duration:.2f}", 1, 1, 1, 1, "", 1  # Snare
                ])
        
        logging.info(f"Generated fixed basic notes.csv at {output_path}")
        return True
        
    except Exception as e:
        logging.error(f"Failed to generate fixed basic notes: {str(e)}", exc_info=True)
        return False

if __name__ == "__main__":
    # Example usage
    import sys
    if len(sys.argv) > 2:
        song_path = sys.argv[1]
        output_path = sys.argv[2]
        template_path = sys.argv[3] if len(sys.argv) > 3 else None
        generate_notes_csv(song_path, template_path, output_path)
    else:
        print("Usage: python notes_generator.py song_path output_path [template_path]")