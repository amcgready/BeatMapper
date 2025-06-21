#!/usr/bin/env python3
"""
Test script to verify notes generator difficulty adjustments are working
"""

import sys
import os
sys.path.append('.')

from processing.notes_generator import generate_notes_csv

def count_notes_in_csv(csv_path):
    """Count total notes in a CSV file"""
    if not os.path.exists(csv_path):
        return 0
    
    with open(csv_path, 'r') as f:
        lines = f.readlines()
        # Skip header
        return len(lines) - 1 if len(lines) > 1 else 0

def test_difficulty_adjustment():
    """Test that difficulty adjustments actually work"""
    
    # Use an existing audio file
    beatmap_dir = r"c:\Users\hypes\OneDrive\Desktop\Projects\BeatMapper\output\6b408394-a52f-4f9c-9f83-decc32b42bcf"
    
    # Find audio file
    audio_file = None
    for filename in os.listdir(beatmap_dir):
        if filename.lower().endswith(('.mp3', '.wav', '.flac', '.ogg')):
            audio_file = os.path.join(beatmap_dir, filename)
            break
    
    if not audio_file:
        print("❌ No audio file found for testing")
        return
    
    print(f"🎵 Testing with audio file: {os.path.basename(audio_file)}")
    
    # Test different difficulties
    test_cases = [
        ("AUTO", None),
        ("EXTREME", "EXTREME"), 
        ("EASY", "EASY")
    ]
    
    results = {}
    
    for test_name, target_difficulty in test_cases:
        test_output = os.path.join(beatmap_dir, f'test_notes_{test_name.lower()}.csv')
        
        print(f"\n🧪 Testing {test_name} difficulty...")
        try:
            success = generate_notes_csv(
                song_path=audio_file,
                midi_path=None,
                output_path=test_output,
                target_difficulty=target_difficulty
            )
            
            if success and os.path.exists(test_output):
                note_count = count_notes_in_csv(test_output)
                results[test_name] = note_count
                print(f"✅ Generated {note_count} notes")
            else:
                print(f"❌ Failed to generate notes")
                results[test_name] = 0
                
        except Exception as e:
            print(f"❌ Error: {e}")
            results[test_name] = 0
    
    # Analyze results
    print(f"\n📊 Results Summary:")
    for test_name, count in results.items():
        if count > 0:
            density = count / 154.85  # Using known duration
            print(f"  {test_name}: {count} notes ({density:.2f} notes/sec)")
        else:
            print(f"  {test_name}: Failed")
    
    # Check if adjustments worked
    if results.get("EASY", 0) > 0 and results.get("EXTREME", 0) > 0:
        if results["EASY"] < results["EXTREME"]:
            print(f"\n✅ Difficulty adjustments ARE working! EASY < EXTREME")
        else:
            print(f"\n❌ Difficulty adjustments NOT working! EASY >= EXTREME")
    else:
        print(f"\n❓ Could not determine if adjustments work (missing data)")

if __name__ == "__main__":
    test_difficulty_adjustment()
