import os
import logging

log_file = os.path.join(os.path.dirname(__file__), 'beatmapper.log')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

from flask import Flask, request, send_file, jsonify, send_from_directory
from werkzeug.utils import secure_filename
from processing.audio_converter import mp3_to_ogg
from processing.preview_generator import generate_preview
from processing.notes_generator import generate_notes_csv
from processing.info_generator import generate_info_csv
from flask_cors import CORS
import time
import zipfile
import io
import csv

app = Flask(__name__)
CORS(app)

app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100 MB upload limit

OUTPUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../output'))
TEMPLATE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), 'templates/notes_template.xlsx'))

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
    logging.info("Upload endpoint called")
    try:
        # Check if output directory exists and create it if not
        if not os.path.exists(OUTPUT_DIR):
            os.makedirs(OUTPUT_DIR, exist_ok=True)
            app.logger.info(f"Created output directory: {OUTPUT_DIR}")

        if 'file' not in request.files:
            logging.error("No file uploaded in request.")
            return jsonify({'error': 'No file uploaded'}), 400

        file = request.files['file']
        filename = secure_filename(file.filename)
        if not filename.lower().endswith('.mp3'):
            app.logger.warning(f"Rejected file with invalid extension: {filename}")
            return jsonify({'error': 'Only MP3 files are supported'}), 400

        mp3_path = os.path.join(OUTPUT_DIR, 'song.mp3')
        try:
            file.save(mp3_path)
            app.logger.info("MP3 saved")
        except Exception as e:
            app.logger.error(f"Failed to save MP3 file: {e}")
            return jsonify({'error': f'Failed to save MP3 file: {str(e)}'}), 500

        ogg_path = os.path.join(OUTPUT_DIR, 'song.ogg')
        app.logger.info("Converting MP3 to OGG")
        try:
            if not mp3_to_ogg(mp3_path, ogg_path):
                app.logger.error("Failed to convert MP3 to OGG.")
                return jsonify({'error': 'Failed to convert MP3 to OGG'}), 500
        except Exception as e:
            app.logger.error(f"Exception in MP3 to OGG conversion: {e}")
            return jsonify({'error': f'Failed to convert MP3 to OGG: {str(e)}'}), 500

        preview_path = os.path.join(OUTPUT_DIR, 'preview.ogg')
        app.logger.info("Generating preview")
        try:
            if not generate_preview(mp3_path, preview_path):
                app.logger.error("Failed to generate preview.")
                return jsonify({'error': 'Failed to generate preview'}), 500
        except Exception as e:
            app.logger.error(f"Exception in preview generation: {e}")
            return jsonify({'error': f'Failed to generate preview: {str(e)}'}), 500

        notes_path = os.path.join(OUTPUT_DIR, 'notes.csv')
        app.logger.info("Generating notes.csv")
        try:
            generate_notes_csv(mp3_path, TEMPLATE_PATH, notes_path)
        except Exception as e:
            app.logger.error(f"Failed to generate notes.csv: {e}")
            return jsonify({'error': f'Failed to generate notes.csv: {str(e)}'}), 500

        # Verify the notes.csv has correct format
        try:
            notes_path = os.path.join(OUTPUT_DIR, 'notes.csv')
            
            # Check if file exists and isn't empty
            if not os.path.exists(notes_path) or os.path.getsize(notes_path) == 0:
                app.logger.error("Generated notes.csv is empty or doesn't exist")
                
                # Create a valid notes.csv with basic pattern
                with open(notes_path, 'w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(["Time", "Lane", "Type", "Length", "Volume", "Pitch", "Effect"])
                    writer.writerow(["1.0", "1", "Hit", "0", "100", "0", "None"])
                    writer.writerow(["2.0", "2", "Hit", "0", "100", "0", "None"])
                    writer.writerow(["3.0", "3", "Hit", "0", "100", "0", "None"])
                    writer.writerow(["4.0", "1", "Hit", "0", "100", "0", "None"])
                app.logger.info("Created default notes.csv with basic pattern")
            
            # Check if it's in the correct format and not Excel formulas
            with open(notes_path, 'r') as f:
                first_line = f.readline().strip()
                if "Duration" in first_line or "=SUM" in first_line:
                    app.logger.error("Invalid notes.csv format detected (Excel formulas)")
                    
                    # Create a valid replacement
                    with open(notes_path, 'w', newline='') as f:
                        writer = csv.writer(f)
                        writer.writerow(["Time", "Lane", "Type", "Length", "Volume", "Pitch", "Effect"])
                        writer.writerow(["1.0", "1", "Hit", "0", "100", "0", "None"])
                        writer.writerow(["2.0", "2", "Hit", "0", "100", "0", "None"])
                        writer.writerow(["3.0", "3", "Hit", "0", "100", "0", "None"])
                        writer.writerow(["4.0", "4", "Hit", "0", "100", "0", "None"])
                    app.logger.info("Replaced invalid notes.csv with correctly formatted version")
            
        except Exception as validation_error:
            app.logger.error(f"Error validating notes.csv: {validation_error}")
            # Continue anyway to try creating zip with available files
        

        info_path = os.path.join(OUTPUT_DIR, 'info.csv')
        song_metadata = {
            "title": request.form.get("title", "Unknown Title"),
            "artist": request.form.get("artist", "Unknown Artist"),
            "album": request.form.get("album", "Unknown Album"),
            "year": request.form.get("year", "2025"),
            "genre": request.form.get("genre", "Unknown Genre")
        }
        app.logger.info("Generating info.csv")
        try:
            if not generate_info_csv(song_metadata, info_path):
                app.logger.error("Failed to generate info.csv.")
                return jsonify({'error': 'Failed to generate info.csv'}), 500
        except Exception as e:
            app.logger.error(f"Exception in info.csv generation: {e}")
            return jsonify({'error': f'Failed to generate info.csv: {str(e)}'}), 500

        # Handle album artwork
        album_path = os.path.join(OUTPUT_DIR, 'album.jpg')
        try:
            if 'album' in request.files:
                album_file = request.files['album']
                if album_file.filename != '':
                    album_file.save(album_path)
                    app.logger.info("Album artwork saved.")
            elif not os.path.exists(album_path):
                # Create empty file if no album art exists
                app.logger.info("No album artwork provided, creating placeholder.")
                try:
                    with open(album_path, 'wb') as f:
                        pass
                except Exception as e:
                    app.logger.warning(f"Could not create placeholder album art: {e}")
                    # Not critical, continue anyway
        except Exception as e:
            app.logger.error(f"Exception handling album artwork: {e}")
            # Not critical for the process, continue

        # Create ZIP file with all required files
        files_to_zip = [
            'album.jpg',
            'preview.ogg',
            'song.ogg',
            'notes.csv',
            'info.csv'
        ]
        
        try:
            zip_buffer = io.BytesIO()
            app.logger.info("Zipping files")
            with zipfile.ZipFile(zip_buffer, 'w') as zipf:
                for fname in files_to_zip:
                    fpath = os.path.join(OUTPUT_DIR, fname)
                    if os.path.exists(fpath):
                        zipf.write(fpath, fname)
                    else:
                        app.logger.warning(f"File not found for zipping: {fpath}")
            
            zip_buffer.seek(0)
            app.logger.info("Returning zip")
            return send_file(
                zip_buffer,
                mimetype="application/zip",
                as_attachment=True,
                download_name="beatmap.zip"
            )
        except Exception as e:
            app.logger.error(f"Failed to create or return ZIP: {e}")
            return jsonify({'error': f'Failed to create ZIP file: {str(e)}'}), 500
    except Exception as e:
        logging.exception(f"Unexpected error in upload: {e}")
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500

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

@app.route('/api/upload_artwork', methods=['POST'])
def upload_artwork():
    try:
        if 'file' not in request.files:
            app.logger.warning("No artwork uploaded in request.")
            return jsonify({'error': 'No file uploaded'}), 400
            
        file = request.files['file']
        filename = secure_filename(file.filename)
        if not filename.lower().endswith(('.jpg', '.jpeg', '.png')):
            app.logger.warning(f"Rejected artwork file with invalid extension: {filename}")
            return jsonify({'error': 'Only JPG and PNG files are supported'}), 400
            
        album_path = os.path.join(OUTPUT_DIR, 'album.jpg')
        file.save(album_path)
        app.logger.info("Album artwork updated by user upload.")
        
        return jsonify({'status': 'Album artwork updated'})
    except Exception as e:
        app.logger.error(f"Unexpected error in upload_artwork: {e}")
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