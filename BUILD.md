# Cómo generar el instalador `.exe`

La app de escritorio se entrega como un instalador de Windows (`From Schedule FI Setup X.Y.Z.exe`).
El instalador incluye **el solver ya empaquetado** (PyInstaller + OR-Tools), así que el cliente
final **no necesita WSL, ni Python, ni Node** — solo doble clic para instalar.

## Por qué se construye en la nube (GitHub Actions)

OR-Tools usa DLL nativas. En PCs con **Smart App Control encendido** (como la de desarrollo
actual) esas DLL están bloqueadas y no se puede ni empaquetar ni probar el solver nativo.
Los runners de Windows de GitHub **no** tienen Smart App Control, por eso el build se hace ahí.

## Opción recomendada — GitHub Actions

1. Crea un repositorio en GitHub y sube esta carpeta:
   ```bash
   git init
   git add .
   git commit -m "From Schedule FI desktop"
   git branch -M main
   git remote add origin https://github.com/<tu-usuario>/from-schedule-fi-desktop.git
   git push -u origin main
   ```
2. El push dispara el workflow **Build Windows installer** (o ejecútalo a mano en la pestaña
   **Actions → Build Windows installer → Run workflow**).
3. Cuando termine (~10-15 min), descarga el instalador desde **Actions → (la corrida) →
   Artifacts → `From-Schedule-FI-Windows`**.

## Opción alternativa — build local

Solo en una PC o VM de Windows **sin Smart App Control**, con Python 3.12 y Node 20:

```bat
scripts\build-win.bat
```

El instalador queda en `dist\`.

## Firma de código (para producción)

Sin firma, Windows SmartScreen muestra "editor desconocido" al instalar. Para evitarlo
necesitas un **certificado de firma de código** (Authenticode). Una vez que lo tengas,
agrégalo como secrets del repositorio:

- `CSC_LINK` — el `.pfx` en base64
- `CSC_KEY_PASSWORD` — la contraseña del `.pfx`

El workflow ya los usa automáticamente si existen.

## Qué hace el pipeline (resumen)

1. `pip install -r solver/requirements.txt` (OR-Tools + PyInstaller)
2. `pyinstaller solver_ipc.spec` → `solver/dist/solver_ipc/solver_ipc.exe`
3. `python scripts/make_icon.py` → `assets/icon.ico`
4. `npm ci`
5. `npm run build:win` (electron-builder, target NSIS) → `dist/*.exe`

El `electron/solver.js` detecta el modo empaquetado y llama a `solver_ipc.exe` directamente
(sin WSL); en desarrollo sigue usando `wsl python3 solver_ipc.py`.
