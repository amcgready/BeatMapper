#!/usr/bin/env python3

import os
import json
import csv
from datetime import datetime

# Constants (matching backend)
DIFFICULTY_MAP = {
    "EASY": 0,
    "MEDIUM": 1, 
    "HARD": 2,
    "EXTREME": 3
}

def rebuild_beatmaps_json():
    """Rebuild beatmaps.json from existing info.csv files"""
    
    output_dir = "C:/Users/hypes/OneDrive/Desktop/Projects/BeatMapper/output"
    beatmaps_file = os.path.join(output_dir, "beatmaps.json")
    
    beatmaps = []
    
    # Scan all subdirectories for beatmaps
    for item in os.listdir(output_dir):
        item_path = os.path.join(output_dir, item)
        
        if os.path.isdir(item_path) and item != "__pycache__":
            info_csv = os.path.join(item_path, "info.csv")
            
            if os.path.exists(info_csv):
                print(f"Processing: {item}")
                
                try:
                    # Read info.csv
                    with open(info_csv, 'r') as f:
                        reader = csv.DictReader(f)
                        for row in reader:
                            # Extract data from info.csv
                            title = row.get('Song Name', 'Unknown')
                            artist = row.get('Author Name', 'Unknown')
                            difficulty_num = int(row.get('Difficulty', 0))
                            song_map = row.get('Song Map', '0')
                            
                            # Get file timestamps
                            created_time = datetime.fromtimestamp(os.path.getctime(item_path))
                            modified_time = datetime.fromtimestamp(os.path.getmtime(info_csv))
                            
                            beatmap_entry = {
                                "id": item,
                                "title": title,
                                "artist": artist,
                                "difficulty": difficulty_num,  # Store as numeric
                                "song_map": song_map,
                                "createdAt": created_time.isoformat(),
                                "updatedAt": modified_time.isoformat()
                            }
                            
                            beatmaps.append(beatmap_entry)
                            print(f"  Added: {title} by {artist} (difficulty: {difficulty_num})")
                            break
                            
                except Exception as e:
                    print(f"  Error processing {item}: {e}")
    
    # Write updated beatmaps.json
    with open(beatmaps_file, 'w') as f:
        json.dump(beatmaps, f, indent=2)
    
    print(f"\nRebuilt beatmaps.json with {len(beatmaps)} entries")
    print("Difficulty values are now numeric (0=EASY, 1=MEDIUM, 2=HARD, 3=EXTREME)")

if __name__ == "__main__":
    rebuild_beatmaps_json()
