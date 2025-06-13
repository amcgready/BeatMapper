"""
Tools for enhancing beat mapping with MIDI-like timing characteristics
"""
import csv
import logging
import numpy as np
from pathlib import Path
from collections import defaultdict, Counter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_micro_timing(time, base_variation=0.03, swing_factor=0):
    """
    Add human-like micro-timing to a beat time
    
    Args:
        time: Base time in seconds
        base_variation: Amount of random variation (seconds)
        swing_factor: Amount of swing (0-0.5, where 0.33 is triplet swing)
        
    Returns:
        float: Adjusted time with micro-timing applied
    """
    import random
    
    # Add random variation within base_variation range
    varied_time = time + random.uniform(-base_variation, base_variation)
    
    # Apply swing if requested (affects every second 8th note)
    beat_position = (time * 2) % 2  # Position within beat (0.0-2.0)
    if 0.9 < beat_position < 1.1 and swing_factor > 0:
        # This is roughly an "and" beat (8th note after the beat)
        varied_time += swing_factor * 0.5  # Push it later by swing amount
        
    return max(0, varied_time)  # Ensure we don't go negative

def analyze_midi_timing(midi_csv_path):
    """
    Analyze timing patterns from a MIDI reference file
    
    Args:
        midi_csv_path: Path to CSV with MIDI note timings
        
    Returns:
        dict: Dictionary with timing characteristics
    """
    try:
        # Read the MIDI timing data
        note_times = []
        with open(midi_csv_path, 'r') as f:
            reader = csv.reader(f)
            headers = next(reader)  # Skip header
            
            for row in reader:
                if len(row) > 0:
                    try:
                        # First column should be time
                        time = float(row[0])
                        note_times.append(time)
                    except (ValueError, IndexError):
                        continue
        
        if not note_times:
            logger.warning(f"No valid note times found in {midi_csv_path}")
            return {}
            
        # Sort times
        note_times.sort()
        
        # Calculate intervals between notes
        intervals = []
        for i in range(1, len(note_times)):
            interval = note_times[i] - note_times[i-1]
            if 0.01 < interval < 2.0:  # Filter out very small or large intervals
                intervals.append(interval)
        
        # Find common intervals (likely representing different note values)
        common_intervals = find_common_intervals(intervals)
        
        # Calculate other statistics
        avg_notes_per_second = len(note_times) / (note_times[-1] - note_times[0])
        density_variations = {}
        
        # Look for patterns in density over time
        for i in range(0, len(note_times) - 20, 20):
            segment_start = note_times[i]
            segment_end = note_times[i + 19]
            segment_duration = segment_end - segment_start
            notes_per_sec = 20 / segment_duration
            density_variations[segment_start] = notes_per_sec
            
        return {
            "note_count": len(note_times),
            "duration": note_times[-1] - note_times[0],
            "avg_notes_per_second": avg_notes_per_second,
            "common_intervals": common_intervals,
            "density_variations": density_variations
        }
        
    except Exception as e:
        logger.error(f"Error analyzing MIDI timing: {e}")
        return {}

def find_common_intervals(intervals, precision=0.01):
    """
    Find common time intervals in a list of durations
    
    Args:
        intervals: List of time intervals
        precision: Rounding precision for binning
        
    Returns:
        list: List of (interval, frequency) tuples
    """
    # Round intervals to specified precision for binning
    rounded = [round(i / precision) * precision for i in intervals]
    
    # Count occurrences
    counter = Counter(rounded)
    
    # Get most common intervals
    common = counter.most_common(5)  # Get top 5 intervals
    
    return common

def enhance_notes_with_midi_timing(notes_csv_path, output_path=None, midi_reference_path=None):
    """
    Enhance a notes.csv file with MIDI-like timing characteristics
    
    Args:
        notes_csv_path: Path to input notes.csv
        output_path: Path to save enhanced notes (defaults to override input)
        midi_reference_path: Optional path to MIDI reference file
        
    Returns:
        bool: True if successful
    """
    if not output_path:
        output_path = notes_csv_path
        
    try:
        # Load patterns from MIDI reference if provided
        midi_patterns = None
        if midi_reference_path and Path(midi_reference_path).exists():
            midi_patterns = analyze_midi_timing(midi_reference_path)
            logger.info(f"Loaded timing patterns from {midi_reference_path}")
        
        # Read existing notes
        notes = []
        with open(notes_csv_path, 'r') as f:
            reader = csv.reader(f)
            headers = next(reader)
            
            for row in reader:
                if len(row) >= 6:  # Ensure valid row
                    notes.append(row)
                    
        if not notes:
            logger.warning(f"No valid notes found in {notes_csv_path}")
            return False
            
        # Sort by time
        notes.sort(key=lambda x: float(x[0]))
            
        # Apply enhanced timing
        enhanced_notes = []
        
        # If we have MIDI reference patterns, use those
        if midi_patterns and "common_intervals" in midi_patterns and midi_patterns["common_intervals"]:
            logger.info("Using MIDI reference timing patterns")
            common_intervals = midi_patterns["common_intervals"]
            
            # Extract the interval values (not the counts)
            intervals = [interval for interval, _ in common_intervals]
            
            # Group notes into logical patterns
            groups = defaultdict(list)
            for note in notes:
                time = float(note[0])
                # Group by rounding to nearest 0.25
                group_key = round(time * 4) / 4
                groups[group_key].append(note)
            
            # Apply MIDI-like timing to each group
            for group_time, group_notes in groups.items():
                if len(group_notes) == 1:
                    # Single notes just get micro-timing
                    note = group_notes[0]
                    new_time = add_micro_timing(float(note[0]), 0.02)
                    note[0] = f"{new_time:.2f}"
                    enhanced_notes.append(note)
                else:
                    # Multiple notes in a group might be a pattern
                    # Use MIDI-like intervals within the group
                    group_notes.sort(key=lambda x: float(x[0]))
                    
                    # Apply first note with micro-timing
                    base_time = float(group_notes[0][0])
                    new_base = add_micro_timing(base_time, 0.02)
                    
                    # Adjust all notes in group
                    for i, note in enumerate(group_notes):
                        if i == 0:
                            note[0] = f"{new_base:.2f}"
                        else:
                            # Apply a MIDI-like interval
                            interval = intervals[i % len(intervals)]
                            note[0] = f"{new_base + (interval * i):.2f}"
                        enhanced_notes.append(note)
        else:
            # No reference - add basic humanization
            logger.info("Using basic humanization")
            for note in notes:
                time = float(note[0])
                new_time = add_micro_timing(time)
                note[0] = f"{new_time:.2f}"
                enhanced_notes.append(note)
        
        # Sort the enhanced notes by time
        enhanced_notes.sort(key=lambda x: float(x[0]))
        
        # Ensure no duplicate timestamps
        last_time = -1.0
        for note in enhanced_notes:
            time = float(note[0])
            if abs(time - last_time) < 0.01:  # Notes too close together
                note[0] = f"{time + 0.01:.2f}"  # Add 10ms
            last_time = float(note[0])
        
        # Write enhanced notes back to file
        with open(output_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(headers)  # Write header
            writer.writerows(enhanced_notes)
            
        logger.info(f"Enhanced {len(enhanced_notes)} notes with MIDI-like timing at {output_path}")
        return True
        
    except Exception as e:
        logger.error(f"Error enhancing notes with MIDI timing: {e}")
        return False

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Enhance beat mapping with MIDI-like timing")
    parser.add_argument("input", help="Path to input notes.csv file")
    parser.add_argument("-o", "--output", help="Path to output (defaults to override input)")
    parser.add_argument("-m", "--midi", help="Path to MIDI reference file")
    
    args = parser.parse_args()
    
    if enhance_notes_with_midi_timing(args.input, args.output, args.midi):
        print("Successfully enhanced notes with MIDI-like timing")
    else:
        print("Failed to enhance notes")