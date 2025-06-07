import csv
import librosa
import numpy as np
import soundfile as sf
import os
import logging
from openpyxl import load_workbook
import subprocess
import sys

logging.basicConfig(level=logging.INFO)

ALLOWED_LANES = {"1", "2", "3", "4"}
ALLOWED_TYPES = {"Hit"}
ALLOWED_EFFECTS = {"None"}

def get_template_header(template_path):
    try:
        wb = load_workbook(template_path)
        ws = wb.active
        header = [cell.value for cell in next(ws.iter_rows(min_row=1, max_row=1))]
        return header
    except Exception as e:
        logging.error(f"Failed to read template: {e}")
        return ["Time", "Lane", "Type", "Length", "Volume", "Pitch", "Effect"]

def separate_drums(mp3_path, output_dir):
    try:
        separator = Separator('spleeter:2stems')
        separator.separate_to_file(mp3_path, output_dir)
        song_name = os.path.splitext(os.path.basename(mp3_path))[0]
        drum_path = os.path.join(output_dir, song_name, 'drums.wav')
        if not os.path.exists(drum_path):
            raise FileNotFoundError(f"Drum stem not found at {drum_path}")
        return drum_path
    except Exception as e:
        logging.error(f"Spleeter separation failed: {e}")
        return None

def spleeter_separate(mp3_path, output_dir, spleeter_venv_path="spleeter_venv"):
    """
    Runs Spleeter in a separate virtual environment as a subprocess.
    """
    python_exe = os.path.join(spleeter_venv_path, "Scripts", "python.exe")
    command = [
        python_exe, "-m", "spleeter", "separate",
        "-p", "spleeter:2stems",
        "-o", output_dir,
        mp3_path
    ]
    try:
        subprocess.check_call(command)
        song_name = os.path.splitext(os.path.basename(mp3_path))[0]
        drum_path = os.path.join(output_dir, song_name, "drums.wav")
        other_path = os.path.join(output_dir, song_name, "accompaniment.wav")
        if not os.path.exists(drum_path):
            raise FileNotFoundError(f"Drum stem not found at {drum_path}")
        return drum_path, other_path
    except Exception as e:
        logging.error(f"Spleeter separation failed: {e}")
        return None, None

def librosa_backup(mp3_path):
    try:
        y, sr = librosa.load(mp3_path, sr=None, mono=True)
        onset_frames = librosa.onset.onset_detect(y=y, sr=sr, backtrack=True)
        onset_times = librosa.frames_to_time(onset_frames, sr=sr)
        rows = []
        for t in onset_times:
            rows.append({
                "Time": t,
                "Lane": "1",
                "Type": "Hit",
                "Length": "0.000",
                "Volume": "100",
                "Pitch": "Unknown",
                "Effect": "None"
            })
        return rows
    except Exception as e:
        logging.error(f"librosa backup failed: {e}")
        return []

def quantize_rows(rows, bpm=120, quantization=16):
    # Snap times to nearest grid (e.g., 1/16th note)
    beat_length = 60.0 / bpm
    grid = beat_length / (quantization / 4)
    for row in rows:
        t = row["Time"]
        quantized = round(t / grid) * grid
        row["Time"] = quantized
    return rows

def post_process(rows, min_interval=0.05):
    processed = []
    last_time = {}
    for row in rows:
        lane = row["Lane"]
        t = row["Time"]
        if lane not in last_time or t - last_time[lane] > min_interval:
            processed.append(row)
            last_time[lane] = t
    return processed

def validate_and_format_rows(rows, header, min_interval=0.05):
    formatted = []
    last_time = {}
    for row in rows:
        try:
            t = float(row.get("Time", 0))
            lane = str(row.get("Lane", "1"))
            typ = row.get("Type", "Hit")
            effect = row.get("Effect", "None")
            # Check for NaN or missing
            if any(x == "" or x is None for x in [t, lane, typ, effect]):
                continue
            # Check allowed values
            if lane not in ALLOWED_LANES or typ not in ALLOWED_TYPES or effect not in ALLOWED_EFFECTS:
                continue
            # Check for overlapping notes
            if lane in last_time and abs(t - last_time[lane]) < min_interval:
                continue
            last_time[lane] = t
            # Format row to match header order
            formatted_row = [row.get(col, "") for col in header]
            formatted.append(formatted_row)
        except Exception as e:
            logging.warning(f"Invalid row skipped: {row} ({e})")
            continue
    return formatted

def estimate_bpm(mp3_path):
    try:
        y, sr = librosa.load(mp3_path, sr=None, mono=True)
        tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
        return tempo
    except Exception as e:
        logging.warning(f"BPM estimation failed: {e}")
        return 120  # Default BPM

def generate_notes_csv(mp3_path, template_path, output_path, bpm=None, quantization=16):
    temp_dir = os.path.join(os.path.dirname(output_path), "temp_sep")
    os.makedirs(temp_dir, exist_ok=True)
    header = get_template_header(template_path)
    try:
        stems_dir = "output/stems"
        drum_path, other_path = spleeter_separate(mp3_path, stems_dir)
        if drum_path:
            y, sr = librosa.load(drum_path, sr=None, mono=True)
            onset_frames = librosa.onset.onset_detect(y=y, sr=sr, backtrack=True)
            onset_times = librosa.frames_to_time(onset_frames, sr=sr)
            rows = []
            for t in onset_times:
                rows.append({
                    "Time": t,
                    "Lane": "1",
                    "Type": "Hit",
                    "Length": "0.000",
                    "Volume": "100",
                    "Pitch": "Unknown",
                    "Effect": "None"
                })
        else:
            logging.warning("Spleeter did not return a drum path, using librosa backup.")
            rows = librosa_backup(mp3_path)
        if bpm is None:
            bpm = estimate_bpm(mp3_path)
        rows = quantize_rows(rows, bpm=bpm, quantization=quantization)
        rows = post_process(rows)
        rows = validate_and_format_rows(rows, header)
        if not rows:
            raise ValueError("No valid drum notes detected. Please check your audio file.")
        with open(output_path, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(header)
            writer.writerows(rows)
        logging.info(f"notes.csv generated at {output_path}")
    except Exception as e:
        logging.error(f"Failed to generate notes.csv: {e}")
        raise
    finally:
        import shutil
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)