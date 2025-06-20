#!/usr/bin/env python3
"""
Test script for the artist-title parsing function
"""

import os
import sys
sys.path.append(os.path.dirname(__file__))

# Import the function from app.py
from app import parse_artist_title_metadata

def test_parsing():
    """Test the artist-title parsing function"""
    print("Testing artist-title parsing function...")
    
    test_cases = [
        # (title, artist, expected_title, expected_artist)
        ("The Hives - Main Offender", "", "Main Offender", "The Hives"),
        ("The Hives - Main Offender", "The Hives", "The Hives - Main Offender", "The Hives"),  # Already has artist
        ("Artist: Song Title", "", "Song Title", "Artist"),
        ("Band — Track Name", "", "Track Name", "Band"),
        ("Regular Title", "Regular Artist", "Regular Title", "Regular Artist"),
        ("Title without separator", "", "Title without separator", ""),
        ("", "Artist Only", "", "Artist Only"),
        ("Multiple - Separators - In Title", "", "Separators - In Title", "Multiple"),  # Should split on first
    ]
    
    print("=" * 80)
    for i, (title, artist, expected_title, expected_artist) in enumerate(test_cases, 1):
        result_title, result_artist = parse_artist_title_metadata(title, artist)
        
        success = (result_title == expected_title and result_artist == expected_artist)
        status = "✓ PASS" if success else "✗ FAIL"
        
        print(f"Test {i}: {status}")
        print(f"  Input:    title='{title}', artist='{artist}'")
        print(f"  Expected: title='{expected_title}', artist='{expected_artist}'")
        print(f"  Got:      title='{result_title}', artist='{result_artist}'")
        print()
    
    print("=" * 80)
    print("All tests completed!")

if __name__ == "__main__":
    test_parsing()
