#!/usr/bin/env python3

import sys
import os
sys.path.append('C:/Users/hypes/OneDrive/Desktop/Projects/BeatMapper/backend')

from processing.info_generator import analyze_notes_difficulty

notes_path = r'C:\Users\hypes\OneDrive\Desktop\Projects\BeatMapper\output\1876a258-319a-44d4-bb97-6439ded2845c\notes.csv'
result = analyze_notes_difficulty(notes_path)
print(f'Difficulty result: {result}')
