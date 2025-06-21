#!/usr/bin/env python3
"""Analyze beatmap for difficulty and beat alignment."""

import pandas as pd
import numpy as np

def analyze_beatmap():
    # Read the beatmap files
    df = pd.read_csv('output/e42b6868-6c7c-436f-94df-8186378673fd/notes.csv')
    info_df = pd.read_csv('output/e42b6868-6c7c-436f-94df-8186378673fd/info.csv')
    
    print('=== BEATMAP ANALYSIS ===')
    print(f'Song: {info_df.iloc[0]["Song Name"]}')
    print(f'Difficulty Level: {info_df.iloc[0]["Difficulty"]} (0=EASY, 1=MEDIUM, 2=HARD, 3=EXTREME)')
    print(f'Song Duration: {info_df.iloc[0]["Song Duration"]:.2f} seconds')
    print()
    
    print('=== NOTES ANALYSIS ===')
    print(f'Total notes: {len(df)}')
    print(f'Time range: {df["Time [s]"].min():.2f} - {df["Time [s]"].max():.2f} seconds')
    print(f'Active duration: {df["Time [s]"].max() - df["Time [s]"].min():.2f} seconds')
    
    # Check beat alignment
    times = df['Time [s]'].unique()
    print(f'Unique time points: {len(times)}')
    print(f'First 10 time values: {sorted(times)[:10]}')
    
    # Check for beat alignment on half-second boundaries (common in beat games)
    beat_aligned_half = sum(1 for t in times if abs(t % 0.5) < 0.01 or abs(t % 0.5 - 0.5) < 0.01)
    print(f'Half-beat aligned (0.5s grid): {beat_aligned_half}/{len(times)} ({beat_aligned_half/len(times)*100:.1f}%)')
    
    # Check for quarter-beat alignment
    quarter_beat_aligned = sum(1 for t in times if abs(t % 0.25) < 0.01)
    print(f'Quarter-beat aligned (0.25s grid): {quarter_beat_aligned}/{len(times)} ({quarter_beat_aligned/len(times)*100:.1f}%)')
    
    # Calculate note density
    active_duration = df['Time [s]'].max() - df['Time [s]'].min()
    notes_per_second = len(df) / active_duration if active_duration > 0 else 0
    print(f'Notes per second: {notes_per_second:.2f}')
    
    # Check if appropriate for EASY difficulty
    print()
    print('=== DIFFICULTY ASSESSMENT ===')
    
    difficulty_level = info_df.iloc[0]["Difficulty"]
    if difficulty_level == 0:
        print('✓ Difficulty is set to EASY (0)')
        if notes_per_second < 1.0:
            print('✓ Note density appropriate for EASY (< 1.0 notes/second)')
        else:
            print('⚠ Note density may be too high for EASY difficulty')
    else:
        print(f'⚠ Difficulty is not EASY (current: {difficulty_level})')
    
    # Check beat alignment quality
    if quarter_beat_aligned / len(times) > 0.8:
        print('✓ Notes are well beat-aligned (>80% on quarter-beat grid)')
    elif beat_aligned_half / len(times) > 0.8:
        print('✓ Notes are reasonably beat-aligned (>80% on half-beat grid)')
    else:
        print('⚠ Notes may not be properly beat-aligned')
    
    # Sample some timing intervals to check consistency
    sorted_times = sorted(times)
    intervals = [sorted_times[i+1] - sorted_times[i] for i in range(min(20, len(sorted_times)-1))]
    print(f'Sample time intervals: {[f"{x:.2f}" for x in intervals[:10]]}')
    
    return {
        'difficulty': difficulty_level,
        'notes_per_second': notes_per_second,
        'beat_alignment_quarter': quarter_beat_aligned / len(times),
        'beat_alignment_half': beat_aligned_half / len(times),
        'total_notes': len(df)
    }

if __name__ == '__main__':
    result = analyze_beatmap()
    print(f'\n=== SUMMARY ===')
    print(f'Difficulty OK: {result["difficulty"] == 0}')
    print(f'Beat Alignment OK: {result["beat_alignment_quarter"] > 0.8 or result["beat_alignment_half"] > 0.8}')
    print(f'Note Density OK for EASY: {result["notes_per_second"] < 1.0}')
