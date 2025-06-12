"""
Module to help generators match characteristics of a MIDI reference file.
"""
import csv
import numpy as np
import logging

logger = logging.getLogger(__name__)

def load_midi_reference(midi_csv_path):
    """
    Load timing patterns from a MIDI reference CSV file
    """
    try:
        patterns = {
            'timing': [],      # Time values
            'intervals': [],   # Differences between successive times
            'density': {},     # How many notes at each time point
            'elements': []     # What elements appear (enemy type, colors, etc)
        }
        
        times = []
        with open(midi_csv_path, 'r') as f:
            reader = csv.reader(f)
            next(reader)  # Skip header
            for row in reader:
                if len(row) >= 6:
                    time = float(row[0])
                    patterns['elements'].append((row[1], row[2], row[3], row[6]))
                    times.append(time)
        
        # Calculate intervals
        times = sorted(times)
        patterns['timing'] = times
        patterns['intervals'] = np.diff(times)
        
        # Calculate note density
        time_counts = {}
        for t in times:
            rounded_t = round(t, 2)
            time_counts[rounded_t] = time_counts.get(rounded_t, 0) + 1
        patterns['density'] = time_counts
        
        return patterns
    except Exception as e:
        logger.error(f"Error loading MIDI reference: {e}")
        return None

def apply_midi_reference_patterns(generated_notes, midi_patterns):
    """
    Adjust generated notes to better match MIDI reference patterns
    """
    if not midi_patterns:
        return generated_notes
    
    adjusted_notes = []
    
    # Extract timing patterns from MIDI reference
    ref_intervals = midi_patterns['intervals']
    ref_density = midi_patterns['density']
    
    # Calculate average metrics
    avg_interval = np.mean(ref_intervals)
    max_density = max(ref_density.values())
    
    # Adjust timing to better match reference
    current_time = 3.0  # Start at standard offset
    
    # Group generated notes by time point
    note_groups = {}
    for time, note_type in generated_notes:
        rounded_time = round(time, 2)
        if rounded_time not in note_groups:
            note_groups[rounded_time] = []
        note_groups[rounded_time].append(note_type)
    
    # Sort times
    sorted_times = sorted(note_groups.keys())
    
    # Redistribute notes with MIDI-like timing
    for i, time in enumerate(sorted_times):
        notes = note_groups[time]
        
        # Skip if this time already has the right density
        desired_density = min(len(notes), max_density)
        
        # Adjust timing with micro-variations
        if i < len(ref_intervals):
            # Use actual intervals from MIDI when available
            jitter = ref_intervals[i % len(ref_intervals)]
        else:
            # Otherwise use average with small random variation
            jitter = avg_interval * (0.9 + 0.2 * np.random.random())
            
        current_time = round(current_time + jitter, 2)
        
        # Add notes at this adjusted time
        for note in notes:
            adjusted_notes.append((current_time, note))
    
    return adjusted_notes