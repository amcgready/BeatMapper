import csv
import logging
import os

logging.basicConfig(level=logging.INFO)

INFO_HEADER = ["Title", "Artist", "Album", "Year", "Genre"]

def validate_metadata(song_metadata):
    """
    Validates and sanitizes song metadata.
    Returns a dict with all required fields.
    """
    validated = {}
    for key in ["title", "artist", "album", "year", "genre"]:
        value = song_metadata.get(key, "")
        if key == "year":
            # Ensure year is a 4-digit number or empty
            if value and (not str(value).isdigit() or len(str(value)) != 4):
                logging.warning(f"Invalid year '{value}', setting as empty.")
                value = ""
        validated[key] = str(value).strip()
    return validated

def generate_info_csv(song_metadata, output_path):
    """
    Writes song metadata to info.csv with validation and logging.
    Args:
        song_metadata (dict): Metadata with keys title, artist, album, year, genre.
        output_path (str): Path to save the info.csv file.
    Returns:
        bool: True if successful, False otherwise.
    """
    try:
        if not output_path.lower().endswith('.csv'):
            logging.error("Output path must be a .csv file.")
            return False
        validated = validate_metadata(song_metadata)
        row = [
            validated.get("title", ""),
            validated.get("artist", ""),
            validated.get("album", ""),
            validated.get("year", ""),
            validated.get("genre", "")
        ]
        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(INFO_HEADER)
            writer.writerow(row)
        logging.info(f"info.csv generated at {output_path}")
        return True
    except Exception as e:
        logging.error(f"Failed to generate info.csv: {e}")
        return False