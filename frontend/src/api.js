import axios from "axios";

export const uploadSong = (formData) =>
  axios.post("/api/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" }
  });