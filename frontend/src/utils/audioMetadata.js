import * as musicMetadata from 'music-metadata-browser';
import { extractMetadataWithJSMediaTags } from './audioMetadataFallback';

/**
 * Extracts metadata from an audio file (MP3, FLAC, WAV, OGG) using multiple methods
 * @param {File|Blob} file - The audio file to extract metadata from
 * @returns {Promise<Object>} - Object containing metadata and artwork
 */
export async function extractAudioMetadata(file) {
  try {
    console.log("Starting metadata extraction for:", file.name);
    
    // Get file extension to determine format
    const fileExtension = file.name.toLowerCase().split('.').pop();
    console.log("Detected file format:", fileExtension);
    
    try {
      // First try with music-metadata-browser (supports multiple formats)
      const metadata = await musicMetadata.parseBlob(file, { skipPostHeaders: true });
      console.log("Raw metadata extracted with music-metadata-browser:", metadata);
        // Extract the required information
      const result = {
        title: metadata.common?.title || '',
        artist: metadata.common?.artist || ''
      };
      
      // Extract album artwork if available
      if (metadata.common?.picture && metadata.common.picture.length > 0) {
        console.log("Found artwork in metadata");
        const picture = metadata.common.picture[0];
        
        // Create a blob from the picture data
        const blob = new Blob([new Uint8Array(picture.data)], { type: picture.format });
        result.artwork = URL.createObjectURL(blob);
        console.log("Created artwork URL:", result.artwork);
      } else {
        console.log("No artwork found in metadata");
        result.artwork = null;
      }
      
      console.log("Extracted metadata with music-metadata-browser:", result);
        // If we have at least some metadata, return it
      if (result.title || result.artist || result.artwork) {
        return result;
      }
    } catch (musicMetadataError) {
      console.error("music-metadata-browser extraction failed:", musicMetadataError);
    }
      // If music-metadata-browser failed or found no metadata, try jsmediatags (mainly for MP3)
    if (fileExtension === 'mp3') {
      console.log("Falling back to jsmediatags extraction for MP3");
      try {
        const jsmediatagsMeta = await extractMetadataWithJSMediaTags(file);
        console.log("Extracted metadata with jsmediatags:", jsmediatagsMeta);
        return jsmediatagsMeta;
      } catch (jsmediatagsError) {
        console.error("jsmediatags extraction failed:", jsmediatagsError);
      }
    }
    
    // If all methods failed, throw error
    throw new Error("All metadata extraction methods failed");  } catch (error) {
    console.error('Error extracting audio metadata:', error);
    throw new Error(`Failed to extract metadata: ${error.message}`);
  }
}

// Keep the old function name for backward compatibility
export const extractMP3Metadata = extractAudioMetadata;