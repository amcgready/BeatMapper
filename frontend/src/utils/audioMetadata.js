import * as musicMetadata from 'music-metadata-browser';

/**
 * Extracts metadata from an MP3 file with focus on core fields (title, artist, artwork)
 * @param {File|Blob} file - The MP3 file to extract metadata from
 * @returns {Promise<Object>} - Object containing metadata and artwork
 */
export async function extractMP3Metadata(file) {
  // Store the logs for debugging
  const logs = [];
  const log = (msg) => {
    console.log(msg);
    logs.push(msg);
  };

  try {
    log(`Starting extraction for: ${file.name}`);
    
    // Create an array of extraction methods to try in sequence
    const extractionMethods = [
      tryMusicMetadata,
      tryDirectImageExtraction,
      tryJSMediaTags
    ];
    
    // Initialize result with filename as backup
    const fileName = file.name.replace(/\.[^/.]+$/, "");
    let result = {
      title: fileName,
      artist: "",
      album: "",
      year: null,
      artwork: null,
      _logs: logs
    };
    
    // Try each method until we get good metadata
    for (const method of extractionMethods) {
      log(`Trying extraction method: ${method.name}`);
      
      try {
        const metadata = await method(file);
        log(`Method ${method.name} returned: ${JSON.stringify(metadata, (k, v) => 
          k === 'artwork' && v ? '[IMAGE DATA]' : v)}`);
        
        // Update result with any new metadata found
        if (metadata.title && metadata.title !== fileName) result.title = metadata.title;
        if (metadata.artist) result.artist = metadata.artist;
        if (metadata.album) result.album = metadata.album;
        if (metadata.year) result.year = metadata.year;
        if (metadata.artwork) result.artwork = metadata.artwork;
        
        // If we have the core fields, we can stop trying other methods
        if (result.title && result.artist && result.artwork) {
          log('Obtained all core metadata, stopping extraction');
          break;
        }
      } catch (error) {
        log(`Method ${method.name} failed: ${error.message}`);
      }
    }
    
    // Try to parse artist from filename if still missing
    if (!result.artist) {
      const dashMatch = fileName.match(/^(.*?)\s*-\s*(.*?)$/);
      if (dashMatch) {
        result.artist = dashMatch[1].trim();
        if (result.title === fileName) {
          result.title = dashMatch[2].trim();
        }
        log(`Extracted artist from filename: ${result.artist}`);
      }
    }
    
    log(`Final metadata: ${JSON.stringify(result, (k, v) => 
      k === 'artwork' && v ? '[IMAGE DATA]' : v)}`);
    
    return result;
    
  } catch (error) {
    console.error("Fatal metadata extraction error:", error);
    return {
      title: file.name.replace(/\.[^/.]+$/, ""),
      artist: "",
      album: "",
      year: null,
      artwork: null,
      _error: error.message,
      _logs: logs
    };
  }
}

/**
 * Try extracting with music-metadata-browser
 */
async function tryMusicMetadata(file) {
  const musicMetadata = await import('music-metadata-browser');
  
  try {
    const metadata = await musicMetadata.parseBlob(file, {
      skipCovers: false,
      duration: false
    });
    
    console.log("Music-metadata raw result:", metadata);
    
    const result = {
      title: metadata.common.title || '',
      artist: metadata.common.artist || metadata.common.albumartist || '',
      album: metadata.common.album || '',
      year: metadata.common.year || null
    };
    
    // Process artwork
    if (metadata.common.picture && metadata.common.picture.length > 0) {
      try {
        const picture = metadata.common.picture[0];
        const blob = new Blob([picture.data], { type: picture.format || 'image/jpeg' });
        result.artwork = URL.createObjectURL(blob);
      } catch (err) {
        console.error("Error processing artwork from music-metadata:", err);
      }
    }
    
    return result;
  } catch (error) {
    console.error("Music-metadata extraction failed:", error);
    throw error;
  }
}

/**
 * Try direct binary extraction of image data
 */
async function tryDirectImageExtraction(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = async (e) => {
      try {
        const buffer = e.target.result;
        const array = new Uint8Array(buffer);
        
        // Common image signatures to search for
        const signatures = [
          { type: 'image/jpeg', sig: [0xFF, 0xD8, 0xFF], endSig: [0xFF, 0xD9] },
          { type: 'image/png', sig: [0x89, 0x50, 0x4E, 0x47] }
        ];
        
        // Search for image signatures
        for (const imgFormat of signatures) {
          const { type, sig } = imgFormat;
          
          for (let i = 0; i < array.length - sig.length; i++) {
            let found = true;
            for (let j = 0; j < sig.length; j++) {
              if (array[i + j] !== sig[j]) {
                found = false;
                break;
              }
            }
            
            if (found) {
              console.log(`Found ${type} signature at position ${i}`);
              
              // Extract the image data
              let endPos = array.length;
              
              if (imgFormat.endSig && type === 'image/jpeg') {
                // For JPEG, search for end marker
                for (let k = i + sig.length; k < array.length - 1; k++) {
                  if (array[k] === imgFormat.endSig[0] && array[k + 1] === imgFormat.endSig[1]) {
                    endPos = k + 2;
                    break;
                  }
                }
              }
              
              const imageData = array.slice(i, endPos);
              const blob = new Blob([imageData], { type });
              
              // Test if this is really a valid image
              const imgTest = new Image();
              const url = URL.createObjectURL(blob);
              
              imgTest.onload = () => {
                // Return only if the image loaded successfully
                if (imgTest.width > 10 && imgTest.height > 10) {
                  console.log("Direct extraction found valid image:", imgTest.width, "x", imgTest.height);
                  resolve({ artwork: url });
                } else {
                  URL.revokeObjectURL(url);
                  console.log("Found image is too small or invalid");
                  reject(new Error("Invalid image"));
                }
              };
              
              imgTest.onerror = () => {
                URL.revokeObjectURL(url);
                console.log("Direct extraction found data but not valid image");
                reject(new Error("Invalid image data"));
              };
              
              imgTest.src = url;
              return; // Exit early since we're handling in the callbacks
            }
          }
        }
        
        reject(new Error("No image signature found"));
      } catch (err) {
        reject(err);
      }
    };
    reader.onerror = reject;
    reader.readAsArrayBuffer(file);
  });
}

/**
 * Try extracting metadata using jsmediatags (needs to be loaded dynamically)
 */
async function tryJSMediaTags(file) {
  // We need to load jsmediatags dynamically because it's not an ES module
  return new Promise((resolve, reject) => {
    // Create a script element to load jsmediatags
    const script = document.createElement('script');
    script.src = 'https://cdnjs.cloudflare.com/ajax/libs/jsmediatags/3.9.5/jsmediatags.min.js';
    script.onload = () => {
      if (window.jsmediatags) {
        window.jsmediatags.read(file, {
          onSuccess: (tag) => {
            console.log("JSMediaTags result:", tag);
            
            const result = {
              title: tag.tags.title || '',
              artist: tag.tags.artist || '',
              album: tag.tags.album || '',
              year: tag.tags.year || null
            };
            
            // Handle artwork
            if (tag.tags.picture) {
              const { data, format } = tag.tags.picture;
              const blob = new Blob([new Uint8Array(data)], { type: format });
              result.artwork = URL.createObjectURL(blob);
            }
            
            resolve(result);
          },
          onError: (error) => {
            console.error("JSMediaTags error:", error);
            reject(error);
          }
        });
      } else {
        reject(new Error("Failed to load jsmediatags library"));
      }
    };
    script.onerror = () => reject(new Error("Failed to load jsmediatags script"));
    document.head.appendChild(script);
  });
}