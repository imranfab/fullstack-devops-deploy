@echo off
cd /d "C:\Users\PAREPALLI VINOD\fullstack-assignment\backend"
call ..\venv\Scripts\activate.bat
python manage.py cleanup_conversations
