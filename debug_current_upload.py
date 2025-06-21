#!/usr/bin/env python3
"""
Debug script to trace what happens during a real upload flow
"""

import os
import sys
import shutil

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from backend.processing.notes_generator import generate_notes_csv
from backend.processing.adaptive_notes_simple import generate_adaptive_notes_csv

def test_current_beatmap():
    """Test the current problematic beatmap"""
    beatmap_id = "d22a0dae-b3f1-42ff-a86d-28e77509d85e"
    beatmap_dir = f"output/{beatmap_id}"
    
    if not os.path.exists(beatmap_dir):
        print(f"Beatmap directory not found: {beatmap_dir}")
        return
        
    # Check current notes.csv
    notes_path = os.path.join(beatmap_dir, "notes.csv")
    if os.path.exists(notes_path):
        print(f"Current notes.csv content (first 10 lines):")
        with open(notes_path, 'r') as f:
            lines = f.readlines()
            for i, line in enumerate(lines[:10]):
                print(f"  {i+1}: {line.strip()}")
        
        # Check if it's generic pattern
        if len(lines) > 5:
            times = []
            for line in lines[1:6]:  # Skip header, check first 5 data lines
                parts = line.strip().split(',')
                if len(parts) >= 1:
                    try:
                        times.append(float(parts[0]))
                    except:
                        pass
            
            if len(times) >= 2:
                interval = times[1] - times[0]
                print(f"  First interval: {interval:.3f}s")
                if abs(interval - 1.25) < 0.1:
                    print("  WARNING: This looks like generic 1.25s pattern!")
                else:
                    print("  Interval looks beat-aligned")
    
    # Test regeneration with adaptive system directly
    song_path = os.path.join(beatmap_dir, "song.ogg")
    if not os.path.exists(song_path):
        print(f"Song file not found: {song_path}")
        return
        
    print(f"\nTesting direct adaptive generation...")
    test_output = "test_adaptive_output.csv"
    
    # Test EASY difficulty
    print(f"Testing EASY difficulty...")
    success = generate_adaptive_notes_csv(song_path, None, test_output, "EASY")
    print(f"Adaptive system result: {success}")
    
    if success and os.path.exists(test_output):
        print(f"Generated notes.csv content (first 5 lines):")
        with open(test_output, 'r') as f:
            lines = f.readlines()
            for i, line in enumerate(lines[:5]):
                print(f"  {i+1}: {line.strip()}")
        
        # Check timing pattern
        if len(lines) > 5:
            times = []
            for line in lines[1:6]:  # Skip header, check first 5 data lines
                parts = line.strip().split(',')
                if len(parts) >= 1:
                    try:
                        times.append(float(parts[0]))
                    except:
                        pass
            
            if len(times) >= 2:
                interval = times[1] - times[0]
                print(f"  First interval: {interval:.3f}s")
                if abs(interval - 1.25) < 0.1:
                    print("  WARNING: Still generic pattern!")
                else:
                    print("  SUCCESS: Beat-aligned pattern!")
        
        # Clean up
        os.remove(test_output)
    
    # Test what happens with standard generate_notes_csv
    print(f"\nTesting standard generate_notes_csv with EASY difficulty...")
    test_output2 = "test_standard_output.csv"
    success2 = generate_notes_csv(song_path, None, test_output2, target_difficulty="EASY")
    print(f"Standard system result: {success2}")
    
    if success2 and os.path.exists(test_output2):
        print(f"Standard generated notes.csv content (first 5 lines):")
        with open(test_output2, 'r') as f:
            lines = f.readlines()
            for i, line in enumerate(lines[:5]):
                print(f"  {i+1}: {line.strip()}")
        
        # Check timing pattern
        if len(lines) > 5:
            times = []
            for line in lines[1:6]:  # Skip header, check first 5 data lines
                parts = line.strip().split(',')
                if len(parts) >= 1:
                    try:
                        times.append(float(parts[0]))
                    except:
                        pass
            
            if len(times) >= 2:
                interval = times[1] - times[0]
                print(f"  First interval: {interval:.3f}s")
                if abs(interval - 1.25) < 0.1:
                    print("  WARNING: Still generic pattern!")
                else:
                    print("  SUCCESS: Beat-aligned pattern!")
        
        # Clean up
        os.remove(test_output2)

if __name__ == "__main__":
    test_current_beatmap()
