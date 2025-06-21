#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend', 'processing'))

from adaptive_notes_simple import generate_adaptive_notes_csv

# Test the fixed adaptive system
song_path = r"c:\Users\hypes\OneDrive\Desktop\Projects\BeatMapper\output\68e7e36e-b6ba-4b9d-b01a-4c4717c7ddc3\song.ogg"
output_path = r"c:\Users\hypes\OneDrive\Desktop\Projects\BeatMapper\output\68e7e36e-b6ba-4b9d-b01a-4c4717c7ddc3\notes_beat_test.csv"

print(f"Testing FIXED adaptive notes generation...")
print(f"Song: {song_path}")
print(f"Output: {output_path}")

result = generate_adaptive_notes_csv(song_path, None, output_path, "EASY")

if result:
    print("SUCCESS: Adaptive notes generated!")
    
    # Analyze the generated notes
    with open(output_path, 'r') as f:
        lines = f.readlines()
    
    # Extract note times (skip header)
    note_times = []
    for line in lines[1:]:  # Skip header
        parts = line.strip().split(',')
        if len(parts) > 0:
            try:
                time = float(parts[0])
                note_times.append(time)
            except:
                pass
    
    print(f"Generated {len(note_times)} notes")
    
    # Show first 10 note times
    print(f"First 10 note times:")
    for i, note_time in enumerate(note_times[:10]):
        print(f"  Note {i+1}: {note_time:.2f}s")
    
    # Calculate intervals to see if they vary now
    if len(note_times) > 1:
        import numpy as np
        intervals = []
        for i in range(len(note_times) - 1):
            interval = note_times[i+1] - note_times[i]
            intervals.append(interval)
        
        print(f"\nNote intervals (should vary if following beats):")
        print(f"  Mean interval: {np.mean(intervals):.3f}s")
        print(f"  Std deviation: {np.std(intervals):.3f}s")
        print(f"  Min interval: {np.min(intervals):.3f}s")
        print(f"  Max interval: {np.max(intervals):.3f}s")
        
        if np.std(intervals) < 0.01:
            print("  ❌ Still perfectly regular - not following beats")
        else:
            print("  ✅ Intervals vary - NOW FOLLOWING DETECTED BEATS!")
            
        # Calculate density
        duration = 154.85
        density = len(note_times) / duration
        print(f"\nDensity: {density:.2f} notes/sec (target: <1.0 for EASY)")
        
else:
    print("FAILED: Adaptive notes generation failed")
