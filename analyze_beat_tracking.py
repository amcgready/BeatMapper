#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend', 'processing'))

# Test if the adaptive system is actually using beat tracking
song_path = r"c:\Users\hypes\OneDrive\Desktop\Projects\BeatMapper\output\68e7e36e-b6ba-4b9d-b01a-4c4717c7ddc3\song.ogg"

print("=== BEAT TRACKING ANALYSIS ===")
print(f"Analyzing: {song_path}")

try:
    import librosa
    import numpy as np
    
    # Load the audio
    print("Loading audio...")
    y, sr = librosa.load(song_path, sr=None)
    duration = len(y) / sr
    print(f"Duration: {duration:.2f} seconds")
    print(f"Sample rate: {sr} Hz")
    
    # Analyze the beat tracking
    print("\n=== BEAT TRACKING TEST ===")
    try:
        # Try the same beat tracking the adaptive system uses
        tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
        beat_times = librosa.frames_to_time(beats, sr=sr)
        
        print(f"✅ Beat tracking successful!")
        print(f"Detected tempo: {tempo:.1f} BPM")
        print(f"Total beats detected: {len(beat_times)}")
        
        # Filter beats to start after 3.0s (like the adaptive system does)
        beat_times_filtered = [t for t in beat_times if t >= 3.0]
        print(f"Beats after 3.0s: {len(beat_times_filtered)}")
        
        # Show first 10 beat times to see if they're irregular (following music) or regular (generic)
        print(f"\nFirst 10 beat times:")
        for i, beat_time in enumerate(beat_times_filtered[:10]):
            print(f"  Beat {i+1}: {beat_time:.2f}s")
            
        # Calculate intervals between beats to see if they vary (following music) or are constant (generic)
        if len(beat_times_filtered) > 1:
            intervals = []
            for i in range(len(beat_times_filtered) - 1):
                interval = beat_times_filtered[i+1] - beat_times_filtered[i]
                intervals.append(interval)
            
            print(f"\nBeat intervals (should vary if following music):")
            print(f"  Mean interval: {np.mean(intervals):.3f}s")
            print(f"  Std deviation: {np.std(intervals):.3f}s")
            print(f"  Min interval: {np.min(intervals):.3f}s") 
            print(f"  Max interval: {np.max(intervals):.3f}s")
            
            # If std deviation is very low, it might be too regular
            if np.std(intervals) < 0.05:
                print("  ⚠️  WARNING: Beat intervals are very regular - might not be following music well")
            else:
                print("  ✅ Beat intervals vary - likely following actual music beats")
                
    except Exception as e:
        print(f"❌ Beat tracking failed: {e}")
        print("This would trigger the fallback generic pattern")
    
    # Now let's compare with the actual notes.csv generated
    print(f"\n=== COMPARING WITH GENERATED NOTES ===")
    notes_path = r"c:\Users\hypes\OneDrive\Desktop\Projects\BeatMapper\output\68e7e36e-b6ba-4b9d-b01a-4c4717c7ddc3\notes.csv"
    
    try:
        with open(notes_path, 'r') as f:
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
        
        print(f"Notes in CSV: {len(note_times)}")
        print(f"First 10 note times:")
        for i, note_time in enumerate(note_times[:10]):
            print(f"  Note {i+1}: {note_time:.2f}s")
        
        # Check if note intervals are perfectly regular (generic) or vary (beat-based)
        if len(note_times) > 1:
            note_intervals = []
            for i in range(len(note_times) - 1):
                interval = note_times[i+1] - note_times[i]
                note_intervals.append(interval)
            
            print(f"\nNote intervals:")
            print(f"  Mean interval: {np.mean(note_intervals):.3f}s")
            print(f"  Std deviation: {np.std(note_intervals):.3f}s")
            print(f"  Min interval: {np.min(note_intervals):.3f}s")
            print(f"  Max interval: {np.max(note_intervals):.3f}s")
            
            # Check if it's too regular (generic fallback) 
            if np.std(note_intervals) < 0.01:  # Very low variation
                print("  ❌ RESULT: Notes are perfectly regular - likely using GENERIC FALLBACK")
                print("  The adaptive system probably failed and used evenly spaced notes")
            else:
                print("  ✅ RESULT: Notes have variation - likely FOLLOWING DETECTED BEATS")
                print("  The adaptive system successfully used beat tracking")
                
    except Exception as e:
        print(f"Error reading notes.csv: {e}")

except ImportError as e:
    print(f"Cannot run analysis: {e}")
except Exception as e:
    print(f"Error: {e}")
