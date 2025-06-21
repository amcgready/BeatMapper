#!/usr/bin/env python3

import requests
import json

def test_metadata_update():
    """Test metadata update and check response format"""
    
    BASE_URL = "http://localhost:5000"
    BEATMAP_ID = "5354800f-00b8-460e-9e69-58c8e206bd3b"  # From current beatmaps.json
    
    print("=== Testing Metadata Update ===\n")
    
    # Test updating title and difficulty
    update_data = {
        "title": "Main Offender Updated",
        "artist": "The Hives",
        "difficulty": "MEDIUM",  # Change to MEDIUM
        "song_map": "DESERT"     # Change to DESERT
    }
    
    print(f"Sending update request:")
    print(f"URL: {BASE_URL}/api/update_beatmap/{BEATMAP_ID}")
    print(f"Data: {json.dumps(update_data, indent=2)}")
    
    try:
        response = requests.put(
            f"{BASE_URL}/api/update_beatmap/{BEATMAP_ID}",
            json=update_data,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"\nResponse Status: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"Response Body: {json.dumps(result, indent=2)}")
            
            # Check if difficulty is numeric
            if 'difficulty' in result:
                difficulty_val = result['difficulty']
                print(f"\nDifficulty value: {difficulty_val} (type: {type(difficulty_val).__name__})")
                
                if isinstance(difficulty_val, int):
                    difficulty_names = ["EASY", "MEDIUM", "HARD", "EXTREME"]
                    if 0 <= difficulty_val < len(difficulty_names):
                        print(f"✅ Difficulty maps to: {difficulty_names[difficulty_val]}")
                    else:
                        print(f"❌ Difficulty value {difficulty_val} is out of range")
                else:
                    print(f"❌ Difficulty should be numeric, got {type(difficulty_val).__name__}")
            
            # Check song_map
            if 'song_map' in result:
                song_map_val = result['song_map']
                print(f"Song Map value: {song_map_val} (type: {type(song_map_val).__name__})")
        else:
            print(f"❌ Error: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to backend. Make sure the server is running on localhost:5000")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Check beatmaps.json file after update
    print(f"\n=== Checking beatmaps.json after update ===")
    try:
        with open("C:/Users/hypes/OneDrive/Desktop/Projects/BeatMapper/output/beatmaps.json", 'r') as f:
            beatmaps_data = json.load(f)
            
        for beatmap in beatmaps_data:
            if beatmap['id'] == BEATMAP_ID:
                print(f"Updated beatmap in file:")
                print(f"  Title: {beatmap['title']}")
                print(f"  Difficulty: {beatmap['difficulty']} (type: {type(beatmap['difficulty']).__name__})")
                print(f"  Song Map: {beatmap['song_map']} (type: {type(beatmap['song_map']).__name__})")
                break
        else:
            print(f"❌ Beatmap {BEATMAP_ID} not found in beatmaps.json")
            
    except Exception as e:
        print(f"❌ Error reading beatmaps.json: {e}")

if __name__ == "__main__":
    test_metadata_update()
