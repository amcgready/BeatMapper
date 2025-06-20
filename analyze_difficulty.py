#!/usr/bin/env python3
"""
Analyze the notes.csv file to determine if the difficulty in info.csv is correctly set.
"""

import csv
import sys
import os

def analyze_notes_difficulty(notes_csv_path):
    """
    Analyze notes.csv to calculate enemies per second and determine appropriate difficulty.
    """
    print("=== Analyzing Notes.csv for Difficulty Assessment ===")
    
    # Read the notes.csv file
    enemies = []
    with open(notes_csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            time = float(row['Time [s]'])
            enemy_type = int(row['Enemy Type'])
            enemies.append({'time': time, 'type': enemy_type})
    
    print(f"Total enemies in notes.csv: {len(enemies)}")
    
    # Get time range
    if enemies:
        start_time = min(enemy['time'] for enemy in enemies)
        end_time = max(enemy['time'] for enemy in enemies)
        duration = end_time - start_time
        
        print(f"Time range: {start_time:.2f}s to {end_time:.2f}s")
        print(f"Active duration: {duration:.2f}s")
        
        # Calculate enemies per second
        enemies_per_second = len(enemies) / duration if duration > 0 else 0
        print(f"Enemies per second: {enemies_per_second:.2f}")
        
        # Determine appropriate difficulty based on thresholds
        difficulty_thresholds = {
            "EASY": 1.0,
            "MEDIUM": 1.7,
            "HARD": 2.3,
            "EXTREME": 2.9
        }
        
        print(f"\nDifficulty Thresholds:")
        for diff, threshold in difficulty_thresholds.items():
            print(f"  {diff}: {threshold} enemies/sec")
        
        # Determine appropriate difficulty
        if enemies_per_second >= 2.9:
            recommended_difficulty = "EXTREME (3)"
        elif enemies_per_second >= 2.3:
            recommended_difficulty = "HARD (2)"
        elif enemies_per_second >= 1.7:
            recommended_difficulty = "MEDIUM (1)"
        else:
            recommended_difficulty = "EASY (0)"
        
        print(f"\nRecommended difficulty: {recommended_difficulty}")
        
        # Analyze enemy types
        enemy_types = {}
        for enemy in enemies:
            enemy_type = enemy['type']
            if enemy_type not in enemy_types:
                enemy_types[enemy_type] = 0
            enemy_types[enemy_type] += 1
        
        print(f"\nEnemy type distribution:")
        for enemy_type, count in sorted(enemy_types.items()):
            percentage = (count / len(enemies)) * 100
            print(f"  Type {enemy_type}: {count} enemies ({percentage:.1f}%)")
        
        # Calculate time intervals between enemies
        enemy_times = sorted([enemy['time'] for enemy in enemies])
        intervals = []
        for i in range(1, len(enemy_times)):
            interval = enemy_times[i] - enemy_times[i-1]
            if interval > 0:  # Only count non-simultaneous enemies
                intervals.append(interval)
        
        if intervals:
            avg_interval = sum(intervals) / len(intervals)
            min_interval = min(intervals)
            max_interval = max(intervals)
            
            print(f"\nTime intervals between enemies:")
            print(f"  Average interval: {avg_interval:.3f}s")
            print(f"  Minimum interval: {min_interval:.3f}s")
            print(f"  Maximum interval: {max_interval:.3f}s")
        
        return {
            'total_enemies': len(enemies),
            'duration': duration,
            'enemies_per_second': enemies_per_second,
            'recommended_difficulty': recommended_difficulty,
            'enemy_types': enemy_types
        }
    else:
        print("No enemies found in notes.csv")
        return None

def check_info_csv_difficulty(info_csv_path):
    """
    Read the current difficulty setting from info.csv
    """
    print(f"\n=== Checking info.csv Difficulty Setting ===")
    
    try:
        with open(info_csv_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                song_name = row['Song Name']
                author_name = row['Author Name']
                difficulty = int(row['Difficulty'])
                duration = float(row['Song Duration'])
                song_map = int(row['Song Map'])
                
                difficulty_names = ["EASY", "MEDIUM", "HARD", "EXTREME"]
                difficulty_name = difficulty_names[difficulty] if difficulty < 4 else "UNKNOWN"
                
                print(f"Song: {song_name}")
                print(f"Artist: {author_name}")
                print(f"Current difficulty: {difficulty} ({difficulty_name})")
                print(f"Song duration: {duration}s")
                print(f"Song map: {song_map}")
                
                return {
                    'difficulty': difficulty,
                    'difficulty_name': difficulty_name,
                    'duration': duration
                }
    except Exception as e:
        print(f"Error reading info.csv: {e}")
        return None

def main():
    # Paths to the files
    notes_path = "output/b9ae6dd2-bfb1-455f-9e2a-df55f99c93ab/notes.csv"
    info_path = "output/b9ae6dd2-bfb1-455f-9e2a-df55f99c93ab/info.csv"
    
    # Analyze notes.csv
    notes_analysis = analyze_notes_difficulty(notes_path)
    
    # Check info.csv
    info_data = check_info_csv_difficulty(info_path)
    
    # Compare and provide recommendation
    if notes_analysis and info_data:
        print(f"\n=== DIFFICULTY ASSESSMENT RESULTS ===")
        print(f"Current setting in info.csv: {info_data['difficulty_name']} ({info_data['difficulty']})")
        print(f"Recommended based on notes.csv: {notes_analysis['recommended_difficulty']}")
        
        # Extract recommended difficulty number
        recommended_num = notes_analysis['recommended_difficulty'].split('(')[1].split(')')[0]
        current_num = str(info_data['difficulty'])
        
        if recommended_num == current_num:
            print(f"✅ CORRECT: The difficulty is properly set!")
        else:
            print(f"❌ MISMATCH: Consider changing difficulty from {info_data['difficulty_name']} to {notes_analysis['recommended_difficulty']}")
            print(f"   The song has {notes_analysis['enemies_per_second']:.2f} enemies per second")
        
        # Additional analysis
        print(f"\nAdditional Analysis:")
        print(f"- Total enemies: {notes_analysis['total_enemies']}")
        print(f"- Active gameplay duration: {notes_analysis['duration']:.2f}s")
        print(f"- Song duration from info.csv: {info_data['duration']:.2f}s")
        print(f"- Enemy density: {notes_analysis['enemies_per_second']:.2f} enemies/second")

if __name__ == "__main__":
    main()
