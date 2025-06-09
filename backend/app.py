import os
import logging
import json
import uuid
from datetime import datetime

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
import shutil

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

        # Create a unique ID for this beatmap
        beatmap_id = str(uuid.uuid4())
        beatmap_dir = os.path.join(OUTPUT_DIR, beatmap_id)
        os.makedirs(beatmap_dir, exist_ok=True)

        mp3_path = os.path.join(beatmap_dir, 'song.mp3')
        try:
            file.save(mp3_path)
            app.logger.info("MP3 saved")
        except Exception as e:
            app.logger.error(f"Failed to save MP3 file: {e}")
            return jsonify({'error': f'Failed to save MP3 file: {str(e)}'}), 500

        # Set up metadata from the filename
        title = os.path.splitext(filename)[0]
        song_metadata = {
            "title": title,
            "artist": request.form.get("artist", "Unknown Artist"),
            "album": request.form.get("album", "Unknown Album"),
            "year": request.form.get("year", str(datetime.now().year)),
            "genre": request.form.get("genre", "Unknown Genre")
        }

        ogg_path = os.path.join(beatmap_dir, 'song.ogg')
        app.logger.info("Converting MP3 to OGG")
        try:
            if not mp3_to_ogg(mp3_path, ogg_path):
                app.logger.error("Failed to convert MP3 to OGG.")
                return jsonify({'error': 'Failed to convert MP3 to OGG'}), 500
        except Exception as e:
            app.logger.error(f"Exception in MP3 to OGG conversion: {e}")
            return jsonify({'error': f'Failed to convert MP3 to OGG: {str(e)}'}), 500

        preview_path = os.path.join(beatmap_dir, 'preview.ogg')
        app.logger.info("Generating preview")
        try:
            if not generate_preview(mp3_path, preview_path):
                app.logger.error("Failed to generate preview.")
                return jsonify({'error': 'Failed to generate preview'}), 500
        except Exception as e:
            app.logger.error(f"Exception in preview generation: {e}")
            return jsonify({'error': f'Failed to generate preview: {str(e)}'}), 500

        notes_path = os.path.join(beatmap_dir, 'notes.csv')
        app.logger.info("Generating notes.csv")
        try:
            if not generate_notes_csv(mp3_path, TEMPLATE_PATH, notes_path):
                app.logger.error("Failed to generate notes.csv")
                return jsonify({'error': 'Failed to generate notes.csv'}), 500
        except Exception as e:
            app.logger.error(f"Failed to generate notes.csv: {e}")
            return jsonify({'error': f'Failed to generate notes.csv: {str(e)}'}), 500

        # Verify and fix notes.csv if needed
        try:
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
        except Exception as validation_error:
            app.logger.error(f"Error validating notes.csv: {validation_error}")

        info_path = os.path.join(beatmap_dir, 'info.csv')
        app.logger.info("Generating info.csv")
        try:
            if not generate_info_csv(song_metadata, info_path):
                app.logger.error("Failed to generate info.csv.")
                return jsonify({'error': 'Failed to generate info.csv'}), 500
        except Exception as e:
            app.logger.error(f"Exception in info.csv generation: {e}")
            return jsonify({'error': f'Failed to generate info.csv: {str(e)}'}), 500

        # Create a simple placeholder album.jpg file if needed
        album_path = os.path.join(beatmap_dir, 'album.jpg')
        if not os.path.exists(album_path):
            try:
                # Create an empty file as placeholder
                with open(album_path, 'wb') as f:
                    pass
                app.logger.info("Created placeholder album.jpg")
            except Exception as e:
                app.logger.warning(f"Failed to create placeholder album.jpg: {e}")

        # Create ZIP file with all required files
        try:
            files_to_zip = [
                ('song.ogg', 'song.ogg'),
                ('preview.ogg', 'preview.ogg'),
                ('notes.csv', 'notes.csv'),
                ('info.csv', 'info.csv'),
                ('album.jpg', 'album.jpg')
            ]
            
            zip_path = os.path.join(beatmap_dir, 'beatmap.zip')
            with zipfile.ZipFile(zip_path, 'w') as zipf:
                for src_name, dest_name in files_to_zip:
                    file_path = os.path.join(beatmap_dir, src_name)
                    if os.path.exists(file_path):
                        zipf.write(file_path, dest_name)
            
            app.logger.info(f"Created ZIP file at {zip_path}")
        except Exception as e:
            app.logger.error(f"Failed to create ZIP file: {e}")
            return jsonify({'error': f'Failed to create ZIP file: {str(e)}'}), 500

        # Save beatmap metadata
        metadata_path = os.path.join(OUTPUT_DIR, 'beatmaps.json')
        beatmaps = []
        
        if os.path.exists(metadata_path):
            try:
                with open(metadata_path, 'r') as f:
                    beatmaps = json.load(f)
            except:
                beatmaps = []
        
        # Add new beatmap to metadata
        beatmap_info = {
            "id": beatmap_id,
            "title": song_metadata["title"],
            "artist": song_metadata["artist"],
            "album": song_metadata["album"],
            "year": song_metadata["year"],
            "createdAt": datetime.now().isoformat()
        }
        
        beatmaps.append(beatmap_info)
        
        with open(metadata_path, 'w') as f:
            json.dump(beatmaps, f)
        
        app.logger.info(f"Added beatmap to metadata: {beatmap_id}")

        # Return beatmap info as JSON
        return jsonify({
            'status': 'success', 
            'message': 'Beatmap created successfully',
            'id': beatmap_id,
            'title': song_metadata["title"],
            'artist': song_metadata["artist"],
            'album': song_metadata["album"],
            'year': song_metadata["year"]
        })
        
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

@app.route('/api/beatmaps', methods=['GET'])
def get_beatmaps():
    """Get all beatmaps in the output directory"""
    try:
        beatmaps = []
        # Check for a metadata file that stores beatmap info
        metadata_path = os.path.join(OUTPUT_DIR, 'beatmaps.json')
        
        if os.path.exists(metadata_path):
            with open(metadata_path, 'r') as f:
                beatmaps = json.load(f)
        
        return jsonify({'beatmaps': beatmaps})
    except Exception as e:
        app.logger.error(f"Failed to get beatmaps: {e}")
        return jsonify({'error': 'Failed to get beatmaps'}), 500

@app.route('/api/beatmap/<beatmap_id>', methods=['DELETE'])
def delete_beatmap(beatmap_id):
    """Delete a beatmap"""
    try:
        # Find and remove the beatmap from metadata
        metadata_path = os.path.join(OUTPUT_DIR, 'beatmaps.json')
        beatmaps = []
        
        if os.path.exists(metadata_path):
            with open(metadata_path, 'r') as f:
                beatmaps = json.load(f)
        
        # Filter out the deleted beatmap
        beatmaps = [b for b in beatmaps if b['id'] != beatmap_id]
        
        # Save updated metadata
        with open(metadata_path, 'w') as f:
            json.dump(beatmaps, f)
        
        # Delete the associated files
        beatmap_dir = os.path.join(OUTPUT_DIR, beatmap_id)
        if os.path.exists(beatmap_dir):
            shutil.rmtree(beatmap_dir)
            app.logger.info(f"Deleted beatmap directory: {beatmap_id}")
        
        return jsonify({'status': 'Beatmap deleted'})
    except Exception as e:
        app.logger.error(f"Failed to delete beatmap: {e}")
        return jsonify({'error': 'Failed to delete beatmap'}), 500

@app.route('/api/clear_beatmaps', methods=['POST'])
def clear_beatmaps():
    """Clear all beatmaps"""
    try:
        # Clear the metadata
        metadata_path = os.path.join(OUTPUT_DIR, 'beatmaps.json')
        with open(metadata_path, 'w') as f:
            json.dump([], f)
        
        # Delete all beatmap directories except for the current working files
        for item in os.listdir(OUTPUT_DIR):
            item_path = os.path.join(OUTPUT_DIR, item)
            if os.path.isdir(item_path):
                shutil.rmtree(item_path)
                app.logger.info(f"Deleted directory: {item}")
        
        return jsonify({'status': 'All beatmaps cleared'})
    except Exception as e:
        app.logger.error(f"Failed to clear beatmaps: {e}")
        return jsonify({'error': 'Failed to clear beatmaps'}), 500

@app.route('/api/update_metadata', methods=['POST'])
def update_metadata():
    """Update beatmap metadata"""
    try:
        data = request.json
        beatmap_id = data.get('id')
        
        # Read existing metadata
        metadata_path = os.path.join(OUTPUT_DIR, 'beatmaps.json')
        beatmaps = []
        
        if os.path.exists(metadata_path):
            with open(metadata_path, 'r') as f:
                beatmaps = json.load(f)
        
        # Update the specified beatmap
        updated = False
        for beatmap in beatmaps:
            if beatmap['id'] == beatmap_id:
                beatmap['title'] = data.get('title', beatmap.get('title', ''))
                beatmap['artist'] = data.get('artist', beatmap.get('artist', ''))
                beatmap['album'] = data.get('album', beatmap.get('album', ''))
                beatmap['year'] = data.get('year', beatmap.get('year', ''))
                updated = True
                break
        
        if not updated:
            return jsonify({'error': 'Beatmap not found'}), 404
            
        # Save updated metadata
        with open(metadata_path, 'w') as f:
            json.dump(beatmaps, f)
        
        # Update the beatmap's info.csv file if it exists
        beatmap_dir = os.path.join(OUTPUT_DIR, beatmap_id)
        info_path = os.path.join(beatmap_dir, 'info.csv')
        
        if os.path.exists(info_path):
            song_metadata = {
                "title": data.get('title', ''),
                "artist": data.get('artist', ''),
                "album": data.get('album', ''),
                "year": data.get('year', ''),
                "genre": data.get('genre', 'Unknown')
            }
            generate_info_csv(song_metadata, info_path)
        
        return jsonify({'status': 'Metadata updated'})
    except Exception as e:
        app.logger.error(f"Failed to update metadata: {e}")
        return jsonify({'error': 'Failed to update metadata'}), 500

@app.route('/api/download_beatmap/<beatmap_id>', methods=['GET'])
def download_beatmap(beatmap_id):
    """Download a beatmap as a ZIP file"""
    try:
        # Find the beatmap metadata
        metadata_path = os.path.join(OUTPUT_DIR, 'beatmaps.json')
        beatmap = None
        
        if os.path.exists(metadata_path):
            with open(metadata_path, 'r') as f:
                beatmaps = json.load(f)
                
            # Find the requested beatmap
            for b in beatmaps:
                if b['id'] == beatmap_id:
                    beatmap = b
                    break
        
        if not beatmap:
            return jsonify({'error': 'Beatmap not found'}), 404
        
        # Check if the beatmap directory exists
        beatmap_dir = os.path.join(OUTPUT_DIR, beatmap_id)
        if not os.path.exists(beatmap_dir):
            return jsonify({'error': 'Beatmap files not found'}), 404
        
        # Create a ZIP file with the beatmap files
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w') as zipf:
            for file in os.listdir(beatmap_dir):
                file_path = os.path.join(beatmap_dir, file)
                if os.path.isfile(file_path):
                    zipf.write(file_path, file)
        
        zip_buffer.seek(0)
        return send_file(
            zip_buffer,
            mimetype="application/zip",
            as_attachment=True,
            download_name=f"{beatmap['title']}_beatmap.zip"
        )
    except Exception as e:
        app.logger.error(f"Failed to download beatmap: {e}")
        return jsonify({'error': 'Failed to download beatmap'}), 500

# Call at startup
if __name__ == '__main__':
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    cleanup_output_dir(days=7)
    app.run(debug=False)