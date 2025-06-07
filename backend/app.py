from flask import Flask, request, send_from_directory, jsonify
from werkzeug.utils import secure_filename
from processing.audio_converter import mp3_to_ogg
from processing.preview_generator import generate_preview
from processing.notes_generator import generate_notes_csv
from processing.info_generator import generate_info_csv
import os
import logging
import time
from functools import wraps
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100 MB upload limit

OUTPUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../output'))
TEMPLATE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), 'templates/notes_template.xlsx'))

logging.basicConfig(level=logging.INFO)

def cleanup_output_dir(days=7):
    now = time.time()
    cutoff = now - days * 86400
    for filename in os.listdir(OUTPUT_DIR):
        file_path = os.path.join(OUTPUT_DIR, filename)
        if os.path.isfile(file_path):
            if os.path.getmtime(file_path) < cutoff:
                try:
                    os.remove(file_path)
                    app.logger.info(f"Deleted old file: {filename}")
                except Exception as e:
                    app.logger.error(f"Failed to delete {filename}: {e}")

@app.route('/api/health')
def health():
    return jsonify({"status": "ok"})

@app.route('/api/upload', methods=['POST'])
def upload():
    try:
        if 'file' not in request.files:
            app.logger.warning("No file uploaded in request.")
            return jsonify({'error': 'No file uploaded'}), 400
        file = request.files['file']
        filename = secure_filename(file.filename)
        if not filename.lower().endswith('.mp3'):
            app.logger.warning(f"Rejected file with invalid extension: {filename}")
            return jsonify({'error': 'Only MP3 files are supported'}), 400

        mp3_path = os.path.join(OUTPUT_DIR, 'song.mp3')
        file.save(mp3_path)

        # Convert to OGG
        ogg_path = os.path.join(OUTPUT_DIR, 'song.ogg')
        if not mp3_to_ogg(mp3_path, ogg_path):
            app.logger.error("Failed to convert MP3 to OGG.")
            return jsonify({'error': 'Failed to convert MP3 to OGG'}), 500

        # Generate preview
        preview_path = os.path.join(OUTPUT_DIR, 'preview.ogg')
        if not generate_preview(mp3_path, preview_path):
            app.logger.error("Failed to generate preview.")
            return jsonify({'error': 'Failed to generate preview'}), 500

        # Generate notes.csv
        notes_path = os.path.join(OUTPUT_DIR, 'notes.csv')
        try:
            bpm = request.form.get("bpm", None)
            quantization = request.form.get("quantization", 16)
            bpm = float(bpm) if bpm else None
            quantization = int(quantization)
            generate_notes_csv(mp3_path, TEMPLATE_PATH, notes_path, bpm=bpm, quantization=quantization)
        except Exception as e:
            app.logger.error(f"Failed to generate notes.csv: {e}")
            return jsonify({'error': f'Failed to generate notes.csv: {str(e)}'}), 500

        # Generate info.csv
        info_path = os.path.join(OUTPUT_DIR, 'info.csv')
        song_metadata = {
            "title": request.form.get("title", "Unknown Title"),
            "artist": request.form.get("artist", "Unknown Artist"),
            "album": request.form.get("album", "Unknown Album"),
            "year": request.form.get("year", "2025"),
            "genre": request.form.get("genre", "Unknown Genre")
        }
        if not generate_info_csv(song_metadata, info_path):
            app.logger.error("Failed to generate info.csv.")
            return jsonify({'error': 'Failed to generate info.csv'}), 500

        # Copy album art if provided
        if 'album' in request.files:
            album_file = request.files['album']
            album_filename = secure_filename(album_file.filename)
            album_file.save(os.path.join(OUTPUT_DIR, 'album.jpg'))

        app.logger.info(f"Upload and processing successful for {filename}")
        return jsonify({'status': 'success'})
    except Exception as e:
        app.logger.error(f"Unexpected error in upload: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/upload_notes', methods=['POST'])
def upload_notes():
    try:
        if 'file' not in request.files:
            app.logger.warning("No notes.csv uploaded in request.")
            return jsonify({'error': 'No file uploaded'}), 400
        file = request.files['file']
        filename = secure_filename(file.filename)
        if not filename.lower().endswith('.csv'):
            app.logger.warning(f"Rejected notes file with invalid extension: {filename}")
            return jsonify({'error': 'Only CSV files are supported'}), 400
        notes_path = os.path.join(OUTPUT_DIR, 'notes.csv')
        file.save(notes_path)
        app.logger.info("notes.csv updated by user upload.")
        return jsonify({'status': 'notes.csv updated'})
    except Exception as e:
        app.logger.error(f"Unexpected error in upload_notes: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/download/<filename>')
def download(filename):
    try:
        safe_filename = secure_filename(filename)
        file_path = os.path.join(OUTPUT_DIR, safe_filename)
        if not os.path.exists(file_path):
            app.logger.warning(f"Requested file does not exist: {safe_filename}")
            return jsonify({'error': 'File not found'}), 404
        return send_from_directory(OUTPUT_DIR, safe_filename, as_attachment=True)
    except Exception as e:
        app.logger.error(f"Unexpected error in download: {e}")
        return jsonify({'error': 'Internal server error'}), 500

# Call at startup
if __name__ == '__main__':
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    cleanup_output_dir(days=7)
    app.run(debug=False)