"""
Tool to extract drum patterns from MIDI files for use in note generation
"""
import os
import csv
import logging
import argparse
from collections import defaultdict
import json

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def extract_patterns(midi_csv_path, output_path=None, min_length=2, max_length=8, min_occurrences=2):
    """
    Extract repeating patterns from a MIDI CSV file
    
    Args:
        midi_csv_path: Path to MIDI CSV file
        output_path: Path to save pattern data (optional)
        min_length: Minimum pattern length
        max_length: Maximum pattern length
        min_occurrences: Minimum number of occurrences to consider a pattern
        
    Returns:
        dict: Dictionary of extracted patterns
    """
    try:
        # Read MIDI CSV file
        notes = []
        with open(midi_csv_path, 'r') as f:
            reader = csv.reader(f)
            headers = next(reader)  # Skip header row
            
            for row in reader:
                if len(row) >= 6:
                    try:
                        time = float(row[0])
                        note_type = row[1] if len(row) > 1 else ""
                        enemy_type = row[1] if len(row) > 1 else ""
                        color1 = row[2] if len(row) > 2 else ""
                        color2 = row[3] if len(row) > 3 else ""
                        aux = row[5] if len(row) > 5 else ""
                        
                        notes.append({
                            "time": time,
                            "note_type": note_type,
                            "enemy_type": enemy_type,
                            "color1": color1,
                            "color2": color2,
                            "aux": aux,
                            "row": row  # Keep full row for reference
                        })
                    except (ValueError, IndexError):
                        continue
                        
        if not notes:
            logger.warning(f"No valid notes found in {midi_csv_path}")
            return {}
            
        logger.info(f"Loaded {len(notes)} notes from {midi_csv_path}")
        
        # Sort notes by time
        notes.sort(key=lambda n: n["time"])
        
        # Group notes into chords (notes occurring at the same time)
        chords = defaultdict(list)
        for note in notes:
            # Group within 10ms
            time_key = round(note["time"] * 100) / 100
            chords[time_key].append(note)
            
        # Convert to list of (time, notes) and sort by time
        chord_sequence = [(time, chord) for time, chord in chords.items()]
        chord_sequence.sort()
        
        logger.info(f"Grouped into {len(chord_sequence)} chords/events")
        
        # Extract timing patterns first
        timing_patterns = extract_timing_patterns(chord_sequence, min_length, max_length, min_occurrences)
        
        # Extract note content patterns (which types of notes appear together)
        content_patterns = extract_content_patterns(chord_sequence, min_length, max_length, min_occurrences)
        
        # Extract density patterns (how many notes appear over time)
        density_patterns = extract_density_patterns(notes)
        
        # Combine results
        patterns = {
            "timing_patterns": timing_patterns,
            "content_patterns": content_patterns,
            "density_patterns": density_patterns,
            "note_count": len(notes),
            "chord_count": len(chord_sequence)
        }
        
        # Save to file if requested
        if output_path:
            with open(output_path, 'w') as f:
                json.dump(patterns, f, indent=2)
            logger.info(f"Saved patterns to {output_path}")
        
        return patterns
        
    except Exception as e:
        logger.error(f"Error extracting patterns: {e}")
        return {}

def extract_timing_patterns(chord_sequence, min_length, max_length, min_occurrences):
    """
    Extract repeating timing patterns from chord sequence
    
    Args:
        chord_sequence: List of (time, chord) tuples
        min_length: Minimum pattern length
        max_length: Maximum pattern length
        min_occurrences: Minimum occurrences to consider a pattern
        
    Returns:
        list: List of timing patterns
    """
    patterns = []
    
    # Extract only the timing information
    times = [time for time, _ in chord_sequence]
    
    # Calculate intervals between consecutive events
    intervals = []
    for i in range(1, len(times)):
        interval = times[i] - times[i-1]
        intervals.append(interval)
    
    # Look for repeating interval sequences
    for length in range(min_length, min(max_length + 1, len(intervals) // 2)):
        for start in range(len(intervals) - length):
            # Extract candidate pattern
            pattern = intervals[start:start+length]
            
            # Count occurrences
            occurrences = []
            pos = 0
            while pos < len(intervals) - length:
                # Check if pattern matches at this position
                if intervals[pos:pos+length] == pattern:
                    occurrences.append(pos)
                    pos += length  # Skip to after this pattern
                else:
                    pos += 1
            
            # If pattern occurs enough times
            if len(occurrences) >= min_occurrences:
                # Convert to actual time positions
                time_positions = []
                for occ in occurrences:
                    start_time = times[occ]
                    end_time = times[occ + length]
                    time_positions.append((start_time, end_time))
                    
                # Add to patterns
                patterns.append({
                    "intervals": pattern,
                    "length": length,
                    "occurrences": len(occurrences),
                    "positions": time_positions
                })
    
    # Sort by number of occurrences
    patterns.sort(key=lambda p: p["occurrences"], reverse=True)
    
    return patterns

def extract_content_patterns(chord_sequence, min_length, max_length, min_occurrences):
    """
    Extract repeating note content patterns
    
    Args:
        chord_sequence: List of (time, chord) tuples
        min_length: Minimum pattern length
        max_length: Maximum pattern length
        min_occurrences: Minimum occurrences to consider a pattern
        
    Returns:
        list: List of content patterns
    """
    patterns = []
    
    # Convert chords to simplified representations for comparison
    simplified_sequence = []
    for time, chord in chord_sequence:
        # Create a simplified representation of the chord
        simple_chord = set()
        for note in chord:
            # Combine key properties into a single string
            key = f"{note['enemy_type']}-{note['color1']}-{note['color2']}"
            simple_chord.add(key)
            
        simplified_sequence.append((time, tuple(sorted(simple_chord))))
    
    # Look for repeating subsequences
    for length in range(min_length, min(max_length + 1, len(simplified_sequence) // 2)):
        for start in range(len(simplified_sequence) - length):
            # Extract candidate pattern
            pattern_content = [chord for _, chord in simplified_sequence[start:start+length]]
            pattern_intervals = []
            for i in range(start, start + length - 1):
                time1 = simplified_sequence[i][0]
                time2 = simplified_sequence[i+1][0]
                pattern_intervals.append(time2 - time1)
            
            # Count occurrences
            occurrences = []
            pos = 0
            while pos <= len(simplified_sequence) - length:
                # Check content match
                content_match = True
                for i in range(length):
                    if pos + i >= len(simplified_sequence):
                        content_match = False
                        break
                    if simplified_sequence[pos+i][1] != pattern_content[i]:
                        content_match = False
                        break
                
                # Check interval match if needed
                if content_match and pos < len(simplified_sequence) - length:
                    interval_match = True
                    for i in range(length - 1):
                        pos_time1 = simplified_sequence[pos+i][0]
                        pos_time2 = simplified_sequence[pos+i+1][0]
                        pos_interval = pos_time2 - pos_time1
                        # Allow some timing flexibility (within 10%)
                        if abs(pos_interval - pattern_intervals[i]) > pattern_intervals[i] * 0.1:
                            interval_match = False
                            break
                    
                    if not interval_match:
                        content_match = False
                
                # If match found
                if content_match:
                    occurrences.append(pos)
                    pos += length  # Skip to after this pattern
                else:
                    pos += 1
            
            # If pattern occurs enough times
            if len(occurrences) >= min_occurrences:
                # Convert to actual content and times
                pattern_details = []
                for i, occ in enumerate(occurrences):
                    start_time = simplified_sequence[occ][0]
                    if occ + length < len(simplified_sequence):
                        end_time = simplified_sequence[occ+length-1][0]
                    else:
                        end_time = simplified_sequence[-1][0]
                        
                    pattern_details.append({
                        "start_time": start_time,
                        "end_time": end_time,
                        "position": i
                    })
                    
                # Add to patterns
                patterns.append({
                    "content": pattern_content,
                    "intervals": pattern_intervals,
                    "length": length,
                    "occurrences": len(occurrences),
                    "details": pattern_details
                })
    
    # Sort by number of occurrences
    patterns.sort(key=lambda p: p["occurrences"], reverse=True)
    
    return patterns

def extract_density_patterns(notes, window_size=5.0):
    """
    Extract note density patterns over time
    
    Args:
        notes: List of note dictionaries
        window_size: Size of window in seconds
        
    Returns:
        dict: Dictionary of density patterns
    """
    if not notes:
        return {}
        
    # Get time range
    start_time = notes[0]["time"]
    end_time = notes[-1]["time"]
    
    # Create density map
    density_map = {}
    for window_start in range(int(start_time), int(end_time) + 1, int(window_size)):
        window_end = window_start + window_size
        
        # Count notes in this window
        window_notes = [n for n in notes if window_start <= n["time"] < window_end]
        note_count = len(window_notes)
        
        density_map[f"{window_start}-{window_end}"] = note_count
    
    # Calculate overall density statistics
    total_duration = end_time - start_time
    avg_density = len(notes) / total_duration if total_duration > 0 else 0
    
    result = {
        "window_size": window_size,
        "avg_density": avg_density,
        "total_duration": total_duration,
        "total_notes": len(notes),
        "density_map": density_map
    }
    
    # Identify high and low density sections
    densities = list(density_map.values())
    avg = sum(densities) / len(densities) if densities else 0
    std_dev = (sum((d - avg) ** 2 for d in densities) / len(densities)) ** 0.5 if densities else 0
    
    high_density = {}
    low_density = {}
    
    for window, count in density_map.items():
        if count > avg + std_dev:
            high_density[window] = count
        elif count < avg - std_dev:
            low_density[window] = count
    
    result["high_density_sections"] = high_density
    result["low_density_sections"] = low_density
    
    return result

def rebuild_patterns_as_notes(patterns, output_path):
    """
    Rebuild the most common patterns as notes in CSV format
    
    Args:
        patterns: Pattern dictionary from extract_patterns
        output_path: Where to save the CSV file
    """
    try:
        # Start with timing patterns
        timing_patterns = patterns.get("timing_patterns", [])
        content_patterns = patterns.get("content_patterns", [])
        
        if not timing_patterns or not content_patterns:
            logger.warning("No patterns to rebuild")
            return False
        
        # Use the most common timing pattern
        main_timing = timing_patterns[0]
        intervals = main_timing["intervals"]
        
        # Use the most common content pattern
        main_content = content_patterns[0]
        content = main_content["content"]
        
        # Build a pattern from scratch
        notes = []
        
        # Start at 3 seconds
        current_time = 3.0
        
        # Generate 16 measures (assuming 4 beats per measure)
        for measure in range(16):
            # Reset time if this is a new measure
            if measure > 0:
                current_time += 0.5  # Add a small gap between measures
                
            # Apply the pattern a few times per measure
            pattern_repeats = 2  # Twice per measure
            
            for repeat in range(pattern_repeats):
                # Apply each interval in the pattern
                for i, interval in enumerate(intervals):
                    # Get the note types at this position
                    note_types = content[i % len(content)]
                    
                    # Add each note type
                    for note_type in note_types:
                        # Parse note properties
                        properties = note_type.split('-')
                        enemy_type = properties[0]
                        color1 = properties[1]
                        color2 = properties[2] if len(properties) > 2 else ""
                        aux = "7"  # Default aux
                        
                        # Add note
                        notes.append([
                            f"{current_time:.2f}",
                            "1",  # Note type
                            enemy_type,
                            color1,
                            color2,
                            "1",  # Number of enemies
                            "",   # Interval
                            aux
                        ])
                    
                    # Update time for next note
                    if i < len(intervals) - 1:
                        current_time += interval
                
                # Add small gap between repeats
                current_time += 0.1
                
        # Sort notes by time
        notes.sort(key=lambda x: float(x[0]))
        
        # Write to CSV
        with open(output_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["Time [s]", "Note Type", "Enemy Type", "Aux Color 1", "Aux Color 2", "N° Enemies", "interval", "Aux"])
            writer.writerows(notes)
            
        logger.info(f"Rebuilt pattern with {len(notes)} notes at {output_path}")
        return True
        
    except Exception as e:
        logger.error(f"Error rebuilding patterns: {e}")
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract patterns from MIDI CSV files")
    parser.add_argument("input", help="Path to MIDI CSV file")
    parser.add_argument("-o", "--output", help="Path to save pattern data (JSON)")
    parser.add_argument("-c", "--csv", help="Path to save rebuilt pattern as CSV")
    parser.add_argument("-l", "--min-length", type=int, default=2, help="Minimum pattern length")
    parser.add_argument("-m", "--max-length", type=int, default=8, help="Maximum pattern length")
    parser.add_argument("-n", "--min-occurrences", type=int, default=2, help="Minimum pattern occurrences")
    
    args = parser.parse_args()
    
    patterns = extract_patterns(
        args.input, 
        args.output, 
        args.min_length, 
        args.max_length,
        args.min_occurrences
    )
    
    if args.csv:
        rebuild_patterns_as_notes(patterns, args.csv)