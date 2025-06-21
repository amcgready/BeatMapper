#!/usr/bin/env python3
"""
Trigger regeneration via the backend directly
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from processing.notes_generator import generate_notes_csv

def test_regeneration():
    print("=== TESTING DIRECT REGENERATION ===")
    
    beatmap_id = '36682c86-8800-4b2a-9a16-6ce9f5284625'
    song_path = f'../output/{beatmap_id}/song.ogg'
    notes_path = f'../output/{beatmap_id}/notes_regenerated.csv'
    
    print(f"Song path: {song_path}")
    print(f"Notes path: {notes_path}")
    print(f"Song exists: {os.path.exists(song_path)}")
    
    if os.path.exists(song_path):
        print("Calling notes generator with EASY difficulty...")
        
        # Clear debug file
        try:
            with open("c:/temp/beatmapper_debug.txt", "w") as f:
                f.write("=== DIRECT REGENERATION TEST ===\n")
        except:
            pass
        
        success = generate_notes_csv(song_path, None, notes_path, "EASY")
        
        print(f"Notes generator returned: {success}")
        
        if success and os.path.exists(notes_path):
            # Analyze results
            import csv
            with open(notes_path, 'r') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            
            times = [float(row['Time [s]']) for row in rows]
            total_notes = len(rows)
            duration = max(times) - min(times) if times else 0
            density = total_notes / duration if duration > 0 else 0
            
            print(f"Results: {total_notes} notes over {duration:.1f}s = {density:.2f} notes/sec")
            
            if density < 1.0:
                print("✓ SUCCESS: Achieved EASY difficulty target!")
            elif density < 1.5:
                print("⚠ CLOSE: Near EASY target but slightly high")
            else:
                print(f"✗ FAILURE: Density too high for EASY (target: <1.0)")
        else:
            print("✗ Notes generation failed or no output file")
    else:
        print("✗ Song file not found")

if __name__ == "__main__":
    test_regeneration()
