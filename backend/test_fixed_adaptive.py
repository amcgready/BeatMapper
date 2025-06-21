#!/usr/bin/env python3
"""
Test the fixed simplified adaptive system
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_fixed_adaptive():
    print("=== TESTING FIXED ADAPTIVE SYSTEM ===")
    
    try:
        from processing.adaptive_notes_simple import generate_adaptive_notes_csv
        
        beatmap_id = '36682c86-8800-4b2a-9a16-6ce9f5284625'
        song_path = f'../output/{beatmap_id}/song.ogg'
        notes_path = f'../output/{beatmap_id}/notes_test_fixed.csv'
        
        print(f"Song path: {song_path}")
        print(f"Notes path: {notes_path}")
        print(f"Song exists: {os.path.exists(song_path)}")
        
        if os.path.exists(song_path):
            print("Calling fixed adaptive system...")
            success = generate_adaptive_notes_csv(song_path, None, notes_path, "EASY")
            
            print(f"Fixed adaptive system returned: {success}")
            
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
                    
                # Show first few notes
                print("\nFirst 10 notes:")
                for i, time in enumerate(times[:10]):
                    print(f"  {time:.2f}s")
                    
            else:
                print("✗ Fixed adaptive system failed or no output file")
        else:
            print("✗ Song file not found")
            
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_fixed_adaptive()
