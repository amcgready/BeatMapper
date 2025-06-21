"""
Simplified adaptive difficulty system for reliable note density control.
"""
import logging
import csv

logger = logging.getLogger(__name__)

def generate_adaptive_notes_csv(song_path, midi_path, output_path, target_difficulty):
    """
    Generate notes.csv with adaptive difficulty that targets specific note densities.
    
    This is a simplified but reliable approach that works across genres.
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
        
        # Calculate target number of notes
        target_note_count = int(duration * target_density)
        
        logger.info(f"Adaptive system: targeting {target_note_count} notes for {target_difficulty} "
                   f"(density: {target_density:.2f} notes/sec, duration: {duration:.1f}s)")
        
        # Generate onset candidates using multiple methods
        onset_candidates = []
          # Method 1: Standard onset detection with low threshold
        onset_env = librosa.onset.onset_strength(y=y, sr=sr)
        try:
            # Try new librosa API first
            onsets1 = librosa.onset.onset_detect(onset_envelope=onset_env, sr=sr, 
                                                threshold=0.1, pre_max=3, post_max=3)
        except TypeError:
            # Fallback for older librosa versions
            onsets1 = librosa.onset.onset_detect(onset_envelope=onset_env, sr=sr, 
                                                delta=0.1, pre_max=3, post_max=3)
        onset_times1 = librosa.frames_to_time(onsets1, sr=sr)
        onset_candidates.extend(onset_times1)
          # Method 2: Percussive component onsets
        y_harmonic, y_percussive = librosa.effects.hpss(y)
        onset_env_perc = librosa.onset.onset_strength(y=y_percussive, sr=sr)
        try:
            # Try new librosa API first
            onsets2 = librosa.onset.onset_detect(onset_envelope=onset_env_perc, sr=sr,
                                                threshold=0.15, pre_max=3, post_max=3)
        except TypeError:
            # Fallback for older librosa versions
            onsets2 = librosa.onset.onset_detect(onset_envelope=onset_env_perc, sr=sr,
                                                delta=0.15, pre_max=3, post_max=3)
        onset_times2 = librosa.frames_to_time(onsets2, sr=sr)
        onset_candidates.extend(onset_times2)
        
        # Method 3: Beat tracking for rhythmic consistency
        tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
        beat_times = librosa.frames_to_time(beats, sr=sr)
        
        # Add beat subdivisions for higher difficulties
        if target_difficulty in ["HARD", "EXTREME"]:
            # Add half-beats
            half_beats = []
            for i in range(len(beat_times) - 1):
                half_beat = beat_times[i] + (beat_times[i+1] - beat_times[i]) / 2
                half_beats.append(half_beat)
            onset_candidates.extend(half_beats)
            
        if target_difficulty == "EXTREME":
            # Add quarter-beats
            quarter_beats = []
            for i in range(len(beat_times) - 1):
                quarter1 = beat_times[i] + (beat_times[i+1] - beat_times[i]) / 4
                quarter3 = beat_times[i] + 3 * (beat_times[i+1] - beat_times[i]) / 4
                quarter_beats.extend([quarter1, quarter3])
            onset_candidates.extend(quarter_beats)
        
        onset_candidates.extend(beat_times)
        
        # Remove duplicates and sort
        onset_candidates = sorted(list(set([round(t, 2) for t in onset_candidates if t >= 3.0])))
        
        logger.info(f"Found {len(onset_candidates)} onset candidates")
        
        # Select the best subset to match target count
        if len(onset_candidates) <= target_note_count:
            # Not enough candidates, use all
            selected_onsets = onset_candidates
        else:
            # Too many candidates, select best ones
            selected_onsets = select_best_onsets(onset_candidates, target_note_count, y, sr)
        
        logger.info(f"Selected {len(selected_onsets)} onsets for final beatmap")
        
        # Write to CSV
        with open(output_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["Time [s]", "Enemy Type", "Aux Color 1", "Aux Color 2", "Nº Enemies", "interval", "Aux"])
            
            for i, onset_time in enumerate(selected_onsets):
                # Vary note types for variety
                if i % 8 == 0:  # Every 8th note is special
                    enemy_type, color1, color2, aux = 2, 5, 6, 5
                elif i % 4 == 0:  # Every 4th note is accent
                    enemy_type, color1, color2, aux = 1, 2, 2, 7
                else:  # Regular notes
                    enemy_type, color1, color2, aux = 1, 1, 1, 6
                
                writer.writerow([
                    f"{onset_time:.2f}",
                    str(enemy_type),
                    str(color1),
                    str(color2),
                    "1",
                    "",
                    str(aux)
                ])
        
        # Verify final density
        final_density = len(selected_onsets) / duration
        logger.info(f"Final density: {final_density:.2f} notes/sec (target: {target_density:.2f})")
        
        return True
        
    except Exception as e:
        logger.error(f"Error in adaptive notes generation: {e}")
        return False

def select_best_onsets(candidates, target_count, y, sr):
    """
    Select the best onset candidates based on audio strength and spacing.
    """
    try:
        import librosa
        import numpy as np
        
        # Calculate onset strength for each candidate
        onset_strengths = []
        hop_length = 512
        
        for onset_time in candidates:
            frame_idx = int(onset_time * sr // hop_length)
            if frame_idx < len(y) // hop_length:
                # Get audio energy around this time
                start_sample = max(0, int(onset_time * sr) - hop_length)
                end_sample = min(len(y), int(onset_time * sr) + hop_length)
                
                if end_sample > start_sample:
                    energy = np.mean(np.abs(y[start_sample:end_sample]))
                else:
                    energy = 0
            else:
                energy = 0
            
            onset_strengths.append((onset_time, energy))
        
        # Sort by energy (strongest first)
        onset_strengths.sort(key=lambda x: x[1], reverse=True)
        
        # Select top candidates while maintaining minimum spacing
        selected = []
        min_spacing = 0.1  # Minimum 0.1 seconds between notes
        
        for onset_time, energy in onset_strengths:
            # Check if this onset is far enough from existing selections
            if not selected or min([abs(onset_time - prev) for prev in selected]) >= min_spacing:
                selected.append(onset_time)
                
                if len(selected) >= target_count:
                    break
        
        return sorted(selected)
        
    except Exception as e:
        logger.error(f"Error selecting onsets: {e}")
        # Fallback: evenly space notes
        if candidates:
            step = max(1, len(candidates) // target_count)
            return sorted(candidates[::step][:target_count])
        return []
