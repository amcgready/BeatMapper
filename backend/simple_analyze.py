import csv
import os

# Read the notes.csv file
beatmap_id = "455ad790-691f-4843-be12-77704bd83b02"
notes_path = f"../output/{beatmap_id}/notes.csv"

try:
    with open(notes_path, 'r') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    # Calculate note density
    times = [float(row['Time [s]']) for row in rows]
    total_notes = len(rows)
    
    if total_notes > 0:
        duration = max(times) - min(times)
        notes_per_second = total_notes / duration if duration > 0 else 0
        
        print(f"=== NOTES.CSV ANALYSIS ===")
        print(f"Total notes: {total_notes}")
        print(f"Duration: {duration:.2f} seconds (from {min(times):.2f}s to {max(times):.2f}s)")
        print(f"Note density: {notes_per_second:.2f} notes/second")
        
        # Count unique timestamps
        unique_times = list(set(times))
        unique_times.sort()
        
        print(f"Unique timestamps: {len(unique_times)}")
        
        # Show first few timestamps
        print(f"\nFirst 10 timestamps:")
        for i, time in enumerate(unique_times[:10]):
            count = times.count(time)
            print(f"{time:.2f}s: {count} notes")
        
        # Difficulty assessment
        print(f"\n=== DIFFICULTY ASSESSMENT ===")
        if notes_per_second < 1.0:
            print("✓ EASY - Note density is appropriate for EASY difficulty")
        elif notes_per_second < 2.0:
            print("⚠ NORMAL - Note density suggests NORMAL difficulty")
        elif notes_per_second < 3.5:
            print("⚠ HARD - Note density suggests HARD difficulty")
        else:
            print("✗ EXTREME - Note density suggests EXTREME difficulty")
    else:
        print("No notes found in the file")
        
except Exception as e:
    print(f"Error analyzing notes.csv: {e}")
    print(f"Current directory: {os.getcwd()}")
    print(f"Looking for file: {notes_path}")
    print(f"File exists: {os.path.exists(notes_path)}")
