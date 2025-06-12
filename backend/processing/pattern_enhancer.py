"""
Tools for enhancing note patterns with greater variation and dynamics
"""
import random
import csv
import logging
import os
import numpy as np

logger = logging.getLogger(__name__)

def identify_pattern_sections(notes_csv_path, measures_per_section=8):
    """
    Identify logical sections in the song based on note patterns
    """
    try:
        # Read all notes
        times = []
        with open(notes_csv_path, 'r') as f:
            reader = csv.reader(f)
            next(reader)  # Skip header
            for row in reader:
                if len(row) >= 1:
                    times.append(float(row[0]))
        
        if not times:
            return []
        
        # Estimate tempo and beat duration
        intervals = np.diff(sorted(times))
        common_intervals = find_common_intervals(intervals)
        
        # Estimate beat duration (typically around 0.5s for 120 BPM)
        beat_duration = 0.5  # Default
        if common_intervals:
            # Common intervals might be 16th notes, 8th notes, or quarter notes
            # Try to estimate beat duration from these
            for interval, _ in common_intervals:
                if 0.4 < interval < 0.6:  # Likely quarter note
                    beat_duration = interval
                    break
                elif 0.2 < interval < 0.3:  # Likely eighth note
                    beat_duration = interval * 2
                    break
                elif 0.1 < interval < 0.15:  # Likely 16th note
                    beat_duration = interval * 4
                    break
        
        # Measure duration is typically 4 beats
        measure_duration = beat_duration * 4
        section_duration = measure_duration * measures_per_section
        
        # Divide song into sections
        min_time = min(times)
        max_time = max(times)
        
        sections = []
        current_start = min_time
        while current_start < max_time:
            section_end = current_start + section_duration
            sections.append((current_start, section_end))
            current_start = section_end
        
        return sections
    
    except Exception as e:
        logger.error(f"Failed to identify pattern sections: {e}")
        return []

def find_common_intervals(intervals, precision=0.01):
    """Find the most common interval values in note timings"""
    rounded_intervals = np.round(intervals / precision) * precision
    unique, counts = np.unique(rounded_intervals, return_counts=True)
    
    # Get top 5 most common intervals
    if len(unique) > 0:
        indices = np.argsort(-counts)[:5]  # Top 5 most frequent
        return [(unique[i], counts[i]) for i in indices]
    return []

def add_fills_and_variations(notes_csv_path):
    """
    Add drum fills and pattern variations at appropriate section transitions
    """
    try:
        # Read all notes
        all_rows = []
        with open(notes_csv_path, 'r') as f:
            reader = csv.reader(f)
            header = next(reader)
            all_rows = list(reader)
        
        if not all_rows:
            return False
        
        # Parse times
        all_notes = []
        for row in all_rows:
            if len(row) >= 7:  # Ensure row has all needed columns
                try:
                    time = float(row[0])
                    enemy_type = row[1]
                    aux_color1 = row[2]
                    aux_color2 = row[3]
                    num_enemies = row[4]
                    interval = row[5]
                    aux = row[6]
                    
                    all_notes.append({
                        "time": time,
                        "row": row,
                        "note_type": "crash" if enemy_type == "2" else "drum"
                    })
                except ValueError:
                    continue
        
        # Sort by time
        all_notes.sort(key=lambda x: x["time"])
        
        # Identify sections
        sections = identify_pattern_sections(notes_csv_path)
        
        # If no sections were found, create some based on time
        if not sections and all_notes:
            min_time = all_notes[0]["time"]
            max_time = all_notes[-1]["time"]
            section_duration = 16.0  # Default 16 seconds per section
            
            sections = []
            current_start = min_time
            while current_start < max_time:
                section_end = current_start + section_duration
                sections.append((current_start, section_end))
                current_start = section_end
        
        # Create fills at section transitions
        fill_notes = []
        for i, (section_start, section_end) in enumerate(sections):
            if i > 0:  # Skip first section start
                # Add fill before section start (in last 2 seconds of previous section)
                fill_start = max(section_start - 2.0, sections[i-1][0])
                
                # Don't add fill if there's already a crash at this position
                crash_at_section = any(n["time"] > section_start - 0.1 and n["time"] < section_start + 0.1 and n["note_type"] == "crash" for n in all_notes)
                
                if not crash_at_section:
                    fill_notes.extend(create_drum_fill(fill_start, section_start))
                    
                    # Add crash at section start if not already present
                    fill_notes.append({
                        "time": section_start,
                        "row": [f"{section_start:.2f}", "2", "5", "6", "1", "", "5"],
                        "note_type": "crash"
                    })
        
        # Merge original notes with fill notes
        all_notes.extend(fill_notes)
        all_notes.sort(key=lambda x: x["time"])
        
        # Create notes with varied density
        final_notes = vary_note_density(all_notes, sections)
        
        # Write back to CSV
        with open(notes_csv_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(header)
            for note in final_notes:
                writer.writerow(note["row"])
        
        logger.info(f"Added fills and variations to {len(final_notes)} notes")
        return True
    
    except Exception as e:
        logger.error(f"Failed to add fills and variations: {e}")
        return False

def create_drum_fill(start_time, end_time):
    """Create a drum fill in the specified time range"""
    fill_notes = []
    
    # How many notes to include in the fill
    density = random.choice([4, 6, 8, 12])
    
    # Time between notes
    interval = (end_time - start_time) / density
    
    # Create the fill notes (mostly snare with some toms)
    for i in range(density):
        note_time = start_time + i * interval
        
        # Randomize note type for variety
        if i == density - 1:
            # Last note is usually a crash/snare
            note_type = "2" if random.random() < 0.7 else "1"
            color1 = "5" if note_type == "2" else "2"
            color2 = "6" if note_type == "2" else "2"
            aux = "5" if note_type == "2" else "7"
        elif random.random() < 0.7:
            # Most notes are snares
            note_type = "1"
            color1 = "2"
            color2 = "2"
            aux = "7"
        else:
            # Some are toms
            note_type = "1"
            color1 = str(random.randint(3, 4))
            color2 = color1
            aux = "7"
        
        fill_notes.append({
            "time": note_time,
            "row": [f"{note_time:.2f}", note_type, color1, color2, "1", "", aux],
            "note_type": "crash" if note_type == "2" else "drum"
        })
    
    return fill_notes

def vary_note_density(notes, sections):
    """Vary note density throughout the song for more natural progression"""
    
    # Get notes by section
    section_notes = []
    for section_start, section_end in sections:
        section_notes.append([])
        for note in notes:
            if section_start <= note["time"] < section_end:
                section_notes[-1].append(note)
    
    # Assign a density variation to each section
    density_variations = []
    for i in range(len(sections)):
        # First section usually starts simpler
        if i == 0:
            density_variations.append(-0.2)  # Slightly reduced density
        # Build up in the middle
        elif i > len(sections) // 3 and i < len(sections) * 2 // 3:
            density_variations.append(0.2)  # Increased density
        # Random variation for other sections
        else:
            density_variations.append(random.uniform(-0.3, 0.3))
    
    # Apply density variations
    modified_notes = []
    for i, section in enumerate(section_notes):
        variation = density_variations[i]
        
        # For positive variation, add more notes
        if variation > 0:
            # Keep all original notes
            modified_notes.extend(section)
            
            # Add extra notes based on variation amount
            extra_count = int(len(section) * variation)
            for _ in range(extra_count):
                if section:  # Make sure section has notes
                    # Copy a random note but adjust timing slightly
                    original = random.choice(section)
                    time_shift = random.uniform(-0.1, 0.1)
                    new_time = original["time"] + time_shift
                    
                    # Skip if too close to existing notes
                    if any(abs(note["time"] - new_time) < 0.07 for note in modified_notes):
                        continue
                    
                    # Create new note (usually hihat)
                    new_note = {
                        "time": new_time,
                        "row": original["row"].copy(),
                        "note_type": "hihat"  # Extra notes are usually hihats
                    }
                    new_note["row"][0] = f"{new_time:.2f}"
                    new_note["row"][1] = "1"  # Enemy type
                    new_note["row"][2] = "1"  # Aux color 1
                    new_note["row"][3] = "1"  # Aux color 2
                    new_note["row"][6] = "6"  # Aux
                    
                    modified_notes.append(new_note)
                    
        # For negative variation, remove some notes
        elif variation < 0:
            # Calculate how many notes to remove
            remove_count = int(len(section) * abs(variation))
            
            # Only remove hihat notes, never crashes or important drum hits
            hihat_indices = [i for i, note in enumerate(section) 
                             if note["note_type"] != "crash" and note["row"][2] == "1" and note["row"][3] == "1"]
            
            # Randomly select indices to remove (up to remove_count)
            if hihat_indices:
                remove_indices = random.sample(hihat_indices, min(remove_count, len(hihat_indices)))
                modified_notes.extend(note for i, note in enumerate(section) if i not in remove_indices)
            else:
                # If no hihat notes, keep all notes
                modified_notes.extend(section)
        else:
            # No variation, keep all notes
            modified_notes.extend(section)
    
    # Sort by time
    modified_notes.sort(key=lambda x: x["time"])
    return modified_notes