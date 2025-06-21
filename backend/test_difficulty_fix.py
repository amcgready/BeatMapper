#!/usr/bin/env python3
"""
Simple test to verify that difficulty detection and conversion is working correctly
"""

import sys
sys.path.append('.')

from processing.info_generator import DIFFICULTY_MAP, SONG_MAP_MAP

def test_difficulty_mapping():
    """Test that difficulty mapping works for both string names and numeric strings"""
    
    print("=== Testing DIFFICULTY_MAP ===")
    
    # Test string names
    assert DIFFICULTY_MAP.get("EASY") == 0, f"Expected 0 for EASY, got {DIFFICULTY_MAP.get('EASY')}"
    assert DIFFICULTY_MAP.get("MEDIUM") == 1, f"Expected 1 for MEDIUM, got {DIFFICULTY_MAP.get('MEDIUM')}"
    assert DIFFICULTY_MAP.get("HARD") == 2, f"Expected 2 for HARD, got {DIFFICULTY_MAP.get('HARD')}"
    assert DIFFICULTY_MAP.get("EXTREME") == 3, f"Expected 3 for EXTREME, got {DIFFICULTY_MAP.get('EXTREME')}"
    
    # Test numeric strings
    assert DIFFICULTY_MAP.get("0") == 0, f"Expected 0 for '0', got {DIFFICULTY_MAP.get('0')}"
    assert DIFFICULTY_MAP.get("1") == 1, f"Expected 1 for '1', got {DIFFICULTY_MAP.get('1')}"
    assert DIFFICULTY_MAP.get("2") == 2, f"Expected 2 for '2', got {DIFFICULTY_MAP.get('2')}"
    assert DIFFICULTY_MAP.get("3") == 3, f"Expected 3 for '3', got {DIFFICULTY_MAP.get('3')}"
    
    print("✓ All difficulty mapping tests passed!")

def test_song_map_mapping():
    """Test that song map mapping works for both string names and numeric strings"""
    
    print("=== Testing SONG_MAP_MAP ===")
    
    # Test string names
    assert SONG_MAP_MAP.get("VULCAN") == 0, f"Expected 0 for VULCAN, got {SONG_MAP_MAP.get('VULCAN')}"
    assert SONG_MAP_MAP.get("DESERT") == 1, f"Expected 1 for DESERT, got {SONG_MAP_MAP.get('DESERT')}"
    assert SONG_MAP_MAP.get("STORM") == 2, f"Expected 2 for STORM, got {SONG_MAP_MAP.get('STORM')}"
    
    # Test numeric strings
    assert SONG_MAP_MAP.get("0") == 0, f"Expected 0 for '0', got {SONG_MAP_MAP.get('0')}"
    assert SONG_MAP_MAP.get("1") == 1, f"Expected 1 for '1', got {SONG_MAP_MAP.get('1')}"
    assert SONG_MAP_MAP.get("2") == 2, f"Expected 2 for '2', got {SONG_MAP_MAP.get('2')}"
    
    print("✓ All song map mapping tests passed!")

def test_conversion_logic():
    """Test the conversion logic used in the upload function"""
    
    print("=== Testing Conversion Logic ===")
    
    # Simulate different scenarios
    scenarios = [
        # (song_metadata_difficulty, expected_numeric_result)
        (0, 0),  # Already numeric
        (1, 1),  # Already numeric  
        (2, 2),  # Already numeric
        (3, 3),  # Already numeric
        ("EASY", 0),   # String name
        ("MEDIUM", 1), # String name
        ("HARD", 2),   # String name
        ("EXTREME", 3), # String name
    ]
    
    for input_val, expected in scenarios:
        # Test the conversion logic from the upload function
        if isinstance(input_val, int):
            result = input_val
        else:
            result = DIFFICULTY_MAP.get(input_val.upper(), 0)
        
        assert result == expected, f"For input {input_val}, expected {expected}, got {result}"
    
    print("✓ All conversion logic tests passed!")

if __name__ == "__main__":
    try:
        test_difficulty_mapping()
        test_song_map_mapping()
        test_conversion_logic()
        print("\n🎉 All tests passed! The difficulty detection fix should work correctly.")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
