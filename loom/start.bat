@echo off
echo.
echo  Loom
echo  ====
echo.
docker compose up -d --build
echo.
echo  Status:
docker compose ps
echo.
echo  Docker Desktop - container loom_engine - Terminal:
echo    python loom.py          (interaktivni meni)
echo    python loom.py status   (hitri status)
echo.
echo  API dokumentacija: http://localhost:8000/api/docs
echo.
pause
