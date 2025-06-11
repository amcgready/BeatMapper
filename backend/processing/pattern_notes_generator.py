import os
import csv
import logging
import numpy as np
import warnings
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def generate_notes_csv(song_path, template_path, output_path):
    """
    Generate drum notes based on pattern recognition instead of individual hit detection.
    """
    try:
        logging.info(f"Generating pattern-based drum notes for {os.path.basename(song_path)}")
        
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
                logging.info(f"Song duration: {song_duration:.2f} seconds")
                
                # Detect the tempo
                tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
                logging.info(f"Detected tempo: {tempo:.2f} BPM")
                
                # Extract drum patterns and generate notes
                success = generate_pattern_based_notes(y, sr, tempo, beats, song_duration, output_path)
                
                if success:
                    logging.info(f"Successfully generated notes.csv at {output_path}")
                    return True
                
        except ImportError:
            logging.warning("Could not import librosa, falling back to basic pattern")
        except Exception as e:
            logging.error(f"Error with analysis: {str(e)}")
        
        # Fallback to basic pattern
        generate_basic_notes_csv(song_path, output_path)
        return True
        
    except Exception as e:
        logging.error(f"Failed to generate notes.csv: {str(e)}")
        return False

def generate_pattern_based_notes(y, sr, tempo, beats, song_duration, output_path):
    """
    Generate notes based on detected patterns rather than individual hits.
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
                    segment = y_percussive[start_sample:end_sample]
                    
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
        return False

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
                return "basic_rock"  # Basic rock pattern
        else:  # Lower energy
            return "half_time"  # Half-time feel
            
    except:
        # Default to basic rock if analysis fails
        return "basic_rock"

def generate_basic_notes_csv(song_path, output_path, song_duration=180.0):
    """
    Generate a very basic notes.csv file if all else fails.
    """
    try:
        # Estimate duration if possible
        try:
            import librosa
            y, sr = librosa.load(song_path, sr=None)
            song_duration = librosa.get_duration(y=y, sr=sr)
        except:
            pass
        
        with open(output_path, 'w', newline='') as f:
            writer = csv.writer(f)
            
            # Header row
            writer.writerow(["Time [s]", "Enemy Type", "Aux Color 1", "Aux Color 2", "Nº Enemies", "interval", "Aux"])
            
            # Place enemies every 2 seconds for the basic rhythm
            current_time = 0.0
            while current_time < song_duration:
                # Regular enemies (type 1, colors 2,2, Aux 7)
                writer.writerow([f"{current_time:.2f}", "1", "2", "2", "1", "", "7"])
                current_time += 1.0
                
                # Every 8 seconds, add a special enemy
                if int(current_time) % 8 == 0:
                    writer.writerow([f"{current_time:.2f}", "2", "5", "6", "1", "", "5"])
        
        logging.info(f"Generated basic notes.csv at {output_path}")
        return True
        
    except Exception as e:
        logging.error(f"Failed to generate basic notes.csv: {str(e)}")
        return False

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 2:
        generate_notes_csv(sys.argv[1], None, sys.argv[2])
    else:
        print("Usage: python pattern_notes_generator.py song_path output_path")