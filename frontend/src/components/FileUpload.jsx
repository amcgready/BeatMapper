import React, { useState } from "react";
import { FaUpload, FaMusic, FaImage, FaSpinner } from "react-icons/fa";
import { parseBlob } from "music-metadata";

function FileUpload({ onSuccess, setLog }) {
  const [mp3, setMp3] = useState(null);
  const [album, setAlbum] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleFileChange = async (e) => {
    const file = e.target.files[0];
    setMp3(file);
    setLog("Extracting metadata...");
    setLoading(true);
    try {
      const metadata = await parseBlob(file);
      const common = metadata.common || {};
      let artworkUrl = "";
      if (common.picture && common.picture[0]) {
        const blob = new Blob([common.picture[0].data], { type: common.picture[0].format });
        artworkUrl = URL.createObjectURL(blob);
      }
      onSuccess(
        {
          title: common.title || "",
          artist: common.artist || "",
          album: common.album || "",
          year: common.year || "",
          artwork: artworkUrl,
        },
        file,
        album
      );
    } catch (err) {
      setLog("Could not extract metadata.");
      onSuccess({ title: "", artist: "", album: "", year: "", artwork: "" }, file, album);
    }
    setLoading(false);
  };

  const handleAlbumChange = (e) => {
    setAlbum(e.target.files[0]);
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!mp3) {
      setError("Please select an MP3 file.");
      return;
    }
    setError("");
    // Extraction is handled on file select, so just finish here
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="w-full flex flex-col items-center space-y-4"
    >
      <label className="w-full flex flex-col items-center bg-gray-900/70 border-2 border-dashed border-yellow-400 rounded-lg p-6 cursor-pointer hover:bg-gray-800 transition">
        <FaMusic className="text-3xl text-yellow-300 mb-2" />
        <span className="font-semibold mb-2">Select MP3 File</span>
        <input
          type="file"
          accept=".mp3"
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