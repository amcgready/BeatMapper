import * as musicMetadata from 'music-metadata-browser';
import { extractMetadataWithJSMediaTags } from './audioMetadataFallback';

/**
 * Extracts metadata from an MP3 file using multiple methods
 * @param {File|Blob} file - The MP3 file to extract metadata from
 * @returns {Promise<Object>} - Object containing metadata and artwork
 */
export async function extractMP3Metadata(file) {
  try {
    console.log("Starting metadata extraction for:", file.name);
    
    try {
      // First try with music-metadata-browser
      const metadata = await musicMetadata.parseBlob(file, { skipPostHeaders: true });
      console.log("Raw metadata extracted with music-metadata-browser:", metadata);
      
      // Extract the required information
      const result = {
        title: metadata.common?.title || '',
        artist: metadata.common?.artist || '',
        album: metadata.common?.album || '',
        year: metadata.common?.year || null
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
      if (result.title || result.artist || result.album || result.artwork) {
        return result;
      }
    } catch (musicMetadataError) {
      console.error("music-metadata-browser extraction failed:", musicMetadataError);
    }
    
    // If music-metadata-browser failed or found no metadata, try jsmediatags
    console.log("Falling back to jsmediatags extraction");
    try {
      const jsmediatagsMeta = await extractMetadataWithJSMediaTags(file);
      console.log("Extracted metadata with jsmediatags:", jsmediatagsMeta);
      return jsmediatagsMeta;
    } catch (jsmediatagsError) {
      console.error("jsmediatags extraction failed:", jsmediatagsError);
      throw new Error("All metadata extraction methods failed");
    }
  } catch (error) {
    console.error('Error extracting MP3 metadata:', error);
    throw new Error(`Failed to extract metadata: ${error.message}`);
  }
}