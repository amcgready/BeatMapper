#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend', 'processing'))

from adaptive_notes_simple import generate_adaptive_notes_csv

# Update the current beatmap with proper beat-aligned notes
beatmap_id = "75b0cf7e-16eb-4626-a94e-6b6fd8372e11"
song_path = f"c:/Users/hypes/OneDrive/Desktop/Projects/BeatMapper/output/{beatmap_id}/song.ogg"
notes_path = f"c:/Users/hypes/OneDrive/Desktop/Projects/BeatMapper/output/{beatmap_id}/notes.csv"

print(f"🎵 Updating beatmap {beatmap_id} with beat-aligned EASY notes")
print(f"Song: {song_path}")
print(f"Notes: {notes_path}")

# Generate beat-aligned EASY notes
result = generate_adaptive_notes_csv(song_path, None, notes_path, "EASY")

if result:
    print("✅ SUCCESS: Updated notes.csv with beat-aligned EASY notes!")
    
    # Verify the update
    with open(notes_path, 'r') as f:
        lines = f.readlines()
    
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
    print(f"First 10 note times: {[f'{t:.2f}s' for t in note_times[:10]]}")
    
    # Check if beat-aligned (intervals should vary)
    if len(note_times) > 1:
        import numpy as np
        intervals = [note_times[i+1] - note_times[i] for i in range(len(note_times) - 1)]
        std_dev = np.std(intervals)
        
        if std_dev > 0.01:
            print(f"✅ BEAT-ALIGNED: Standard deviation = {std_dev:.3f} (intervals vary)")
        else:
            print(f"❌ STILL REGULAR: Standard deviation = {std_dev:.3f} (too uniform)")
            
        duration = 154.85
        density = len(note_times) / duration
        print(f"Note density: {density:.2f} notes/sec (target: <1.0 for EASY)")
    
else:
    print("❌ FAILED: Could not update notes.csv")
