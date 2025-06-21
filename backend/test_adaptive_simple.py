#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'processing'))

from adaptive_notes_simple import generate_adaptive_notes_csv

# Test the adaptive system directly
song_path = r"c:\Users\hypes\OneDrive\Desktop\Projects\BeatMapper\output\36682c86-8800-4b2a-9a16-6ce9f5284625\song.ogg"
output_path = r"c:\Users\hypes\OneDrive\Desktop\Projects\BeatMapper\output\36682c86-8800-4b2a-9a16-6ce9f5284625\notes_test.csv"

print(f"Testing adaptive notes generation...")
print(f"Song: {song_path}")
print(f"Output: {output_path}")

result = generate_adaptive_notes_csv(song_path, None, output_path, "EASY")

if result:
    print("SUCCESS: Adaptive notes generated!")
    
    # Count lines
    with open(output_path, 'r') as f:
        lines = f.readlines()
    
    # Calculate note density (exclude header)
    note_count = len(lines) - 1
    duration = 154.85  # from info.csv
    density = note_count / duration
    
    print(f"Generated {note_count} notes")
    print(f"Duration: {duration:.2f} seconds")
    print(f"Density: {density:.2f} notes/second")
    print(f"Target for EASY: <1.0 notes/second")
    
    if density < 1.0:
        print("✅ SUCCESS: Density is appropriate for EASY!")
    else:
        print("❌ FAILED: Density is too high for EASY")
        
    # Show first few lines
    print("\nFirst few lines:")
    for i, line in enumerate(lines[:6]):
        print(f"{i}: {line.strip()}")
else:
    print("FAILED: Adaptive notes generation failed")
