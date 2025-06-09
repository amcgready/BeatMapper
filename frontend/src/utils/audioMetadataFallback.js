/**
 * Alternative metadata extraction using jsmediatags
 * @param {File} file - The audio file
 * @returns {Promise<Object>} - Extracted metadata
 */
export function extractMetadataWithJSMediaTags(file) {
  return new Promise((resolve, reject) => {
    const script = document.createElement('script');
    script.src = 'https://cdnjs.cloudflare.com/ajax/libs/jsmediatags/3.9.5/jsmediatags.min.js';
    script.onload = () => {
      window.jsmediatags.read(file, {
        onSuccess: (tag) => {
          console.log("jsmediatags extraction successful:", tag);
          
          const result = {
            title: tag.tags.title || '',
            artist: tag.tags.artist || '',
            album: tag.tags.album || '',
            year: tag.tags.year || null,
            artwork: null
          };
          
          // Extract artwork if available
          if (tag.tags.picture) {
            const { data, format } = tag.tags.picture;
            let base64String = "";
            for (let i = 0; i < data.length; i++) {
              base64String += String.fromCharCode(data[i]);
            }
            
            const base64 = "data:" + format + ";base64," + 
                          window.btoa(base64String);
            result.artwork = base64;
          }
          
          resolve(result);
        },
        onError: (error) => {
          console.error("jsmediatags error:", error);
          reject(error);
        }
      });
    };
    script.onerror = (error) => {
      console.error("Failed to load jsmediatags:", error);
      reject(new Error("Failed to load metadata extraction library"));
    };
    document.head.appendChild(script);
  });
}