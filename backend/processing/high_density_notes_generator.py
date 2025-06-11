import os
import csv
import logging
import numpy as np
import warnings
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def generate_notes_csv(song_path, template_path, output_path):
    """Generate extremely dense notes based on minimal filtering and pattern infilling"""
    try:
        logging.info(f"Generating high-density notes for {os.path.basename(song_path)}")
        
        # Try to use librosa for analysis
        try:
            import librosa
            
            # Suppress warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                
                # Load the audio file
                y, sr = librosa.load(song_path, sr=None)
                
                # Get song duration
                song_duration = librosa.get_duration(y=y, sr=sr)
                logging.info(f"Song duration: {song_duration:.2f} seconds")
                
                # Detect the tempo
                tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
                logging.info(f"Detected tempo: {tempo:.2f} BPM")
                
                # MASSIVE CHANGE: Use aggressive onset detection with multiple methods
                logging.info("Using aggressive onset detection...")
                high_density_events = generate_high_density_events(y, sr, tempo, song_duration)
                
                # Generate the notes CSV
                success = write_high_density_notes_csv(high_density_events, song_duration, tempo, output_path)
                
                if success:
                    logging.info(f"Successfully generated high-density notes at {output_path}")
                    return True
                
        except ImportError:
            logging.warning("Could not import librosa, falling back to basic pattern")
        except Exception as e:
            logging.error(f"Error in high-density generation: {str(e)}")
        
        # Fallback to dense pattern
        return generate_dense_pattern_csv(song_path, output_path, song_duration=180.0)
        
    except Exception as e:
        logging.error(f"Failed to generate notes.csv: {str(e)}")
        return False

def generate_high_density_events(y, sr, tempo, song_duration):
    """Generate extremely dense note events using multiple detection methods"""
    import librosa
    
    events = []
    
    # Calculate time between 16th notes (common in drum patterns)
    beat_duration = 60 / tempo
    sixteenth_duration = beat_duration / 4
    
    # 1. EXTREMELY LOW THRESHOLD ONSET DETECTION
    # Extract percussive component
    y_harmonic, y_percussive = librosa.effects.hpss(y)
    
    # Use an absurdly low threshold to catch nearly everything
    onset_env = librosa.onset.onset_strength(y=y_percussive, sr=sr)
    onset_frames = librosa.onset.onset_detect(
        onset_envelope=onset_env, sr=sr,
        threshold=0.0001,  # Ultra-low threshold
        pre_max=0.02*sr//512,  # Smaller window to catch more events
        post_max=0.02*sr//512,
        pre_avg=0.05*sr//512,
        post_avg=0.05*sr//512
    )
    onset_times = librosa.frames_to_time(onset_frames, sr=sr)
    
    # Add detected onsets as events
    for i, time in enumerate(onset_times):
        # Alternate between kick and hihat
        drum_type = "kick" if i % 3 == 0 else ("snare" if i % 3 == 1 else "hihat")
        events.append((time, drum_type))
    
    logging.info(f"Detected {len(onset_times)} primary onsets")
    
    # 2. RMS ENERGY BASED DETECTION
    # Compute RMS energy
    rms = librosa.feature.rms(y=y)[0]
    
    # Find peaks in RMS with extremely low threshold
    rms_peaks = librosa.util.peak_pick(
        rms, 
        pre_max=3,  # Very small windows
        post_max=3,
        pre_avg=10,
        post_avg=10,
        delta=0.0001,  # Ultra-low threshold
        wait=1
    )
    
    # Convert frames to times
    rms_times = librosa.frames_to_time(rms_peaks, sr=sr, hop_length=512)
    
    # Add detected RMS peaks as events
    for time in rms_times:
        # Add as kick drums (strong beats)
        events.append((time, "kick"))
    
    logging.info(f"Detected {len(rms_times)} RMS peaks")
    
    # 3. SPECTRAL FLUX BASED DETECTION
    flux = librosa.onset.onset_strength(
        y=y, sr=sr,
        feature=librosa.feature.spectral_flux
    )
    
    # Find peaks in flux with extremely low threshold
    flux_peaks = librosa.util.peak_pick(
        flux, 
        pre_max=3,
        post_max=3,
        pre_avg=10,
        post_avg=10,
        delta=0.0001,  # Ultra-low threshold
        wait=1
    )
    
    # Convert frames to times
    flux_times = librosa.frames_to_time(flux_peaks, sr=sr, hop_length=512)
    
    # Add detected flux peaks as events
    for time in flux_times:
        # Add as hihat drums (sharp attacks)
        events.append((time, "hihat"))
    
    logging.info(f"Detected {len(flux_times)} spectral flux peaks")
    
    # 4. HIGH FREQUENCY CONTENT DETECTION (for cymbals)
    # Filter to high frequencies
    from scipy.signal import butter, sosfilt
    
    def butter_highpass(cutoff, fs, order=5):
        nyq = 0.5 * fs
        normal_cutoff = cutoff / nyq
        sos = butter(order, normal_cutoff, btype='high', analog=False, output='sos')
        return sos
    
    def highpass_filter(data, cutoff, fs, order=5):
        sos = butter_highpass(cutoff, fs, order=order)
        y = sosfilt(sos, data)
        return y
    
    # High-pass filter to focus on cymbal frequencies
    y_high = highpass_filter(y, cutoff=5000, fs=sr)
    
    # Detect onsets in high-frequency content
    onset_high = librosa.onset.onset_strength(y=y_high, sr=sr)
    onset_high_frames = librosa.onset.onset_detect(
        onset_envelope=onset_high,
        sr=sr,
        threshold=0.0001
    )
    
    # Convert frames to times
    onset_high_times = librosa.frames_to_time(onset_high_frames, sr=sr)
    
    # Add detected high-frequency onsets as events
    for time in onset_high_times:
        # Add as crash cymbals
        events.append((time, "crash"))
    
    logging.info(f"Detected {len(onset_high_times)} high-frequency onsets")
    
    # 5. PATTERN INFILLING
    # If the detection found less than ~800 events, fill in with pattern-based notes
    if len(events) < 800:
        logging.info(f"Detected only {len(events)} events, filling with pattern-based notes")
        
        # Determine the note density needed
        target_density = 800 / song_duration  # Notes per second
        detected_density = len(events) / song_duration
        
        # How many pattern notes to add per second
        notes_to_add_per_second = max(0, target_density - detected_density)
        
        # Fill with 16th note patterns where detection is sparse
        detected_times = [time for time, _ in events]
        pattern_events = []
        
        # Add regular patterns between detected events
        for i in range(int(song_duration * notes_to_add_per_second)):
            time = i / notes_to_add_per_second
            
            # Check if this time is far from any detected event
            is_far = True
            for detected_time in detected_times:
                if abs(detected_time - time) < sixteenth_duration * 0.5:
                    is_far = False
                    break
            
            # If this time doesn't conflict with a detected event, add it
            if is_far:
                drum_type = "hihat" if i % 4 != 0 else ("kick" if i % 8 == 0 else "snare")
                pattern_events.append((time, drum_type))
        
        # Add pattern events
        events.extend(pattern_events)
        logging.info(f"Added {len(pattern_events)} pattern-based events")
    
    # Sort all events by time
    events.sort(key=lambda x: x[0])
    
    # 6. REMOVE EXCESSIVE DUPLICATION
    # We want high density but not ridiculous duplication
    cleaned_events = []
    last_time = -1
    
    for time, drum_type in events:
        # Only filter if notes are extremely close (less than 1/32nd note)
        if last_time < 0 or time - last_time > sixteenth_duration * 0.5:
            cleaned_events.append((time, drum_type))
            last_time = time
    
    logging.info(f"Final event count after cleaning: {len(cleaned_events)}")
    
    return cleaned_events

def write_high_density_notes_csv(events, song_duration, tempo, output_path):
    """Write the high-density events to a CSV file in Drums Rock format"""
    try:
        # Map drum types to enemy types and colors
        drum_to_enemy_type = {
            "kick": 1,
            "snare": 1, 
            "hihat": 1,
            "crash": 2,
            "ride": 3
        }
        
        drum_to_aux = {
            "kick": 7,
            "snare": 7,
            "hihat": 6,
            "crash": 5,
            "ride": 5
        }
        
        drum_to_colors = {
            "kick": (2, 2),
            "snare": (2, 2),
            "hihat": (1, 1),
            "crash": (5, 6),
            "ride": (2, 4)
        }
        
        with open(output_path, 'w', newline='') as f:
            writer = csv.writer(f)
            
            # Header row
            writer.writerow(["Time [s]", "Enemy Type", "Aux Color 1", "Aux Color 2", "Nº Enemies", "interval", "Aux"])
            
            # Process each event
            for time, drum_type in events:
                # Skip if beyond song duration
                if time >= song_duration:
                    continue
                    
                enemy_type = drum_to_enemy_type.get(drum_type, 1)
                aux = drum_to_aux.get(drum_type, 7)
                color1, color2 = drum_to_colors.get(drum_type, (2, 2))
                
                # Write to CSV
                writer.writerow([
                    f"{time:.2f}",
                    str(enemy_type),
                    str(color1),
                    str(color2),
                    "1",
                    "",
                    str(aux)
                ])
        
        return True
    except Exception as e:
        logging.error(f"Failed to write high-density notes: {str(e)}")
        return False

def generate_dense_pattern_csv(song_path, output_path, song_duration=180.0):
    """Generate a dense pattern as fallback"""
    try:
        # Try to get actual duration
        try:
            import librosa
            y, sr = librosa.load(song_path, sr=None)
            song_duration = librosa.get_duration(y=y, sr=sr)
            
            # Try to detect tempo
            tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
        except:
            tempo = 120  # Default tempo
        
        with open(output_path, 'w', newline='') as f:
            writer = csv.writer(f)
            
            # Header row
            writer.writerow(["Time [s]", "Enemy Type", "Aux Color 1", "Aux Color 2", "Nº Enemies", "interval", "Aux"])
            
            # Calculate 16th note duration
            beat_duration = 60 / tempo
            sixteenth_duration = beat_duration / 4
            
            # Generate very dense pattern (16th notes)
            current_time = 0.0
            
            while current_time < song_duration:
                # Every beat (quarter note)
                if current_time % beat_duration < 0.01:
                    # Downbeat (every 4 beats)
                    if int(current_time / beat_duration) % 4 == 0:
                        writer.writerow([f"{current_time:.2f}", "1", "2", "2", "1", "", "7"])  # Kick
                        writer.writerow([f"{current_time:.2f}", "2", "5", "6", "1", "", "5"])  # Crash
                    # Beat 3
                    elif int(current_time / beat_duration) % 4 == 2:
                        writer.writerow([f"{current_time:.2f}", "1", "2", "2", "1", "", "7"])  # Kick
                    # Beats 2 and 4
                    else:
                        writer.writerow([f"{current_time:.2f}", "1", "2", "2", "1", "", "7"])  # Snare
                # Every 16th note gets a hihat
                writer.writerow([f"{current_time:.2f}", "1", "1", "1", "1", "", "6"])  # Hihat
                
                # Advance by 16th note
                current_time += sixteenth_duration
        
        logging.info(f"Generated dense fallback pattern at {output_path}")
        return True
    except Exception as e:
        logging.error(f"Failed to generate dense fallback pattern: {str(e)}")
        return False

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 2:
        song_path = sys.argv[1]
        output_path = sys.argv[2]
        generate_notes_csv(song_path, None, output_path)
    else:
        print("Usage: python high_density_notes_generator.py song_path output_path")