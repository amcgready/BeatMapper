#!/usr/bin/env python3
"""
Debug script to test the progress bar functionality
"""

import json
import time

def debug_progress_bar():
    """Debug the progress bar functionality"""
    
    # Check the current beatmaps.json
    beatmaps_path = "output/beatmaps.json"
    
    print("=== BeatMapper Progress Bar Debug ===")
    
    try:
        with open(beatmaps_path, 'r') as f:
            beatmaps = json.load(f)
        
        print(f"Found {len(beatmaps)} beatmaps:")
        for i, beatmap in enumerate(beatmaps):
            print(f"  {i+1}. {beatmap.get('title', 'Unknown')} by {beatmap.get('artist', 'Unknown')}")
            print(f"     ID: {beatmap.get('id', 'Unknown')}")
            print(f"     Current difficulty: {beatmap.get('difficulty', 'Unknown')}")
            print()
            
    except Exception as e:
        print(f"Error reading beatmaps.json: {e}")
        return
    
    print("\n=== Progress Bar Troubleshooting ===")
    print("To see the progress bar, you need to:")
    print("1. Make sure both backend (port 5000) and frontend (port 5173) are running")
    print("2. Go to http://localhost:5173")
    print("3. Click on a beatmap from your library") 
    print("4. Click the 'Edit Metadata' button (pencil icon)")
    print("5. Click a DIFFERENT difficulty button than the current one")
    print("6. Click 'Save Changes'")
    print()
    print("If you don't see the progress bar, check:")
    print("- Browser console for JavaScript errors (F12 → Console)")
    print("- Backend console for Python errors")
    print("- Network tab to see if API calls are being made")
    print()
    print("The progress bar ONLY appears when:")
    print("- You change the difficulty to a different value")
    print("- The backend determines note regeneration is needed")
    print("- The response includes 'regenerating: true' and 'progress_task_id'")

if __name__ == "__main__":
    debug_progress_bar()
