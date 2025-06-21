#!/usr/bin/env python3

import os
import sys

# Change to backend directory
os.chdir(r"C:\Users\hypes\OneDrive\Desktop\Projects\BeatMapper\backend")

# Add to Python path
sys.path.insert(0, ".")

try:
    from processing.notes_generator import generate_notes_csv
    
    # Configuration
    BEATMAP_ID = "9f2ebaf4-2c90-4fff-94a4-ef938743e0a6"
    BEATMAP_DIR = f"../output/{BEATMAP_ID}"
    
    print("Looking for audio file...")
    
    # Find audio file
    audio_file = None
    midi_file = None
    
    for filename in os.listdir(BEATMAP_DIR):
        filepath = os.path.join(BEATMAP_DIR, filename)
        if filename.lower().endswith(('.mp3', '.wav', '.flac', '.ogg')):
            audio_file = filepath
            print(f"Found audio: {filename}")
        elif filename.lower().endswith(('.mid', '.midi')):
            midi_file = filepath
            print(f"Found MIDI: {filename}")
    
    if not audio_file:
        print("ERROR: No audio file found!")
        sys.exit(1)
    
    # Count original notes
    notes_path = os.path.join(BEATMAP_DIR, "notes.csv")
    original_count = 0
    if os.path.exists(notes_path):
        with open(notes_path, 'r') as f:
            original_count = len(f.readlines()) - 1  # Subtract header
        print(f"Original notes: {original_count}")
    
    print("\nRegenerating with EASY difficulty...")
    
    # Regenerate notes.csv
    generate_notes_csv(
        song_path=audio_file,
        midi_path=midi_file if midi_file and os.path.exists(midi_file) else None,
        output_path=notes_path,
        target_difficulty="EASY"
    )
    
    # Count new notes
    new_count = 0
    if os.path.exists(notes_path):
        with open(notes_path, 'r') as f:
            new_count = len(f.readlines()) - 1
        print(f"New notes: {new_count}")
        
        if new_count < original_count:
            print(f"✅ SUCCESS! Reduced from {original_count} to {new_count} notes")
        else:
            print(f"⚠️ Note count didn't decrease as expected")
    
    print("Regeneration complete!")
    
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
