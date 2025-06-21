#!/usr/bin/env python3
import sys
import os

# Add the current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from processing.notes_generator import generate_notes_csv

beatmap_id = '455ad790-691f-4843-be12-77704bd83b02'
beatmap_dir = f'../output/{beatmap_id}'
audio_file = os.path.join(beatmap_dir, 'song.ogg')
notes_path = os.path.join(beatmap_dir, 'notes.csv')

print(f"Looking for audio file: {audio_file}")
print(f"File exists: {os.path.exists(audio_file)}")

if os.path.exists(audio_file):
    print(f'Found audio file: {audio_file}')
    print(f'Regenerating notes with EASY difficulty...')
    
    # Clear debug file first
    try:
        with open("c:/temp/beatmapper_debug.txt", "w") as f:
            f.write("=== MANUAL NOTES REGENERATION TEST ===\n")
    except:
        pass
    
    # Test with EASY difficulty
    generate_notes_csv(
        song_path=audio_file,
        midi_path=None,
        output_path=notes_path,
        target_difficulty='EASY'
    )
    
    print('Notes.csv regenerated with EASY difficulty')
    
    # Analyze the results
    import csv
    with open(notes_path, 'r') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    times = [float(row['Time [s]']) for row in rows]
    total_notes = len(rows)
    duration = max(times) - min(times)
    notes_per_second = total_notes / duration
    
    print(f"Analysis: {total_notes} notes over {duration:.2f}s = {notes_per_second:.2f} notes/sec")
    
    if notes_per_second < 1.0:
        print("✓ SUCCESS: Note density is appropriate for EASY difficulty")
    else:
        print("✗ FAILURE: Note density is still too high for EASY difficulty")
        
else:
    print(f'Audio file not found: {audio_file}')
    print(f'Directory contents: {os.listdir(beatmap_dir) if os.path.exists(beatmap_dir) else "Directory not found"}')
