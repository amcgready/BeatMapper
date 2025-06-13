"""
Module to help generators match characteristics of a MIDI reference file.
"""
import os
import csv
import logging
import numpy as np
from pathlib import Path
from collections import defaultdict
import random

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def load_midi_reference(midi_csv_path):
    """
    Load timing patterns from a MIDI reference CSV file
    """
    try:
        if not os.path.exists(midi_csv_path):
            logger.error(f"MIDI reference file not found: {midi_csv_path}")
            return None
            
        # Load the MIDI CSV file
        notes = []
        with open(midi_csv_path, 'r') as f:
            reader = csv.reader(f)
            headers = next(reader)  # Skip header
            
            for row in reader:
                if len(row) >= 6:  # We need at least time and basic note info
                    try:
                        time = float(row[0])
                        notes.append({
                            'time': time,
                            'enemy_type': row[1] if len(row) > 1 else '',
                            'color1': row[2] if len(row) > 2 else '',
                            'color2': row[3] if len(row) > 3 else '',
                            'aux': row[5] if len(row) > 5 else ''
                        })
                    except (ValueError, IndexError) as e:
                        logger.warning(f"Error parsing MIDI note row: {e}")
        
        if not notes:
            logger.warning(f"No valid notes found in {midi_csv_path}")
            return None
            
        # Sort by time
        notes.sort(key=lambda x: x['time'])
        
        # Extract patterns
        patterns = extract_patterns(notes)
        
        # Analyze note density
        density_map = analyze_density(notes)
        
        return {
            'notes': notes,
            'patterns': patterns,
            'density_map': density_map,
            'total_notes': len(notes),
            'duration': notes[-1]['time'] - notes[0]['time'] if notes else 0
        }
        
    except Exception as e:
        logger.error(f"Failed to load MIDI reference: {e}")
        return None

def extract_patterns(notes, window_size=8):
    """
    Extract common patterns from note sequences
    """
    patterns = []
    
    if len(notes) < window_size:
        return patterns
    
    # Group notes by time (within small tolerance)
    grouped_notes = defaultdict(list)
    for note in notes:
        # Group at 10ms resolution
        time_key = round(note['time'] * 100) / 100
        grouped_notes[time_key].append(note)
    
    # Convert to list of (time, notes) sorted by time
    time_groups = [(time, group) for time, group in grouped_notes.items()]
    time_groups.sort()
    
    # Look for repeated sequences in the time groups
    for i in range(len(time_groups) - window_size):
        pattern_times = []
        pattern_notes = []
        
        # Get the first pattern_size time groups
        for j in range(window_size):
            if i + j < len(time_groups):
                time, group = time_groups[i + j]
                pattern_times.append(time)
                pattern_notes.append(group)
        
        # See if this pattern occurs again
        pattern_count = 1
        for k in range(i + 1, len(time_groups) - window_size + 1):
            matches = True
            for j in range(window_size):
                if k + j >= len(time_groups):
                    matches = False
                    break
                    
                _, group = time_groups[k + j]
                ref_group = pattern_notes[j]
                
                # Compare note types in this group
                if len(group) != len(ref_group):
                    matches = False
                    break
                    
                # Check if note types match
                group_types = sorted([n['enemy_type'] + n['color1'] + n['color2'] for n in group])
                ref_types = sorted([n['enemy_type'] + n['color1'] + n['color2'] for n in ref_group])
                if group_types != ref_types:
                    matches = False
                    break
            
            if matches:
                pattern_count += 1
        
        # If we found a repeating pattern
        if pattern_count >= 2:
            # Calculate intervals between notes in the pattern
            intervals = []
            for j in range(1, len(pattern_times)):
                intervals.append(pattern_times[j] - pattern_times[j-1])
                
            patterns.append({
                'count': pattern_count,
                'intervals': intervals,
                'notes': pattern_notes
            })
    
    # Sort patterns by frequency (most common first)
    patterns.sort(key=lambda p: p['count'], reverse=True)
    
    return patterns[:10]  # Return top 10 patterns

def analyze_density(notes, segment_size=5.0):
    """
    Analyze note density over time
    
    Returns a map of time segments to note counts
    """
    if not notes:
        return {}
        
    # Get time range
    start_time = notes[0]['time']
    end_time = notes[-1]['time']
    
    density_map = {}
    
    # Count notes in each segment
    for segment_start in np.arange(start_time, end_time, segment_size):
        segment_end = segment_start + segment_size
        segment_notes = [n for n in notes if segment_start <= n['time'] < segment_end]
        density_map[segment_start] = len(segment_notes)
    
    return density_map

def apply_midi_reference_patterns(generated_notes, midi_reference_path):
    """
    Calibrate generated notes to match MIDI reference patterns
    
    Args:
        generated_notes: List of generated notes
        midi_reference_path: Path to MIDI reference CSV
        
    Returns:
        list: Calibrated notes
    """
    # Read MIDI reference
    midi_notes = []
    with open(midi_reference_path, 'r') as f:
        reader = csv.reader(f)
        headers = next(reader)
        for row in reader:
            if len(row) >= 6:
                midi_notes.append(row)
    
    # Calculate timing and density characteristics
    midi_times = [float(n[0]) for n in midi_notes]
    midi_density = {}
    
    # Group notes into 1-second windows
    for time in range(int(midi_times[-1])):
        window_notes = [n for n in midi_notes if time <= float(n[0]) < time + 1]
        midi_density[time] = len(window_notes)
    
    # Do the same for generated notes
    gen_times = [float(n[0]) for n in generated_notes]
    gen_density = {}
    
    # Group generated notes into same windows
    for time in range(int(gen_times[-1]) if gen_times else 0):
        window_notes = [n for n in generated_notes if time <= float(n[0]) < time + 1]
        gen_density[time] = len(window_notes)
    
    # Adjust density to match MIDI
    adjusted_notes = []
    for time in sorted(midi_density.keys()):
        target_count = midi_density[time]
        current_count = gen_density.get(time, 0)
        
        # Get notes in this window
        window_notes = [n for n in generated_notes if time <= float(n[0]) < time + 1]
        
        if current_count == 0:
            # No notes in this window, generate some based on MIDI pattern
            midi_window = [n for n in midi_notes if time <= float(n[0]) < time + 1]
            for midi_note in midi_window:
                # Copy notes from MIDI but adjust to match our format
                adjusted_notes.append(midi_note)
                
        elif current_count < target_count:
            # Add some notes to match density
            adjusted_notes.extend(window_notes)
            
            # Add more notes by copying existing ones with slight time shifts
            to_add = target_count - current_count
            for _ in range(to_add):
                if window_notes:
                    template = random.choice(window_notes)
                    new_note = template.copy()
                    # Shift time slightly
                    old_time = float(template[0])
                    new_time = old_time + random.uniform(0.05, 0.15)
                    new_time = min(time + 0.99, new_time)  # Keep in window
                    new_note[0] = f"{new_time:.2f}"
                    adjusted_notes.append(new_note)
                    
        elif current_count > target_count:
            # Remove some notes to match density
            # Sort by importance (kicks and snares are more important than hi-hats)
            sorted_notes = sorted(window_notes, 
                                 key=lambda n: 0 if n[1] == "1" and n[2] == "1" else  # Kicks most important
                                              1 if n[1] == "1" and n[2] == "2" else   # Snares next
                                              2)                                       # Hi-hats last
            adjusted_notes.extend(sorted_notes[:target_count])
            
        else:
            # Already matches, keep all notes
            adjusted_notes.extend(window_notes)
    
    # Final sort by time
    adjusted_notes.sort(key=lambda x: float(x[0]))
    return adjusted_notes

def add_notes_to_match_density(notes, midi_patterns):
    """Add additional notes to match MIDI reference density"""
    try:
        result = list(notes)  # Copy the original list
        
        # Get target note count
        current_count = len(notes)
        target_count = midi_patterns['total_notes']
        notes_to_add = target_count - current_count
        
        if notes_to_add <= 0:
            return result
            
        # Use patterns from MIDI to add notes
        if 'patterns' in midi_patterns and midi_patterns['patterns']:
            # Get the most common pattern
            pattern = midi_patterns['patterns'][0]
            
            # Find spots to add this pattern
            for i in range(len(result) - 1):
                # Don't add too many notes
                if len(result) >= target_count:
                    break
                    
                # Find gaps where we could insert notes
                current_time = float(result[i][0])
                next_time = float(result[i+1][0])
                gap = next_time - current_time
                
                # If there's a significant gap
                if gap > 0.5:
                    # Add a note halfway in the gap
                    new_time = current_time + (gap / 2)
                    
                    # Use similar note type to previous note
                    new_note = result[i].copy()
                    new_note[0] = f"{new_time:.2f}"
                    
                    result.append(new_note)
        
        # Simple density fill as backup
        current_count = len(result)
        if current_count < target_count:
            # Fill using existing notes as templates
            templates = {}
            for note in notes:
                # Group by enemy type and color
                key = f"{note[1]}-{note[2]}-{note[3]}"
                if key not in templates:
                    templates[key] = note
                    
            # Find gaps where we could add notes
            for i in range(len(result) - 1):
                if len(result) >= target_count:
                    break
                    
                current_time = float(result[i][0])
                next_time = float(result[i+1][0])
                gap = next_time - current_time
                
                # If there's enough gap for another note
                if gap > 0.15:
                    # Try to add intermediate notes
                    steps = min(3, int(gap / 0.15))
                    for step in range(1, steps):
                        if len(result) >= target_count:
                            break
                            
                        # Add note at this step
                        new_time = current_time + (gap * step / steps)
                        
                        # Use a template based on position in bar
                        beat_pos = new_time % 4.0
                        if beat_pos < 0.1 or (beat_pos > 0.9 and beat_pos < 1.1):
                            # On beat - use kick or crash
                            template_key = "1-1-1"  # Kick
                        elif 0.4 < beat_pos < 0.6 or 1.4 < beat_pos < 1.6:
                            # 2 and 4 - use snare
                            template_key = "1-2-2"  # Snare
                        else:
                            # Use hi-hat
                            template_key = "1-3-3"  # Hi-hat
                            
                        # Get a template note
                        template = templates.get(template_key, result[i])
                        
                        # Create new note
                        new_note = template.copy()
                        new_note[0] = f"{new_time:.2f}"
                        
                        result.append(new_note)
        
        # Sort by time
        result.sort(key=lambda x: float(x[0]))
        
        logger.info(f"Added {len(result) - current_count} notes to match density")
        return result
        
    except Exception as e:
        logger.error(f"Error adding notes: {e}")
        return notes

def remove_notes_to_match_density(notes, midi_patterns):
    """Remove notes to match MIDI reference density"""
    try:
        # Copy the original list
        result = list(notes)
        
        # Get target note count
        current_count = len(notes)
        target_count = midi_patterns['total_notes']
        notes_to_remove = current_count - target_count
        
        if notes_to_remove <= 0:
            return result
            
        # Sort by time
        result.sort(key=lambda x: float(x[0]))
        
        # First strategy: remove redundant notes (notes too close together)
        filtered_result = []
        last_time = -1.0
        min_gap = 0.05  # 50ms minimum gap
        
        for note in result:
            time = float(note[0])
            if time - last_time >= min_gap:
                filtered_result.append(note)
                last_time = time
        
        # If we removed too many, adjust min_gap
        if len(filtered_result) < target_count:
            # Try again with smaller gap
            filtered_result = []
            last_time = -1.0
            min_gap = 0.03  # 30ms minimum gap
            
            for note in result:
                time = float(note[0])
                if time - last_time >= min_gap:
                    filtered_result.append(note)
                    last_time = time
        
        # If we still need to remove notes
        if len(filtered_result) > target_count:
            # Strategy 2: Prefer keeping notes on the beat
            weighted_notes = []
            for i, note in enumerate(filtered_result):
                time = float(note[0])
                
                # Calculate position in beat (assuming 4/4 time)
                beat_pos = time % 1.0
                
                # Assign weight based on position (on-beat notes are heavier)
                weight = 1.0
                if beat_pos < 0.05 or beat_pos > 0.95:
                    weight = 3.0  # Strong beat
                elif abs(beat_pos - 0.5) < 0.05:
                    weight = 2.0  # Backbeat
                    
                weighted_notes.append((note, weight))
            
            # Sort by weight (descending)
            weighted_notes.sort(key=lambda x: x[1], reverse=True)
            
            # Take the top target_count notes
            result = [note for note, weight in weighted_notes[:target_count]]
            
            # Resort by time
            result.sort(key=lambda x: float(x[0]))
        else:
            result = filtered_result
            
        logger.info(f"Removed {current_count - len(result)} notes to match density")
        return result
        
    except Exception as e:
        logger.error(f"Error removing notes: {e}")
        return notes

def apply_pattern_structure(notes, midi_patterns):
    """Apply MIDI pattern structure to generated notes"""
    try:
        # Check if we have pattern information
        if 'patterns' not in midi_patterns or not midi_patterns['patterns']:
            logger.warning("No patterns in MIDI reference")
            return notes
            
        # Get the most common patterns
        patterns = midi_patterns['patterns']
        
        # Group notes by time
        note_groups = defaultdict(list)
        for note in notes:
            # Group at 10ms resolution
            time_key = round(float(note[0]) * 100) / 100
            note_groups[time_key].append(note)
            
        # Convert groups to list and sort by time
        time_groups = [(time, group) for time, group in note_groups.items()]
        time_groups.sort()
        
        # Apply pattern intervals to maintain structure
        result = []
        processed = 0
        
        while processed < len(time_groups):
            # Use first pattern by default
            pattern_intervals = patterns[0]['intervals']
            
            # See if remaining group count is enough for a pattern
            if len(time_groups) - processed >= len(pattern_intervals) + 1:
                pattern_time = time_groups[processed][0]
                
                # Apply each interval to position notes
                for i, interval in enumerate(pattern_intervals):
                    if processed + i + 1 < len(time_groups):
                        current_group = time_groups[processed + i]
                        next_group = time_groups[processed + i + 1]
                        
                        # Calculate new time for next group
                        new_time = pattern_time + interval
                        
                        # Update times for this group
                        for note in next_group[1]:
                            note[0] = f"{new_time:.2f}"
                        
                        # Add to result
                        result.extend(current_group[1])
                        
                        # Update pattern time
                        pattern_time = new_time
                
                # Add the last group in the pattern
                if processed + len(pattern_intervals) < len(time_groups):
                    result.extend(time_groups[processed + len(pattern_intervals)][1])
                
                # Move to next pattern
                processed += len(pattern_intervals) + 1
            else:
                # Not enough groups left for a pattern, add remaining groups
                for i in range(processed, len(time_groups)):
                    result.extend(time_groups[i][1])
                processed = len(time_groups)
        
        # Sort result by time
        result.sort(key=lambda x: float(x[0]))
        
        return result
        
    except Exception as e:
        logger.error(f"Error applying pattern structure: {e}")
        return notes

def compare_note_density(generated_path, reference_path):
    """
    Compare note density between generated and reference files
    
    Returns:
        dict: Dictionary with comparison metrics
    """
    try:
        # Load notes from both files
        generated_notes = []
        with open(generated_path, 'r') as f:
            reader = csv.reader(f)
            header = next(reader)
            for row in reader:
                if len(row) >= 1:
                    generated_notes.append(float(row[0]))
                    
        reference_notes = []
        with open(reference_path, 'r') as f:
            reader = csv.reader(f)
            header = next(reader)
            for row in reader:
                if len(row) >= 1:
                    reference_notes.append(float(row[0]))
        
        # Calculate overall metrics
        gen_count = len(generated_notes)
        ref_count = len(reference_notes)
        count_diff = abs(gen_count - ref_count)
        count_ratio = gen_count / ref_count if ref_count > 0 else float('inf')
        
        # Calculate density by section
        section_size = 10.0  # 10-second sections
        gen_max = max(generated_notes) if generated_notes else 0
        ref_max = max(reference_notes) if reference_notes else 0
        max_time = max(gen_max, ref_max)
        
        sections = {}
        for start in np.arange(0, max_time, section_size):
            end = start + section_size
            
            # Count notes in this section
            gen_section = [t for t in generated_notes if start <= t < end]
            ref_section = [t for t in reference_notes if start <= t < end]
            
            gen_section_count = len(gen_section)
            ref_section_count = len(ref_section)
            
            sections[f"{start:.1f}-{end:.1f}"] = {
                "generated": gen_section_count,
                "reference": ref_section_count,
                "difference": gen_section_count - ref_section_count,
                "ratio": gen_section_count / ref_section_count if ref_section_count > 0 else float('inf')
            }
        
        return {
            "generated_count": gen_count,
            "reference_count": ref_count,
            "difference": gen_count - ref_count,
            "ratio": count_ratio,
            "sections": sections
        }
        
    except Exception as e:
        logger.error(f"Error comparing note density: {e}")
        return {}