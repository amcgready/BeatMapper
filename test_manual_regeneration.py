"""
Simple script to manually trigger notes.csv regeneration for Easy difficulty
"""
import os
import sys

# Add the backend directory to the path
backend_path = "C:/Users/hypes/OneDrive/Desktop/Projects/BeatMapper/backend"
sys.path.append(backend_path)

# Import the notes generator
try:
    from processing.notes_generator import generate_notes_csv
    
    # Test configuration  
    BEATMAP_ID = "9f2ebaf4-2c90-4fff-94a4-ef938743e0a6"
    BEATMAP_DIR = f"C:/Users/hypes/OneDrive/Desktop/Projects/BeatMapper/output/{BEATMAP_ID}"
    
    print("=== Manual Notes Regeneration Test ===")
    print(f"Beatmap Directory: {BEATMAP_DIR}")
    
    # Find audio and MIDI files
    audio_file = None
    midi_file = None
    
    for filename in os.listdir(BEATMAP_DIR):
        if filename.lower().endswith(('.mp3', '.wav', '.flac', '.ogg')):
            audio_file = os.path.join(BEATMAP_DIR, filename)
            print(f"Found audio file: {filename}")
        elif filename.lower().endswith(('.mid', '.midi')):
            midi_file = os.path.join(BEATMAP_DIR, filename)
            print(f"Found MIDI file: {filename}")
    
    if not audio_file:
        print("❌ No audio file found!")
        sys.exit(1)
    
    # Get current notes.csv stats
    notes_path = os.path.join(BEATMAP_DIR, 'notes.csv')
    if os.path.exists(notes_path):
        with open(notes_path, 'r') as f:
            original_lines = len(f.readlines()) - 1
        print(f"Original note count: {original_lines}")
    
    print("\nRegenerating notes.csv with EASY difficulty...")
    
    # Regenerate with EASY difficulty
    generate_notes_csv(
        song_path=audio_file,
        midi_path=midi_file if midi_file and os.path.exists(midi_file) else None,
        output_path=notes_path,
        target_difficulty="EASY"
    )
    
    # Check new stats
    if os.path.exists(notes_path):
        with open(notes_path, 'r') as f:
            new_lines = len(f.readlines()) - 1
        print(f"New note count: {new_lines}")
        
        if new_lines < original_lines:
            print("✅ Success! Note density reduced for EASY difficulty")
        else:
            print("⚠️  Note count didn't decrease as expected for EASY")
    
    print("\nDone! Check the notes.csv file to verify the changes.")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you're running this from the correct directory")
except Exception as e:
    print(f"❌ Error: {e}")
