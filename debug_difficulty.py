#!/usr/bin/env python3
"""
Debug script to test difficulty detection logic
"""
import sys
import os
import logging

# Add the backend directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from processing.info_generator import generate_info_csv, analyze_notes_difficulty

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_difficulty_detection():
    """Test the difficulty detection logic"""
    
    # Test song metadata (simulating app.py)
    song_metadata = {
        "title": "Test Song",
        "artist": "Test Artist", 
        "difficulty": "EASY",  # This should trigger auto-detection
        "song_map": "VULCAN"
    }
    
    print("=== Testing Difficulty Detection ===")
    print(f"Initial metadata: {song_metadata}")
    
    # Test the condition that should trigger auto-detection
    should_auto_detect = song_metadata.get("difficulty") in [None, "", "EASY"]
    print(f"Should auto-detect difficulty: {should_auto_detect}")
    
    # Test notes analysis (if we had a notes.csv file)
    test_notes_path = "test_notes.csv"
    
    # Create a dummy notes.csv for testing
    with open(test_notes_path, 'w') as f:
        f.write("Time [s],Enemy Type,Lane ID\n")
        # Add some sample enemies to simulate EXTREME difficulty (3+ enemies per second)
        for i in range(30):  # 30 enemies in 10 seconds = 3 enemies/sec = EXTREME
            time = i * 0.33  # Every 0.33 seconds
            f.write(f"{time:.2f},1,{(i % 4) + 1}\n")
    
    print(f"Created test notes.csv with 30 enemies over 10 seconds")
    
    # Test the notes analysis
    detected_difficulty = analyze_notes_difficulty(test_notes_path)
    print(f"Detected difficulty from notes: {detected_difficulty}")
    
    # Test full info.csv generation
    output_path = "test_info.csv"
    success = generate_info_csv(
        song_metadata=song_metadata,
        output_path=output_path,
        audio_path=None,  # No audio file for this test
        notes_csv_path=test_notes_path,
        auto_detect_difficulty=True
    )
    
    print(f"Info CSV generation success: {success}")
    
    # Read back the generated info.csv
    if os.path.exists(output_path):
        with open(output_path, 'r') as f:
            content = f.read()
        print(f"Generated info.csv content:\n{content}")
    
    # Clean up
    if os.path.exists(test_notes_path):
        os.remove(test_notes_path)
    if os.path.exists(output_path):
        os.remove(output_path)

if __name__ == "__main__":
    test_difficulty_detection()
