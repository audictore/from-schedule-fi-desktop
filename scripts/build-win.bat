@echo off
REM Build local del instalador (solo en una PC SIN Smart App Control, p.ej. una VM).
REM En tu PC actual NO funciona: Smart App Control bloquea OR-Tools nativo.
REM Para builds normales usa GitHub Actions (push) — ver BUILD.md.
setlocal
cd /d "%~dp0\.."

echo [1/4] Dependencias del solver...
pip install -r solver/requirements.txt || goto err

echo [2/4] Empaquetando el solver (PyInstaller)...
pushd solver
pyinstaller --noconfirm solver_ipc.spec --distpath dist --workpath build || (popd & goto err)
popd

echo [3/4] Icono + dependencias de Node...
pip install Pillow >nul 2>&1
python scripts/make_icon.py || goto err
call npm ci || goto err

echo [4/4] Construyendo el instalador (electron-builder)...
call npm run build:win || goto err

echo.
echo  LISTO. El instalador esta en la carpeta  dist\
exit /b 0

:err
echo.
echo  *** Fallo el build. Revisa los mensajes de arriba. ***
exit /b 1
