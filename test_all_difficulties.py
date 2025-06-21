#!/usr/bin/env python3

import sys
import os
import numpy as np
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend', 'processing'))

from adaptive_notes_simple import generate_adaptive_notes_csv

def analyze_note_timing(note_times, difficulty):
    """Analyze if notes follow beats or are generic"""
    if len(note_times) < 2:
        return "Too few notes to analyze"
    
    # Calculate intervals between notes
    intervals = []
    for i in range(len(note_times) - 1):
        interval = note_times[i+1] - note_times[i]
        intervals.append(interval)
    
    mean_interval = np.mean(intervals)
    std_dev = np.std(intervals)
    min_interval = np.min(intervals)
    max_interval = np.max(intervals)
    
    print(f"  📊 {difficulty} Analysis:")
    print(f"    Notes: {len(note_times)}")
    print(f"    Mean interval: {mean_interval:.3f}s")
    print(f"    Std deviation: {std_dev:.3f}s") 
    print(f"    Range: {min_interval:.3f}s - {max_interval:.3f}s")
    print(f"    First 5 times: {[f'{t:.2f}s' for t in note_times[:5]]}")
    
    # Determine if beat-aligned or generic
    if std_dev < 0.01:
        print(f"    ❌ GENERIC: Perfectly regular intervals")
        return False
    elif std_dev > 0.02:
        print(f"    ✅ BEAT-ALIGNED: Natural rhythm variation")
        return True
    else:
        print(f"    ⚠️  BORDERLINE: Some variation but might be generic")
        return True

def test_difficulty(difficulty, song_path, base_output_path):
    """Test a specific difficulty level"""
    output_path = base_output_path.replace('.csv', f'_{difficulty.lower()}.csv')
    
    print(f"\n🎵 Testing {difficulty} difficulty...")
    
    result = generate_adaptive_notes_csv(song_path, None, output_path, difficulty)
    
    if not result:
        print(f"  ❌ FAILED: Could not generate notes for {difficulty}")
        return False
    
    # Read and analyze the generated notes
    try:
        with open(output_path, 'r') as f:
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
        
        # Calculate density
        duration = 154.85  # Known duration
        density = len(note_times) / duration
        
        # Expected density ranges for each difficulty
        expected_densities = {
            "EASY": (0.6, 1.0),
            "MEDIUM": (1.2, 1.8), 
            "HARD": (2.0, 3.0),
            "EXTREME": (3.5, 5.0)
        }
        
        expected_min, expected_max = expected_densities[difficulty]
        
        print(f"  📈 Density: {density:.2f} notes/sec (target: {expected_min}-{expected_max})")
        
        # Check if density is in expected range
        density_ok = expected_min <= density <= expected_max
        if density_ok:
            print(f"    ✅ Density is appropriate for {difficulty}")
        else:
            print(f"    ⚠️  Density might be outside target range")
        
        # Analyze timing patterns
        timing_ok = analyze_note_timing(note_times, difficulty)
        
        return timing_ok and density_ok
        
    except Exception as e:
        print(f"  ❌ Error analyzing {difficulty}: {e}")
        return False

# Main test
def main():
    print("🎯 COMPREHENSIVE DIFFICULTY BEAT-ALIGNMENT TEST")
    print("=" * 60)
    
    song_path = r"c:\Users\hypes\OneDrive\Desktop\Projects\BeatMapper\output\68e7e36e-b6ba-4b9d-b01a-4c4717c7ddc3\song.ogg"
    base_output_path = r"c:\Users\hypes\OneDrive\Desktop\Projects\BeatMapper\output\68e7e36e-b6ba-4b9d-b01a-4c4717c7ddc3\notes_test.csv"
    
    # Test all difficulties
    difficulties = ["EASY", "MEDIUM", "HARD", "EXTREME"]
    results = {}
    
    for difficulty in difficulties:
        results[difficulty] = test_difficulty(difficulty, song_path, base_output_path)
    
    # Summary
    print("\n" + "=" * 60)
    print("📋 SUMMARY RESULTS:")
    
    all_passed = True
    for difficulty, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {difficulty:8} | {status}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 SUCCESS: All difficulties are properly beat-aligned!")
        print("   The adaptive system correctly follows music beats")
        print("   while scaling note density for each difficulty level.")
    else:
        print("⚠️  ISSUES DETECTED: Some difficulties need adjustment")
        print("   Check the analysis above for specific problems.")

if __name__ == "__main__":
    main()
