import React, { useState } from "react";
import { FaImage, FaUpload, FaSpinner } from "react-icons/fa";
import axios from "axios";

function ManualAlbumUpload({ onSuccess }) {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    setFile(selectedFile);
    
    if (selectedFile) {
      const reader = new FileReader();
      reader.onload = (e) => setPreview(e.target.result);
      reader.readAsDataURL(selectedFile);
    } else {
      setPreview(null);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!file) {
      setError("Please select an image file.");
      return;
    }
    
    setLoading(true);
    setError("");
    
    const formData = new FormData();
    formData.append("file", file);
    
    try {
      await axios.post("/api/upload_artwork", formData, {
        headers: { "Content-Type": "multipart/form-data" }
      });
      setLoading(false);
      onSuccess && onSuccess();
    } catch (err) {
      setError("Upload failed.");
      setLoading(false);
    }
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="bg-gray-800 rounded-xl p-8 shadow-lg max-w-xl mx-auto mt-8"
    >
      <h2 className="text-2xl font-bold mb-6 flex items-center">
        <FaImage className="mr-2 text-yellow-400" /> Upload Album Art
      </h2>
      
      <div className="mb-4">
        <label className="block font-medium mb-2">
          Select JPEG or PNG image:
          <input
            type="file"
            accept="image/jpeg,image/png"
            onChange={handleFileChange}
            required
            className="block mt-2 w-full text-white bg-gray-700 rounded p-2"
          />
        </label>
      </div>
      
      {preview && (
        <div className="mb-4 text-center">
          <img 
            src={preview} 
            alt="Preview" 
            className="max-w-full max-h-48 rounded mx-auto border border-gray-600" 
          />
        </div>
      )}
      
      <button
        type="submit"
        disabled={loading || !file}
        className="w-full py-3 mt-2 bg-yellow-500 hover:bg-yellow-600 text-gray-900 font-semibold rounded transition flex items-center justify-center disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {loading ? (
          <>
            <FaSpinner className="animate-spin mr-2" /> Uploading...
          </>
        ) : (
          <>
            <FaUpload className="mr-2" /> Upload Album Art
          </>
        )}
      </button>
      
      {error && <div className="text-red-400 mt-2 text-center">{error}</div>}
    </form>
  );
}

export default ManualAlbumUpload;