import pandas as pd
import sys
import os

# Add the backend directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Read the notes.csv file
beatmap_id = "455ad790-691f-4843-be12-77704bd83b02"
notes_path = f"../output/{beatmap_id}/notes.csv"

try:
    df = pd.read_csv(notes_path)
    
    # Calculate note density
    times = df['Time [s]'].values
    total_notes = len(df)
    duration = times[-1] - times[0] if len(times) > 1 else 0
    notes_per_second = total_notes / duration if duration > 0 else 0
    
    print(f"=== NOTES.CSV ANALYSIS ===")
    print(f"Total notes: {total_notes}")
    print(f"Duration: {duration:.2f} seconds (from {times[0]:.2f}s to {times[-1]:.2f}s)")
    print(f"Note density: {notes_per_second:.2f} notes/second")
    
    # Check time intervals between notes
    unique_times = sorted(df['Time [s]'].unique())
    intervals = []
    for i in range(1, len(unique_times)):
        intervals.append(unique_times[i] - unique_times[i-1])
    
    if intervals:
        import numpy as np
        avg_interval = np.mean(intervals)
        min_interval = np.min(intervals)
        
        print(f"Average time between note groups: {avg_interval:.2f}s")
        print(f"Minimum time between note groups: {min_interval:.2f}s")
    
    # Count notes per timestamp
    notes_per_timestamp = df.groupby('Time [s]').size()
    avg_notes_per_timestamp = notes_per_timestamp.mean()
    max_notes_per_timestamp = notes_per_timestamp.max()
    
    print(f"Average notes per timestamp: {avg_notes_per_timestamp:.2f}")
    print(f"Maximum notes per timestamp: {max_notes_per_timestamp}")
    
    # Show first few timestamps to see pattern
    print(f"\nFirst 10 timestamps and note counts:")
    for i, (time, count) in enumerate(notes_per_timestamp.head(10).items()):
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
        
except Exception as e:
    print(f"Error analyzing notes.csv: {e}")
