# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec — empaqueta solver_ipc.py + OR-Tools en un ejecutable nativo
# (modo carpeta/onedir, el más fiable para las DLL nativas de OR-Tools).
# Build:  pyinstaller --noconfirm solver/solver_ipc.spec --distpath solver/dist --workpath solver/build
# Salida: solver/dist/solver_ipc/solver_ipc.exe  (+ dependencias)
from PyInstaller.utils.hooks import collect_all

# Recolecta TODO lo de ortools: datos, binarios (.dll/.so) e imports ocultos.
datas, binaries, hiddenimports = collect_all('ortools')

a = Analysis(
    ['solver_ipc.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'numpy.testing', 'pytest'],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='solver_ipc',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,            # UPX puede romper DLL nativas de OR-Tools
    console=True,         # el motor habla por stdin/stdout (IPC con Electron)
    disable_windowed_traceback=False,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name='solver_ipc',
)
