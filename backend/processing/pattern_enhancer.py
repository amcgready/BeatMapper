"""
Tools for enhancing note patterns with greater variation and dynamics
"""
import os
import csv
import random
import numpy as np
import logging
from collections import defaultdict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def identify_pattern_sections(notes_csv_path, measures_per_section=8):
    """
    Identify logical sections in the song based on note patterns
    
    Args:
        notes_csv_path: Path to notes CSV
        measures_per_section: How many measures to consider a section
        
    Returns:
        list: [(start_time, end_time, section_type), ...]
    """
    try:
        # Load notes
        times = []
        with open(notes_csv_path, 'r') as f:
            reader = csv.reader(f)
            next(reader)  # Skip header
            for row in reader:
                if row and len(row) > 0:
                    try:
                        times.append(float(row[0]))
                    except ValueError:
                        continue
        
        if not times:
            return []
            
        # Sort times
        times.sort()
        
        # Calculate intervals between consecutive notes
        intervals = np.diff(times)
        
        # Find common intervals
        common_intervals = find_common_intervals(intervals)
        
        # Estimate beat duration from common intervals
        if common_intervals:
            beat_duration = common_intervals[0][0]
        else:
            beat_duration = np.median(intervals)
        
        # Estimate measure duration (assuming 4/4 time)
        measure_duration = beat_duration * 4
        
        # Create sections
        sections = []
        song_duration = times[-1]
        section_duration = measure_duration * measures_per_section
        
        # Create sections with 8-measure chunks
        for i in range(0, int(song_duration / section_duration) + 1):
            start_time = i * section_duration
            end_time = (i + 1) * section_duration
            
            # Don't exceed song duration
            if start_time >= song_duration:
                break
                
            if end_time > song_duration:
                end_time = song_duration
            
            # Alternate section types for now
            section_type = "A" if i % 2 == 0 else "B"
            
            sections.append((start_time, end_time, section_type))
        
        logger.info(f"Identified {len(sections)} sections: " + 
                  f"beat={beat_duration:.2f}s, measure={measure_duration:.2f}s")
        
        return sections
        
    except Exception as e:
        logger.error(f"Error identifying pattern sections: {e}")
        return []

def find_common_intervals(intervals, precision=0.01):
    """Find the most common interval values in note timings"""
    # Round intervals to group similar values
    rounded_intervals = np.round(intervals / precision) * precision
    
    # Count occurrences
    unique, counts = np.unique(rounded_intervals, return_counts=True)
    
    # Create and sort interval-count pairs
    interval_counts = [(float(interval), int(count)) 
                      for interval, count in zip(unique, counts)]
    interval_counts.sort(key=lambda x: x[1], reverse=True)
    
    # Get top 5 most common intervals
    if len(interval_counts) > 0:
        top_intervals = interval_counts[:min(5, len(interval_counts))]
        return top_intervals
    
    return []

def add_fills_and_variations(notes_csv_path, output_path=None):
    """
    Add drum fills and pattern variations at appropriate section transitions
    
    Args:
        notes_csv_path: Path to input notes.csv
        output_path: Path for enhanced output (defaults to overwrite input)
        
    Returns:
        bool: Success or failure
    """
    try:
        if output_path is None:
            output_path = notes_csv_path
            
        # Identify sections
        sections = identify_pattern_sections(notes_csv_path)
        
        if not sections:
            logger.warning("Could not identify sections in song")
            return False
        
        # Load original notes
        all_rows = []
        with open(notes_csv_path, 'r') as f:
            reader = csv.reader(f)
            header = next(reader)
            all_rows = list(reader)
        
        # Convert to time-keyed dictionary for easier processing
        original_notes = {}
        for row in all_rows:
            if row and len(row) > 0:
                try:
                    time_val = float(row[0])
                    if time_val not in original_notes:
                        original_notes[time_val] = []
                    original_notes[time_val].append(row)
                except ValueError:
                    pass
        
        # Create a new set of notes with fills and variations
        enhanced_notes = []
        
        # Process each section
        for i, (start_time, end_time, section_type) in enumerate(sections):
            # Different pattern types for different sections
            if section_type == "A":
                # Standard pattern - keep as is
                for time in sorted(original_notes.keys()):
                    if start_time <= time < end_time - 2.0:  # Leave room for fill
                        enhanced_notes.extend(original_notes[time])
                        
            elif section_type == "B":
                # Variation pattern - we'll vary note types and densities
                for time in sorted(original_notes.keys()):
                    if start_time <= time < end_time - 2.0:
                        # Get notes at this time
                        notes_at_time = original_notes[time]
                        
                        # Randomly modify some notes
                        for note in notes_at_time:
                            # 15% chance to modify a note type
                            if random.random() < 0.15:
                                # Change note type (column 1)
                                if note[1] == "1":  # If "enemy type" is 1
                                    note[1] = "2"
                                    
                            enhanced_notes.append(note)
            
            # Add fill at end of section (if not the last section)
            if i < len(sections) - 1:
                # Create a drum fill in the last 1-2 seconds of section
                fill_start = max(3.0, end_time - 2.0)
                fill_end = end_time
                
                fill_notes = create_drum_fill(fill_start, fill_end)
                enhanced_notes.extend(fill_notes)
        
        # Sort by time
        enhanced_notes.sort(key=lambda row: float(row[0]) if row and len(row) > 0 else 0)
        
        # Make sure no notes are too close together
        filtered_notes = []
        last_time = 0
        
        for row in enhanced_notes:
            current_time = float(row[0])
            
            if current_time - last_time >= 0.05 or last_time == 0:
                filtered_notes.append(row)
                last_time = current_time
        
        # Write back
        with open(output_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(header)
            writer.writerows(filtered_notes)
        
        logger.info(f"Added fills and variations, resulting in {len(filtered_notes)} notes")
        return True
    
    except Exception as e:
        logger.error(f"Error adding fills and variations: {e}")
        return False

def create_drum_fill(start_time, end_time):
    """
    Create a drum fill between given start and end times
    
    Args:
        start_time: Fill start time in seconds
        end_time: Fill end time in seconds
        
    Returns:
        list: Rows for a drum fill
    """
    fill_notes = []
    fill_duration = end_time - start_time
    
    # Only create fill if we have enough space
    if fill_duration < 0.5:
        return fill_notes
    
    # Choose a fill type
    fill_types = ["basic", "snare_roll", "tom_fill", "complex"]
    fill_type = random.choice(fill_types)
    
    if fill_type == "basic":
        # Simple quarter-note fill
        num_notes = int(fill_duration / 0.25)
        for i in range(num_notes):
            time = start_time + i * 0.25
            
            # Alternate snare and kick
            if i % 2 == 0:
                fill_notes.append([f"{time:.2f}", "1", "2", "2", "1", "", "7"])  # Snare
            else:
                fill_notes.append([f"{time:.2f}", "1", "2", "2", "1", "", "7"])  # Kick
                
    elif fill_type == "snare_roll":
        # Snare roll with increasing density
        interval = 0.25
        time = start_time
        
        while time < end_time - 0.5:
            fill_notes.append([f"{time:.2f}", "1", "2", "2", "1", "", "7"])  # Snare
            
            # Decrease interval as we approach the end
            interval = max(0.1, interval * 0.8)
            time += interval
        
        # End with crash
        fill_notes.append([f"{end_time - 0.1:.2f}", "2", "5", "6", "1", "", "5"])  # Crash
        
    elif fill_type == "tom_fill":
        # Tom fill (different colors)
        num_notes = int(fill_duration / 0.2)
        colors = [["1", "3", "3"], ["1", "3", "4"], ["1", "4", "4"]]
        
        for i in range(num_notes):
            time = start_time + i * 0.2
            color = random.choice(colors)
            
            fill_notes.append([f"{time:.2f}", "1", color[1], color[2], "1", "", "7"])
            
        # End with crash
        fill_notes.append([f"{end_time - 0.1:.2f}", "2", "5", "6", "1", "", "5"])  # Crash
            
    elif fill_type == "complex":
        # Complex fill with varied elements
        num_notes = int(fill_duration / 0.15)
        elements = [
            ["1", "2", "2", "1", "", "7"],  # Kick
            ["1", "2", "2", "1", "", "7"],  # Snare
            ["1", "1", "1", "1", "", "6"],  # Hi-hat
            ["2", "5", "6", "1", "", "5"],  # Crash
        ]
        
        for i in range(num_notes):
            time = start_time + i * 0.15
            element = random.choice(elements)
            
            fill_notes.append([f"{time:.2f}"] + element)
    
    return fill_notes

def vary_note_density(notes_csv_path, sections, output_path=None):
    """
    Vary note density based on song sections
    
    Args:
        notes_csv_path: Path to input notes.csv
        sections: List of (start, end, type) tuples
        output_path: Path for enhanced output
        
    Returns:
        bool: Success or failure
    """
    try:
        if output_path is None:
            output_path = notes_csv_path
            
        # Load original notes
        all_rows = []
        with open(notes_csv_path, 'r') as f:
            reader = csv.reader(f)
            header = next(reader)
            all_rows = list(reader)
        
        # Group notes by time
        notes_by_time = defaultdict(list)
        for row in all_rows:
            if row and len(row) > 0:
                try:
                    time_val = float(row[0])
                    notes_by_time[time_val].append(row)
                except ValueError:
                    pass
        
        # Process each section
        varied_notes = []
        
        for i, (start_time, end_time, section_type) in enumerate(sections):
            # Determine density factor for this section
            if section_type == "A":
                density = 1.0  # Normal density
            elif section_type == "B":
                density = 1.2  # 20% more notes
            else:
                density = 0.8  # 20% fewer notes
            
            # Apply density variation
            for time, notes in notes_by_time.items():
                if start_time <= time < end_time:
                    if density < 1.0:
                        # Reduce density - randomly remove some notes
                        if random.random() > density:
                            continue
                        varied_notes.extend(notes)
                    elif density > 1.0:
                        # Increase density - add extra notes
                        varied_notes.extend(notes)
                        
                        # Add extra notes with some probability
                        if random.random() < (density - 1.0):
                            # Add an extra note 1/8 note later
                            extra_time = time + 0.125
                            for note in notes:
                                if note[1] == "1":  # If it's a normal note
                                    extra_note = note.copy()
                                    extra_note[0] = f"{extra_time:.2f}"
                                    varied_notes.append(extra_note)
                                    break
                    else:
                        # Keep normal density
                        varied_notes.extend(notes)
        
        # Sort by time
        varied_notes.sort(key=lambda row: float(row[0]) if row and len(row) > 0 else 0)
        
        # Write back
        with open(output_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(header)
            writer.writerows(varied_notes)
        
        logger.info(f"Varied note density, resulting in {len(varied_notes)} notes")
        return True
        
    except Exception as e:
        logger.error(f"Error varying note density: {e}")
        return False

def enhance_pattern(notes_csv_path, output_path=None):
    """
    Main entry point for pattern enhancement
    
    Args:
        notes_csv_path: Path to input notes.csv
        output_path: Path for enhanced output (defaults to overwrite input)
        
    Returns:
        bool: Success or failure
    """
    try:
        if output_path is None:
            output_path = notes_csv_path
        
        # Create an intermediate file for each step
        temp_dir = os.path.dirname(output_path)
        temp_file = os.path.join(temp_dir, "temp_pattern.csv")
        
        # Step 1: Identify sections
        sections = identify_pattern_sections(notes_csv_path)
        
        if not sections:
            logger.warning("Could not identify sections, using default")
            # Create default sections
            sections = [(0, 30, "A"), (30, 60, "B"), (60, 90, "A"), (90, 120, "B")]
        
        # Step 2: Add fills and variations (save to temp)
        if not add_fills_and_variations(notes_csv_path, temp_file):
            logger.warning("Failed to add fills, continuing with original")
            temp_file = notes_csv_path
            
        # Step 3: Vary note density
        if not vary_note_density(temp_file, sections, output_path):
            logger.warning("Failed to vary density")
            
            # If this fails but we have a temp file, use that
            if temp_file != notes_csv_path and os.path.exists(temp_file):
                try:
                    import shutil
                    shutil.copy(temp_file, output_path)
                except:
                    pass
        
        # Clean up temp file
        if temp_file != notes_csv_path and os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except:
                pass
        
        return True
        
    except Exception as e:
        logger.error(f"Error enhancing pattern: {e}")
        return False

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Enhance note patterns with variations")
    parser.add_argument("notes_csv", help="Path to input notes.csv file")
    parser.add_argument("--output", help="Path for output file (defaults to overwriting input)")
    
    args = parser.parse_args()
    
    success = enhance_pattern(args.notes_csv, args.output)
    
    if success:
        print(f"Successfully enhanced note pattern")
    else:
        print("Failed to enhance note pattern")