"""
Test script to verify notes.csv regeneration when difficulty is changed
"""
import requests
import json
import time
import os

# Test configuration
BEATMAP_ID = "9f2ebaf4-2c90-4fff-94a4-ef938743e0a6"
BASE_URL = "http://localhost:5000"

def test_difficulty_change():
    print("=== Testing Difficulty Change and Notes Regeneration ===\n")
    
    # Get initial notes.csv timestamp
    notes_path = f"C:/Users/hypes/OneDrive/Desktop/Projects/BeatMapper/output/{BEATMAP_ID}/notes.csv"
    
    if os.path.exists(notes_path):
        initial_time = os.path.getmtime(notes_path)
        print(f"Initial notes.csv timestamp: {time.ctime(initial_time)}")
        
        # Count initial notes
        with open(notes_path, 'r') as f:
            initial_lines = len(f.readlines()) - 1  # Subtract header
        print(f"Initial note count: {initial_lines}")
    else:
        print("ERROR: notes.csv not found!")
        return
    
    print("\n" + "="*50)
    print("Changing difficulty from EASY to HARD...")
    print("="*50)
    
    # Change difficulty to HARD
    update_data = {
        "title": "Main Offender",
        "artist": "The Hives", 
        "difficulty": "HARD",
        "song_map": "VULCAN"
    }
    
    try:
        response = requests.put(
            f"{BASE_URL}/api/update_beatmap/{BEATMAP_ID}",
            json=update_data,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"Response status: {response.status_code}")
        print(f"Response body: {response.text}")
        
        if response.status_code == 200:
            print("✅ Update request successful!")
            
            # Wait a moment for file operations
            time.sleep(2)
            
            # Check if notes.csv was modified
            if os.path.exists(notes_path):
                new_time = os.path.getmtime(notes_path)
                print(f"\nNew notes.csv timestamp: {time.ctime(new_time)}")
                
                if new_time > initial_time:
                    print("✅ notes.csv was regenerated!")
                    
                    # Count new notes
                    with open(notes_path, 'r') as f:
                        new_lines = len(f.readlines()) - 1
                    print(f"New note count: {new_lines}")
                    
                    if new_lines != initial_lines:
                        print(f"✅ Note density changed! ({initial_lines} -> {new_lines})")
                    else:
                        print("⚠️  Note count is the same - check if difficulty logic is working")
                        
                else:
                    print("❌ notes.csv was NOT regenerated!")
            else:
                print("❌ notes.csv file missing after update!")
        else:
            print(f"❌ Update failed: {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to backend. Make sure the server is running on localhost:5000")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_difficulty_change()
