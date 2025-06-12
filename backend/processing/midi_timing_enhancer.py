"""
Tools for enhancing beat mapping with MIDI-like timing characteristics
"""
import random
import csv
import os
import numpy as np
import logging

logger = logging.getLogger(__name__)

def add_micro_timing(time, base_variation=0.03, swing_factor=0):
    """
    Add human-like micro timing variations to note placement
    
    Args:
        time: Original time value
        base_variation: Maximum random variation in seconds (default: 30ms)
        swing_factor: Optional swing feel (0-0.33) for triplet feel
    
    Returns:
        Modified time with natural variation
    """
    # Apply random variation (-30ms to +30ms by default)
    variation = random.uniform(-base_variation, base_variation)
    
    # Apply swing feel if requested (triplet-like timing)
    if swing_factor > 0:
        # Check if this is an offbeat eighth note
        beat_position = time % 1.0  # Get position within beat
        if 0.4 < beat_position < 0.6:  # Close to offbeat eighth
            # Move it slightly later for swing feel
            variation += swing_factor * 0.1
    
    return round(time + variation, 2)  # Round to 2 decimal places

def analyze_midi_timing(midi_csv_path):
    """
    Analyze timing patterns from a MIDI reference file to extract characteristics
    """
    try:
        times = []
        with open(midi_csv_path, 'r') as f:
            reader = csv.reader(f)
            next(reader)  # Skip header
            for row in reader:
                if len(row) >= 1:
                    times.append(float(row[0]))
        
        # Sort times and calculate intervals
        times.sort()
        intervals = np.diff(times)
        
        # Calculate statistics
        timing_data = {
            "mean_interval": np.mean(intervals),
            "min_interval": np.min(intervals),
            "median_interval": np.median(intervals),
            "std_interval": np.std(intervals),
            "timing_irregularity": np.std(intervals) / np.mean(intervals),
            "common_intervals": find_common_intervals(intervals)
        }
        
        return timing_data
    except Exception as e:
        logger.error(f"Failed to analyze MIDI timing: {e}")
        return None

def find_common_intervals(intervals, precision=0.01):
    """Find the most common interval values in a MIDI file"""
    rounded_intervals = np.round(intervals / precision) * precision
    unique, counts = np.unique(rounded_intervals, return_counts=True)
    
    # Get top 5 most common intervals
    if len(unique) > 0:
        indices = np.argsort(-counts)[:5]  # Top 5 most frequent
        return [(unique[i], counts[i]) for i in indices]
    return []

def enhance_notes_with_midi_patterns(notes_csv_path, midi_reference_path=None):
    """
    Enhance an existing notes.csv file with timing characteristics from MIDI reference
    
    If no MIDI reference is provided, default human-like timing is applied
    """
    try:
        # Read the original notes
        original_notes = []
        with open(notes_csv_path, 'r') as f:
            reader = csv.reader(f)
            header = next(reader)
            for row in reader:
                original_notes.append(row)
        
        # Analyze MIDI timing if available
        timing_data = None
        if midi_reference_path and os.path.exists(midi_reference_path):
            timing_data = analyze_midi_timing(midi_reference_path)
        
        # Default timing parameters
        base_variation = 0.03  # 30ms
        swing_factor = 0
        
        # Use MIDI timing parameters if available
        if timing_data:
            # Adjust base variation based on MIDI characteristics
            base_variation = min(timing_data["std_interval"], 0.05)  # Cap at 50ms
            
            # Check for swing feel (common in jazz, blues, funk)
            common_intervals = timing_data["common_intervals"]
            if common_intervals and len(common_intervals) >= 2:
                # If there's significant variation in the common intervals, might be swing
                if abs(common_intervals[0][0] - common_intervals[1][0]) > 0.05:
                    swing_factor = 0.2
        
        # Create enhanced notes with varied timing
        enhanced_notes = []
        previous_time = 0  # Track previous time to ensure proper spacing
        
        for row in original_notes:
            if len(row) >= 1:
                try:
                    time = float(row[0])
                    
                    # Only vary timing for notes after the initial offset
                    if time >= 3.0:
                        # Add micro-timing variation
                        new_time = add_micro_timing(time, base_variation, swing_factor)
                        
                        # Ensure minimum spacing of 50ms between notes
                        if new_time - previous_time < 0.05 and previous_time > 0:
                            new_time = previous_time + 0.05
                        
                        # Update the time in the row
                        row[0] = f"{new_time:.2f}"
                        previous_time = new_time
                    
                    enhanced_notes.append(row)
                except ValueError:
                    # Keep row unchanged if time can't be parsed
                    enhanced_notes.append(row)
            else:
                enhanced_notes.append(row)
        
        # Write enhanced notes back to file
        with open(notes_csv_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(header)
            writer.writerows(enhanced_notes)
        
        logger.info(f"Enhanced {len(enhanced_notes)} notes with MIDI-like timing")
        return True
    
    except Exception as e:
        logger.error(f"Failed to enhance notes with MIDI patterns: {e}")
        return False