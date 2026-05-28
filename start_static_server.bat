@echo off
cd /d "%~dp0"
echo Starting static site at http://127.0.0.1:8765/
echo Open: http://127.0.0.1:8765/
start http://127.0.0.1:8765/
python -m http.server 8765 --bind 127.0.0.1
