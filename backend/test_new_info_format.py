#!/usr/bin/env python3
"""
Test script for the new info.csv format
"""

import os
import sys
sys.path.append(os.path.dirname(__file__))

from processing.info_generator import generate_info_csv

def test_new_info_format():
    """Test the new info.csv format"""
    print("Testing new info.csv format...")
    
    # Test metadata
    song_metadata = {
        "title": "Test Song",
        "artist": "Test Artist",
        "difficulty": "MEDIUM",  # Should become 1
        "song_map": "DESERT",    # Should become 1
        "duration": 180.5        # Will be overridden if audio_path provided
    }
    
    # Output path
    output_path = os.path.join(os.path.dirname(__file__), "test_info.csv")
    
    # Generate info.csv
    success = generate_info_csv(song_metadata, output_path)
    
    if success:
        print(f"✓ Successfully generated info.csv at {output_path}")
        
        # Read and display the content
        try:
            with open(output_path, 'r', encoding='utf-8') as f:
                content = f.read()
                print("\nGenerated info.csv content:")
                print("=" * 50)
                print(content)
                print("=" * 50)
        except Exception as e:
            print(f"Error reading generated file: {e}")
            
        # Clean up
        try:
            os.remove(output_path)
            print("✓ Test file cleaned up")
        except Exception as e:
            print(f"Warning: Could not clean up test file: {e}")
    else:
        print("✗ Failed to generate info.csv")
        return False
    
    print("\n" + "="*60)
    print("Testing different difficulty and song map values...")
    
    # Test all combinations
    difficulties = ["EASY", "MEDIUM", "HARD", 0, 1, 2, "invalid"]
    song_maps = ["VULCAN", "DESERT", "STORM", 0, 1, 2, "invalid"]
    
    for difficulty in difficulties:
        for song_map in song_maps:
            test_metadata = {
                "title": f"Test {difficulty} {song_map}",
                "artist": "Test Artist",
                "difficulty": difficulty,
                "song_map": song_map
            }
            
            test_output = os.path.join(os.path.dirname(__file__), f"test_{difficulty}_{song_map}.csv")
            
            try:
                success = generate_info_csv(test_metadata, test_output)
                if success:
                    with open(test_output, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                        if len(lines) >= 2:
                            data_line = lines[1].strip().split(',')
                            print(f"  {difficulty:>8} + {song_map:>8} -> Difficulty: {data_line[2]}, Song Map: {data_line[4]}")
                    os.remove(test_output)
                else:
                    print(f"  {difficulty:>8} + {song_map:>8} -> FAILED")
            except Exception as e:
                print(f"  {difficulty:>8} + {song_map:>8} -> ERROR: {e}")
    
    print("\n✓ All tests completed!")
    return True

if __name__ == "__main__":
    test_new_info_format()
