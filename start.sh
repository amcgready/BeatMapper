#!/bin/bash
# Start backend (Flask API)
(cd backend && py -3.10 app.py) &

# Start frontend (Vite)
(cd frontend && npm run dev) &
wait