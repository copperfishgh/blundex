# Building Blundex Executable

## Prerequisites

1. **Install PyInstaller:**
   ```bash
   pip install pyinstaller
   ```

2. **Ensure all dependencies are installed:**
   ```bash
   pip install -r requirements.txt
   ```

## Build Single Executable

Run this command from the `python/` directory:

```bash
pyinstaller Blundex.spec
```

## Output

The executable will be created at:
- **Windows**: `dist/Blundex.exe`
- **Mac**: `dist/Blundex` (Unix executable)
- **Linux**: `dist/Blundex` (Unix executable)

## Distribution

Simply share the executable from the `dist/` folder. Users can run it without installing Python.

**File size**: Approximately 15-20 MB (includes Python runtime, dependencies, and assets)

## Optional: Add an Icon

1. Create or download a `.ico` file (Windows) or `.icns` file (Mac)
2. Save it as `blundex.ico` in the `python/` directory
3. Edit `Blundex.spec` and change:
   ```python
   icon=None,
   ```
   to:
   ```python
   icon='blundex.ico',
   ```
4. Rebuild: `pyinstaller Blundex.spec`

## Troubleshooting

**Missing assets error:**
- Ensure the `pngs/` folder exists in the python directory
- Check that all PNG files are present in `pngs/2x/`

**Import errors:**
- Install missing packages with pip
- Add any missing imports to `hiddenimports=[]` in the spec file

**Antivirus false positives:**
- Some antivirus software flags PyInstaller executables
- This is a known issue with all PyInstaller apps
- Users may need to whitelist the executable

## Clean Build

To remove build artifacts:
```bash
# Windows
rmdir /s /q build dist
del Blundex.spec

# Mac/Linux
rm -rf build dist __pycache__
rm *.spec
```

Then rebuild with `pyinstaller Blundex.spec`
