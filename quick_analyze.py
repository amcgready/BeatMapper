#!/usr/bin/env python3

import numpy as np

def quick_analyze_file(filepath, difficulty):
    """Quick analysis of a generated notes file"""
    try:
        with open(filepath, 'r') as f:
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
        
        if len(note_times) < 2:
            return f"{difficulty}: Too few notes"
        
        # Calculate intervals
        intervals = [note_times[i+1] - note_times[i] for i in range(len(note_times) - 1)]
        
        duration = 154.85
        density = len(note_times) / duration
        std_dev = np.std(intervals)
        
        # Check if beat-aligned (has variation) or generic (perfectly regular)
        beat_aligned = "✅ BEAT-ALIGNED" if std_dev > 0.015 else ("⚠️ BORDERLINE" if std_dev > 0.005 else "❌ GENERIC")
        
        return f"{difficulty:8} | {len(note_times):3} notes | {density:.2f} n/s | σ={std_dev:.3f} | {beat_aligned}"
        
    except Exception as e:
        return f"{difficulty}: Error - {e}"

# Analyze all generated files
base_path = r"c:\Users\hypes\OneDrive\Desktop\Projects\BeatMapper\output\68e7e36e-b6ba-4b9d-b01a-4c4717c7ddc3\notes_test"

print("🎯 QUICK ANALYSIS OF ALL DIFFICULTIES")
print("=" * 80)
print("Difficulty | Notes | Density | Variation | Beat Alignment")
print("-" * 80)

difficulties = ["easy", "medium", "hard", "extreme"]
for diff in difficulties:
    filepath = f"{base_path}_{diff}.csv"
    result = quick_analyze_file(filepath, diff.upper())
    print(result)

print("\n📝 Legend:")
print("  σ (std dev): >0.015 = good variation, 0.005-0.015 = borderline, <0.005 = too regular")
print("  Beat-aligned = notes follow musical beats vs generic spacing")
