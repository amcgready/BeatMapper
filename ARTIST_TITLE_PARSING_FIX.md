# Artist-Title Parsing Fix Summary

## Issue
The info.csv was generated with incorrect metadata:
- **Song Name**: "The Hives - Main Offender" (should be "Main Offender")
- **Author Name**: "The Hives" (correct, but should be parsed from title)

## Root Cause
The MP3 metadata extraction was returning "The Hives - Main Offender" in the title field, but the system wasn't parsing the "Artist - Title" format to separate them properly.

## Solution
Added intelligent metadata parsing with the `parse_artist_title_metadata()` function that:
1. Detects common separators: ` - `, ` – `, ` — `, `: `
2. Splits on the first occurrence to handle multiple separators
3. Only splits if both artist and title parts are non-empty
4. Falls back to original values if parsing isn't possible

## Implementation
1. **Added parsing function** in app.py
2. **Integrated parsing** into upload endpoint
3. **Fixed librosa parameter** from `path=` to `filename=`
4. **Corrected existing beatmap** files

## Test Results
The parsing function correctly handles:
- ✅ "The Hives - Main Offender" → Title: "Main Offender", Artist: "The Hives"
- ✅ "Artist: Song Title" → Title: "Song Title", Artist: "Artist"  
- ✅ "Band — Track Name" → Title: "Track Name", Artist: "Band"
- ✅ Regular metadata without changes when artist is already provided
- ✅ Multiple separators (splits on first only)

## Fixed Output
**Before:**
```csv
Song Name,Author Name,Difficulty,Song Duration,Song Map
The Hives - Main Offender,The Hives,0,154.85,0
```

**After:**
```csv
Song Name,Author Name,Difficulty,Song Duration,Song Map
Main Offender,The Hives,0,154.85,0
```

## Future Uploads
All new uploads will automatically:
1. Parse "Artist - Title" formats correctly
2. Generate proper info.csv files
3. Calculate accurate song duration
4. Handle all edge cases gracefully

The fix is now in place and tested. Future uploads should generate correct metadata automatically!
