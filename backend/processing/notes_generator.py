import os
import csv
import logging
import warnings

def generate_notes_csv(song_path, template_path, output_path):
    """
    Generate a notes.csv file with enemy spawns synchronized to the detected beat of the song.
    Falls back to simpler methods if advanced analysis fails.
    """
    try:
        logging.info(f"Generating Drums Rock-compatible notes for {os.path.basename(song_path)}")
        
        # Try advanced beat detection with librosa
        try:
            import numpy as np
            import librosa
            
            logging.info("Using librosa for advanced tempo detection")
            
            # Suppress warnings from librosa
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                
                # Load the audio file
                y, sr = librosa.load(song_path, sr=None)
                
                # Get song duration
                song_duration = librosa.get_duration(y=y, sr=sr)
                logging.info(f"Song duration: {song_duration:.2f} seconds")
                
                # Detect the tempo
                tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
                logging.info(f"Detected tempo: {tempo:.2f} BPM")
                
                # Get beat frames and convert to time
                _, beat_frames = librosa.beat.beat_track(y=y, sr=sr, units='frames')
                beat_times = librosa.frames_to_time(beat_frames, sr=sr)
                
                # Advanced tempo-synchronized enemy generation
                return generate_tempo_synced_notes(beat_times, tempo, song_duration, output_path)
        
        except ImportError:
            logging.warning("Librosa not available, falling back to basic tempo estimation")
            return generate_basic_notes_csv(song_path, output_path)
        except Exception as e:
            logging.error(f"Advanced tempo detection failed: {str(e)}", exc_info=True)
            logging.warning("Falling back to basic tempo estimation")
            return generate_basic_notes_csv(song_path, output_path)
            
    except Exception as e:
        logging.error(f"Failed to generate notes.csv: {str(e)}", exc_info=True)
        return False

def generate_tempo_synced_notes(beat_times, tempo, song_duration, output_path):
    """Generate notes.csv with precise beat synchronization"""
    try:
        with open(output_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["Time [s]", "Enemy Type", "Aux Color 1", "Aux Color 2", "Nº Enemies", "interval", "Aux"])
            
            # Track measure position
            measure_beat = 0
            
            # Generate enemies synchronized to detected beats
            for beat_idx, beat_time in enumerate(beat_times):
                # Skip first few beats for intro
                if beat_idx < 4:
                    continue
                
                # Update measure position (assuming 4/4 time)
                measure_beat = beat_idx % 4
                
                # Basic pattern: Main beats get enemies
                if measure_beat == 0:  # First beat of measure
                    writer.writerow([f"{beat_time:.2f}", "1", "2", "2", "1", "", "7"])
                
                # Second beat of measure - less frequent
                if measure_beat == 1 and beat_idx % 8 == 1:
                    writer.writerow([f"{beat_time:.2f}", "1", "5", "5", "1", "", "5"])
                
                # Third beat - every other measure
                if measure_beat == 2 and beat_idx % 8 >= 4:
                    writer.writerow([f"{beat_time:.2f}", "1", "1", "1", "1", "", "6"])
                
                # Fourth beat - special patterns
                if measure_beat == 3:
                    if beat_idx % 16 == 15:  # End of every 4 measures
                        writer.writerow([f"{beat_time:.2f}", "2", "2", "4", "1", "", "7"])
                    elif beat_idx % 32 == 31:  # End of every 8 measures
                        writer.writerow([f"{beat_time:.2f}", "3", "2", "2", "1", "4", "7"])
            
            # Ensure enemy data spans the song duration
            if len(beat_times) > 0 and beat_times[-1] < song_duration - 10:
                writer.writerow([f"{song_duration - 5:.2f}", "1", "2", "2", "1", "", "7"])
        
        logging.info(f"Generated tempo-synced notes.csv at {output_path}")
        return True
        
    except Exception as e:
        logging.error(f"Failed to generate tempo-synced notes: {str(e)}", exc_info=True)
        return generate_basic_notes_csv(None, output_path, song_duration)

def generate_basic_notes_csv(song_path, output_path, song_duration=180.0):
    """Generate notes.csv with basic, fixed BPM patterns"""
    logging.info("Using basic fixed-BPM pattern generation")
    
    try:
        # Try to get duration from song_path if available
        if song_path and os.path.exists(song_path):
            try:
                from pydub import AudioSegment
                audio = AudioSegment.from_file(song_path)
                song_duration = len(audio) / 1000.0  # Convert ms to seconds
                logging.info(f"Got song duration from pydub: {song_duration:.2f} seconds")
            except Exception as e:
                logging.warning(f"Could not get duration from audio file: {e}")
        
        # Fixed tempo
        bpm = 120
        beat_duration = 60 / bpm
        
        with open(output_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["Time [s]", "Enemy Type", "Aux Color 1", "Aux Color 2", "Nº Enemies", "interval", "Aux"])
            
            # Generate a basic pattern
            measures = int(song_duration / (4 * beat_duration))
            for measure in range(measures):
                base_time = measure * 4 * beat_duration
                
                # First beat of every measure
                writer.writerow([f"{base_time:.2f}", "1", "2", "2", "1", "", "7"])
                
                # Second beat of some measures
                if measure % 2 == 0:
                    time = base_time + beat_duration
                    writer.writerow([f"{time:.2f}", "1", "5", "5", "1", "", "5"])
                
                # Third beat
                if measure % 2 == 1:
                    time = base_time + (2 * beat_duration)
                    writer.writerow([f"{time:.2f}", "1", "1", "1", "1", "", "6"])
                
                # Fourth beat - special patterns
                if measure % 4 == 3:
                    time = base_time + (3 * beat_duration)
                    writer.writerow([f"{time:.2f}", "2", "2", "4", "1", "", "7"])
                
                # Add interval enemies occasionally
                if measure % 8 == 7:
                    time = base_time + (3.5 * beat_duration)
                    writer.writerow([f"{time:.2f}", "3", "2", "2", "1", "3", "7"])
        
        logging.info(f"Generated basic notes.csv at {output_path}")
        return True
        
    except Exception as e:
        logging.error(f"Failed to generate basic notes: {str(e)}", exc_info=True)
        return False