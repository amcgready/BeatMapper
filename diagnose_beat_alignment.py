#!/usr/bin/env python3

import sys
import os
import numpy as np
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend', 'processing'))

def analyze_current_beatmap():
    """Analyze the current beatmap and test the adaptive system"""
    
    beatmap_id = "75b0cf7e-16eb-4626-a94e-6b6fd8372e11"
    song_path = f"c:/Users/hypes/OneDrive/Desktop/Projects/BeatMapper/output/{beatmap_id}/song.ogg"
    current_notes_path = f"c:/Users/hypes/OneDrive/Desktop/Projects/BeatMapper/output/{beatmap_id}/notes.csv"
    test_notes_path = f"c:/Users/hypes/OneDrive/Desktop/Projects/BeatMapper/output/{beatmap_id}/notes_diagnostic.csv"
    
    print("🔍 DIAGNOSING BEAT ALIGNMENT ISSUE")
    print("=" * 60)
    
    # 1. Check if audio file exists
    print(f"1. Audio file check:")
    print(f"   Path: {song_path}")
    print(f"   Exists: {os.path.exists(song_path)}")
    
    if not os.path.exists(song_path):
        print("❌ Audio file missing! Cannot proceed.")
        return
    
    # 2. Analyze current notes
    print(f"\n2. Current notes analysis:")
    try:
        with open(current_notes_path, 'r') as f:
            lines = f.readlines()
        
        # Extract note times
        note_times = []
        for line in lines[1:]:  # Skip header
            parts = line.strip().split(',')
            if len(parts) > 0:
                try:
                    time = float(parts[0])
                    note_times.append(time)
                except:
                    pass
        
        print(f"   Total notes: {len(note_times)}")
        print(f"   First 5 times: {note_times[:5]}")
        
        # Check intervals
        if len(note_times) > 1:
            intervals = [note_times[i+1] - note_times[i] for i in range(len(note_times) - 1)]
            std_dev = np.std(intervals)
            
            print(f"   Mean interval: {np.mean(intervals):.3f}s")
            print(f"   Std deviation: {std_dev:.3f}s")
            
            if std_dev < 0.01:
                print("   ❌ PROBLEM: Perfectly regular intervals (generic pattern)")
            else:
                print("   ✅ Intervals vary (beat-aligned pattern)")
    
    except Exception as e:
        print(f"   ❌ Error reading current notes: {e}")
    
    # 3. Test beat detection
    print(f"\n3. Beat detection test:")
    try:
        import librosa
        
        y, sr = librosa.load(song_path, sr=None)
        duration = len(y) / sr
        print(f"   Duration: {duration:.2f}s")
        
        tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
        beat_times = librosa.frames_to_time(beats, sr=sr)
        beat_times_filtered = [t for t in beat_times if t >= 3.0]
        
        print(f"   Tempo detected: {tempo:.1f} BPM")
        print(f"   Total beats: {len(beat_times)}")
        print(f"   Beats after 3.0s: {len(beat_times_filtered)}")
        print(f"   First 5 beat times: {beat_times_filtered[:5]}")
        
    except Exception as e:
        print(f"   ❌ Beat detection failed: {e}")
        return
    
    # 4. Test adaptive system directly
    print(f"\n4. Testing adaptive system:")
    try:
        from adaptive_notes_simple import generate_adaptive_notes_csv
        
        print("   Calling adaptive system with EASY difficulty...")
        result = generate_adaptive_notes_csv(song_path, None, test_notes_path, "EASY")
        
        if result:
            print("   ✅ Adaptive system succeeded")
            
            # Analyze the generated notes
            with open(test_notes_path, 'r') as f:
                test_lines = f.readlines()
            
            test_note_times = []
            for line in test_lines[1:]:  # Skip header
                parts = line.strip().split(',')
                if len(parts) > 0:
                    try:
                        time = float(parts[0])
                        test_note_times.append(time)
                    except:
                        pass
            
            print(f"   Generated notes: {len(test_note_times)}")
            print(f"   First 5 times: {test_note_times[:5]}")
            
            if len(test_note_times) > 1:
                test_intervals = [test_note_times[i+1] - test_note_times[i] for i in range(len(test_note_times) - 1)]
                test_std_dev = np.std(test_intervals)
                
                print(f"   Mean interval: {np.mean(test_intervals):.3f}s")
                print(f"   Std deviation: {test_std_dev:.3f}s")
                
                if test_std_dev < 0.01:
                    print("   ❌ STILL GENERIC: Adaptive system is producing regular intervals")
                    print("   🔧 The issue is in the adaptive system logic")
                else:
                    print("   ✅ BEAT-ALIGNED: Adaptive system is working correctly")
                    print("   🔧 The issue is that the main system isn't calling the adaptive system")
        else:
            print("   ❌ Adaptive system failed")
            
    except Exception as e:
        print(f"   ❌ Adaptive system error: {e}")
        import traceback
        traceback.print_exc()
    
    # 5. Compare results
    print(f"\n5. Conclusion:")
    if os.path.exists(test_notes_path):
        print("   📝 Check the notes_diagnostic.csv file to see the correct beat-aligned version")
        print("   🔧 If diagnostic version is beat-aligned but current isn't,")
        print("      then the issue is in the backend integration")
    else:
        print("   ❌ Diagnostic test failed - check the adaptive system")

if __name__ == "__main__":
    analyze_current_beatmap()
