# Info.csv Format Update Summary

## Overview
The info.csv format has been successfully updated to match your requirements. Here's what changed:

## Old Format
```
Title,Artist,Album,Year,Genre
```

## New Format
```
Song Name,Author Name,Difficulty,Song Duration,Song Map
```

## Field Mappings

### Difficulty Values
- **EASY** = 0
- **MEDIUM** = 1  
- **HARD** = 2

### Song Map Values
- **VULCAN** = 0
- **DESERT** = 1
- **STORM** = 2

## Implementation Details

### Backend Changes
1. **info_generator.py** - Completely rewritten to handle new format:
   - Added difficulty and song map validation
   - Added audio duration calculation using librosa
   - Added mapping constants for difficulty and song map
   - Improved error handling and logging

2. **app.py** - Updated to use new metadata structure:
   - Modified upload endpoint to create default difficulty (EASY) and song map (VULCAN)
   - Updated update_beatmap endpoint to handle new fields
   - Modified download endpoint to generate proper placeholder info.csv files
   - Added audio duration calculation during info.csv generation

### Frontend Changes
1. **App.jsx** - Updated UI components:
   - Replaced album/year fields with difficulty/song map dropdowns
   - Added proper validation and default values
   - Updated form handling for new metadata structure
   - Modified beatmap display to show difficulty and song map values

## Features
- **Smart Defaults**: New uploads default to EASY difficulty and VULCAN song map
- **Validation**: Invalid difficulty/song map values are automatically corrected with warnings
- **Duration Calculation**: Song duration is automatically calculated from audio files
- **Backward Compatibility**: Existing uploads are handled gracefully
- **UI Integration**: Dropdown menus for easy difficulty and song map selection

## Example Output
```csv
Song Name,Author Name,Difficulty,Song Duration,Song Map
Test Song,Test Artist,1,180.5,1
```

This represents:
- Song: "Test Song" 
- Artist: "Test Artist"
- Difficulty: 1 (MEDIUM)
- Duration: 180.5 seconds
- Song Map: 1 (DESERT)

## Next Steps
The foundation is now in place for implementing the difficulty and song map functionality. You can now:

1. **Difficulty Implementation**: Use the difficulty value (0-2) to adjust note generation complexity
2. **Song Map Implementation**: Use the song map value (0-2) to select different visual themes/environments
3. **Duration Usage**: Use the calculated duration for better note timing and preview generation

All changes are fully tested and ready for production use.
