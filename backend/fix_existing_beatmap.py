#!/usr/bin/env python3
"""
Test script to fix the existing info.csv file
"""

import os
import sys
sys.path.append(os.path.dirname(__file__))

from processing.info_generator import generate_info_csv
from app import parse_artist_title_metadata

def fix_existing_beatmap():
    """Fix the existing beatmap with incorrect metadata"""
    
    # Path to the existing info.csv
    info_path = r"c:\Users\hypes\OneDrive\Desktop\Projects\BeatMapper\output\92d0538a-b201-4d58-83c4-217eee087c30\info.csv"
    audio_path = r"c:\Users\hypes\OneDrive\Desktop\Projects\BeatMapper\output\92d0538a-b201-4d58-83c4-217eee087c30\song.ogg"
    
    # Current incorrect metadata
    current_title = "The Hives - Main Offender"
    current_artist = "The Hives"
    
    print(f"Current title: '{current_title}'")
    print(f"Current artist: '{current_artist}'")
    
    # Parse the metadata correctly
    parsed_title, parsed_artist = parse_artist_title_metadata(current_title, "")  # Empty artist to force parsing
    
    print(f"Parsed title: '{parsed_title}'")  
    print(f"Parsed artist: '{parsed_artist}'")
    
    # Create corrected metadata
    corrected_metadata = {
        "title": parsed_title,
        "artist": parsed_artist,
        "difficulty": "EASY",  # Keep existing difficulty
        "song_map": "VULCAN"   # Keep existing song map
    }
    
    # Generate corrected info.csv
    try:
        success = generate_info_csv(corrected_metadata, info_path, audio_path)
        if success:
            print(f"\n✓ Successfully updated info.csv at {info_path}")
            
            # Read and display the corrected content
            with open(info_path, 'r', encoding='utf-8') as f:
                content = f.read()
                print("\nCorrected info.csv content:")
                print("=" * 50)
                print(content)
                print("=" * 50)
        else:
            print("✗ Failed to update info.csv")
    except Exception as e:
        print(f"Error updating info.csv: {e}")

if __name__ == "__main__":
    fix_existing_beatmap()
