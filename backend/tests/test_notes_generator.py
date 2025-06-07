import unittest
from backend.processing import notes_generator

class TestNotesGenerator(unittest.TestCase):
    def test_custom_drum_mapping(self):
        self.assertEqual(notes_generator.custom_drum_mapping(0), ("Kick", "1"))
        self.assertEqual(notes_generator.custom_drum_mapping(1), ("Snare", "2"))
        self.assertEqual(notes_generator.custom_drum_mapping(2), ("HiHat", "3"))
        self.assertEqual(notes_generator.custom_drum_mapping(99), ("Other", "4"))

    def test_quantize_rows(self):
        rows = [{"Time": 0.123, "Lane": "1"}]
        quantized = notes_generator.quantize_rows(rows, bpm=120, quantization=16)
        self.assertTrue(isinstance(quantized[0]["Time"], float))

    def test_validate_and_format_rows(self):
        header = ["Time", "Lane", "Type", "Length", "Volume", "Pitch", "Effect"]
        rows = [
            {"Time": 0.1, "Lane": "1", "Type": "Hit", "Length": "0.000", "Volume": "100", "Pitch": "Kick", "Effect": "None"},
            {"Time": 0.1, "Lane": "1", "Type": "Hit", "Length": "0.000", "Volume": "100", "Pitch": "Kick", "Effect": "None"},  # duplicate
            {"Time": "", "Lane": "1", "Type": "Hit", "Length": "0.000", "Volume": "100", "Pitch": "Kick", "Effect": "None"},   # missing time
        ]
        validated = notes_generator.validate_and_format_rows(rows, header)
        self.assertEqual(len(validated), 1)  # Only the first row should remain

if __name__ == "__main__":
    unittest.main()