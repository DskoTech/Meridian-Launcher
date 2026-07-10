# 1. Install Python dependencies
pip install pygame pyinstaller

# 2. (Optional but recommended) Build the standalone EXE
pyinstaller --onefile --noconsole --icon="Meridian_Explorer.ico" --name "Meridian Explorer" meridian_explorer.py