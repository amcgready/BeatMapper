#!/usr/bin/env python3

import requests
import json

# Test the API update to trigger regeneration
beatmap_id = "36682c86-8800-4b2a-9a16-6ce9f5284625"
url = f"http://localhost:5000/api/update_beatmap/{beatmap_id}"

# Update with EASY difficulty to trigger regeneration
data = {
    "difficulty": 0,  # EASY
    "song_map": 0
}

print(f"Making API call to: {url}")
print(f"Data: {data}")

try:
    response = requests.put(url, json=data)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
    
    if response.status_code == 200:
        print("✅ API call successful!")
    else:
        print("❌ API call failed!")
        
except Exception as e:
    print(f"❌ Error making API call: {e}")
    print("Make sure the Flask server is running on localhost:5000")
