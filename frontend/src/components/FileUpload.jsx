import React, { useState } from "react";
import { FaUpload, FaMusic, FaImage, FaSpinner } from "react-icons/fa";
import { extractAudioMetadata } from '../utils/audioMetadata';

function FileUpload({ onSuccess, setLog }) {
  const [audioFile, setAudioFile] = useState(null);
  const [album, setAlbum] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const handleFileChange = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    
    setAudioFile(file);
    setLog("Extracting metadata...");
    setLoading(true);
    
    try {
      console.log("Starting metadata extraction process");
      const metadata = await extractAudioMetadata(file);
      
      console.log("Metadata returned to component:", metadata);
        // Check if we got any meaningful metadata
      const hasMetadata = metadata.title || metadata.artist;
      
      if (!hasMetadata) {
        console.log("No meaningful metadata found in the file");
        setLog("No metadata found in file. Please enter details manually.");
      } else {
        setLog("Metadata extracted successfully");
      }
        onSuccess(
        {
          title: metadata.title || '',
          artist: metadata.artist || '',
          artwork: metadata.artwork || null,
        },
        file,
        album
      );
    } catch (err) {
      console.error("Component level error handling:", err);      setLog("Error extracting metadata. Please enter details manually.");
      onSuccess({ title: "", artist: "", artwork: "" }, file, album);
    } finally {
      setLoading(false);
    }
  };

  const handleAlbumChange = (e) => {
    setAlbum(e.target.files[0]);
  };
  const handleSubmit = (e) => {
    e.preventDefault();
    if (!audioFile) {
      setError("Please select an audio file.");
      return;
    }
    setError("");
    // Extraction is handled on file select, so just finish here
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="w-full flex flex-col items-center space-y-4"
    >      <label className="w-full flex flex-col items-center bg-gray-900/70 border-2 border-dashed border-yellow-400 rounded-lg p-6 cursor-pointer hover:bg-gray-800 transition">
        <FaMusic className="text-3xl text-yellow-300 mb-2" />
        <span className="font-semibold mb-2">Select Audio File</span>
        <span className="text-sm text-gray-400 mb-2">Supported: MP3, FLAC, WAV, OGG</span>
        <input
          type="file"
          accept=".mp3,.flac,.wav,.ogg"
          onChange={handleFileChange}
          required
          className="hidden"
        />
      </label>
      <label className="w-full flex flex-col items-center bg-gray-900/70 border-2 border-dashed border-gray-500 rounded-lg p-6 cursor-pointer hover:bg-gray-800 transition">
        <FaImage className="text-2xl text-yellow-200 mb-2" />
        <span className="font-semibold mb-2">Album Art (optional)</span>
        <input
          type="file"
          accept="image/*"
          onChange={handleAlbumChange}
          className="hidden"
        />
      </label>
      <button
        type="submit"
        disabled={loading}
        className="w-full py-3 mt-2 bg-yellow-400 hover:bg-yellow-500 text-gray-900 font-semibold rounded transition flex items-center justify-center"
      >
        {loading ? (
          <>
            <FaSpinner className="animate-spin mr-2" /> Processing...
          </>
        ) : (
          <>
            <FaUpload className="mr-2" /> Extract Metadata
          </>
        )}
      </button>
      {error && <div className="text-red-400 mt-2">{error}</div>}
    </form>
  );
}

export default FileUpload;