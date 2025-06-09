import unittest
import os
from backend.processing import audio_converter, preview_generator, info_generator, notes_generator
import madmom
import numpy as np

class TestProcessing(unittest.TestCase):
    def setUp(self):
        self.test_mp3 = "test_song.mp3"  # Place a small valid MP3 here for testing
        self.test_ogg = "test_song.ogg"
        self.test_preview = "test_preview.ogg"
        self.test_info = "test_info.csv"
        self.test_notes = "test_notes.csv"
        self.template = "backend/templates/notes_template.xlsx"
        self.song_metadata = {
            "title": "Test Song",
            "artist": "Test Artist",
            "album": "Test Album",
            "year": "2025",
            "genre": "Rock"
        }

    def tearDown(self):
        for f in [self.test_ogg, self.test_preview, self.test_info, self.test_notes]:
            if os.path.exists(f):
                os.remove(f)

    def test_mp3_to_ogg(self):
        result = audio_converter.mp3_to_ogg(self.test_mp3, self.test_ogg)
        self.assertTrue(result)
        self.assertTrue(os.path.exists(self.test_ogg))

    def test_generate_preview(self):
        result = preview_generator.generate_preview(self.test_mp3, self.test_preview)
        self.assertTrue(result)
        self.assertTrue(os.path.exists(self.test_preview))

    def test_generate_info_csv(self):
        result = info_generator.generate_info_csv(self.song_metadata, self.test_info)
        self.assertTrue(result)
        self.assertTrue(os.path.exists(self.test_info))

    def test_generate_notes_csv(self):
        # This test assumes Spleeter/madmom are installed and the template exists
        notes_generator.generate_notes_csv(self.test_mp3, self.template, self.test_notes, bpm=120, quantization=16)
        self.assertTrue(os.path.exists(self.test_notes))

    # 4. Add madmom drum detection as a separate process (optional, advanced)
    def madmom_onsets(self, audio_path):
        proc = madmom.features.onsets.OnsetPeakPickingProcessor(fps=100)
        act = madmom.features.onsets.OnsetPeakPickingProcessor()(audio_path)
        return act  # List of onset times in seconds

if __name__ == "__main__":
    unittest.main()