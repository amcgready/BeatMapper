"""
Simplified adaptive difficulty system that avoids problematic librosa API calls.
"""
import logging
import csv
import os

logger = logging.getLogger(__name__)

def generate_adaptive_notes_csv(song_path, midi_path, output_path, target_difficulty):
    """
    Generate notes.csv with adaptive difficulty using a simplified, reliable approach.
    """
    target_densities = {
        "EASY": 0.8,      # Very relaxed - about 1 note per 1.25 seconds
        "MEDIUM": 1.5,    # Moderate - about 1 note per 0.67 seconds  
        "HARD": 2.5,      # Challenging - about 1 note per 0.4 seconds
        "EXTREME": 4.0    # Maximum - about 1 note per 0.25 seconds
    }
    
    target_density = target_densities.get(target_difficulty, 1.5)
    
    try:
        # Import required libraries
        import librosa
        import numpy as np
        
        # Load audio
        y, sr = librosa.load(song_path, sr=None)
        duration = len(y) / sr
        
        # Calculate target number of notes        target_note_count = int(duration * target_density)
        
        logger.info(f"Adaptive system: targeting {target_note_count} notes for {target_difficulty} "
                   f"(density: {target_density:.2f} notes/sec, duration: {duration:.1f}s)")
        
        # Debug logging
        debug_file = "c:/temp/beatmapper_debug.txt"
        try:
            with open(debug_file, "a") as f:
                f.write(f"Starting beat tracking for {target_difficulty}, duration: {duration:.1f}s\n")
        except:
            pass
        
        # Use a simplified approach: beat tracking + subdivisions
        try:
            # Get beats using librosa with more basic parameters to avoid API issues
            try:
                tempo, beats = librosa.beat.beat_track(y=y, sr=sr, hop_length=512, start_bpm=120.0)
                beat_times = librosa.frames_to_time(beats, sr=sr, hop_length=512)
            except Exception as beat_error:
                logger.warning(f"Beat tracking with parameters failed: {beat_error}, trying simpler approach")
                # Even simpler approach
                tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
                beat_times = librosa.frames_to_time(beats, sr=sr)
            
            # Filter beats to start after 3.0s
            beat_times = [t for t in beat_times if t >= 3.0]
            
            logger.info(f"Found {len(beat_times)} beats, tempo: {tempo:.1f} BPM")
            
            # Generate note candidates based on difficulty
            note_candidates = []
            
            # Always include main beats
            note_candidates.extend(beat_times)
            
            # Add subdivisions based on difficulty
            if target_difficulty in ["MEDIUM", "HARD", "EXTREME"]:
                # Add half-beats (off-beats)
                for i in range(len(beat_times) - 1):
                    half_beat = beat_times[i] + (beat_times[i+1] - beat_times[i]) / 2
                    note_candidates.append(half_beat)
            
            if target_difficulty in ["HARD", "EXTREME"]:
                # Add quarter-beats
                for i in range(len(beat_times) - 1):
                    interval = beat_times[i+1] - beat_times[i]
                    quarter1 = beat_times[i] + interval / 4
                    quarter3 = beat_times[i] + 3 * interval / 4
                    note_candidates.extend([quarter1, quarter3])
            
            if target_difficulty == "EXTREME":
                # Add eighth-beats for extreme difficulty
                for i in range(len(beat_times) - 1):
                    interval = beat_times[i+1] - beat_times[i]
                    for j in range(1, 8):  # Add 7 subdivisions between beats
                        if j not in [2, 4, 6]:  # Skip ones we already added
                            eighth = beat_times[i] + j * interval / 8
                            note_candidates.append(eighth)
            
            # Remove duplicates and sort
            note_candidates = sorted(list(set([round(t, 2) for t in note_candidates])))
            
            logger.info(f"Generated {len(note_candidates)} note candidates")
              # Select subset to match target count
            if len(note_candidates) > target_note_count:
                # For EASY: take every Nth beat to reduce density while preserving musical timing
                if target_difficulty == "EASY":
                    # Take every 3rd or 4th beat to maintain musical feel but reduce density
                    step = max(2, len(note_candidates) // target_note_count)
                    selected_notes = note_candidates[::step][:target_note_count]
                elif target_difficulty == "MEDIUM":
                    # Take every 2nd beat  
                    step = max(2, len(note_candidates) // target_note_count)
                    selected_notes = note_candidates[::step][:target_note_count]
                else:
                    # For HARD/EXTREME: take all available up to target
                    selected_notes = note_candidates[:target_note_count]
            else:
                selected_notes = note_candidates
            
            # Ensure minimum spacing for playability
            min_spacing = 0.1  # 100ms minimum between notes
            filtered_notes = []
            last_time = 0
            
            for note_time in sorted(selected_notes):
                if note_time - last_time >= min_spacing:
                    filtered_notes.append(note_time)
                    last_time = note_time            
            selected_notes = filtered_notes
              except Exception as e:
            logger.error(f"Beat tracking failed: {e}")
            
            # Debug logging - save error details
            debug_file = "c:/temp/beatmapper_debug.txt"
            try:
                with open(debug_file, "a") as f:
                    f.write(f"Beat tracking error: {e}\n")
                    import traceback
                    f.write(f"Traceback: {traceback.format_exc()}\n")
                    f.write(f"Adaptive system failed - returning False to allow other generators to try\n")
            except:
                pass
            
            # For beat alignment, we don't want to fall back to generic patterns
            # Instead, return False so other beat-aware generators can be tried
            logger.info("Returning False to allow other beat-aligned generators to attempt")
            return False
        
        logger.info(f"Final selection: {len(selected_notes)} notes")
        
        # Write to CSV
        with open(output_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["Time [s]", "Enemy Type", "Aux Color 1", "Aux Color 2", "Nº Enemies", "interval", "Aux"])
            
            for i, note_time in enumerate(selected_notes):
                # Vary note types for variety
                if i % 8 == 0:  # Every 8th note is special
                    enemy_type, color1, color2, aux = 2, 5, 6, 5
                elif i % 4 == 0:  # Every 4th note is accent
                    enemy_type, color1, color2, aux = 1, 2, 2, 7
                else:  # Regular notes
                    enemy_type, color1, color2, aux = 1, 1, 1, 6
                
                writer.writerow([
                    f"{note_time:.2f}",
                    str(enemy_type),
                    str(color1),
                    str(color2),
                    "1",
                    "",
                    str(aux)
                ])
        
        # Verify final density
        final_density = len(selected_notes) / duration
        logger.info(f"Final density: {final_density:.2f} notes/sec (target: {target_density:.2f})")
        
        return True
        
    except Exception as e:
        logger.error(f"Error in adaptive notes generation: {e}")
        import traceback
        traceback.print_exc()
        return False
