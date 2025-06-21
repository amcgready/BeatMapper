#!/usr/bin/env python3
"""
Simple script to regenerate beat-aligned notes for the problematic beatmap
by directly calling a working system
"""

import os
import sys
import shutil

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

def regenerate_with_working_system():
    """Use the working beat-aligned system to regenerate notes"""
    beatmap_id = "d22a0dae-b3f1-42ff-a86d-28e77509d85e"
    song_path = f"output/{beatmap_id}/song.ogg"
    notes_path = f"output/{beatmap_id}/notes.csv"
    
    if not os.path.exists(song_path):
        print(f"Song file not found: {song_path}")
        return
    
    # Backup original
    backup_path = f"output/{beatmap_id}/notes_backup.csv"
    if os.path.exists(notes_path):
        shutil.copy(notes_path, backup_path)
        print(f"Backed up original to: {backup_path}")
    
    # Use the working high_density_notes_generator with EASY settings
    try:
        from backend.processing.high_density_notes_generator import generate_high_density_notes_csv
        print("Using high_density_notes_generator for beat alignment...")
        
        # Call with EASY difficulty
        success = generate_high_density_notes_csv(
            song_path=song_path,
            midi_path=None,
            output_path=notes_path,
            target_difficulty="EASY"
        )
        
        if success:
            print("Successfully regenerated with beat-aligned system!")
            
            # Check the result
            if os.path.exists(notes_path):
                print("New notes.csv content (first 10 lines):")
                with open(notes_path, 'r') as f:
                    lines = f.readlines()
                    for i, line in enumerate(lines[:10]):
                        print(f"  {line.strip()}")
                
                # Check intervals
                times = []
                for line in lines[1:6]:  # Skip header
                    parts = line.strip().split(',')
                    if len(parts) > 0:
                        try:
                            times.append(float(parts[0]))
                        except:
                            pass
                
                if len(times) >= 2:
                    intervals = [times[i] - times[i-1] for i in range(1, len(times))]
                    avg_interval = sum(intervals) / len(intervals)
                    print(f"Average interval: {avg_interval:.3f}s")
                    
                    if abs(avg_interval - 1.25) < 0.1:
                        print("WARNING: Still showing 1.25s pattern")
                    else:
                        print("SUCCESS: Beat-aligned pattern detected!")
        else:
            print("Generation failed")
            
    except ImportError:
        print("high_density_notes_generator not available, trying alternative...")
        
        # Alternative: use the beat_matched_generator
        try:
            from backend.processing.beat_matched_generator import generate_beat_matched_notes_csv
            print("Using beat_matched_generator...")
            
            success = generate_beat_matched_notes_csv(
                song_path=song_path,
                midi_path=None,
                output_path=notes_path,
                target_difficulty="EASY"
            )
            
            if success:
                print("Successfully regenerated with beat-matched system!")
            else:
                print("Beat-matched generation failed")
                
        except ImportError:
            print("No alternative generators available")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    regenerate_with_working_system()
