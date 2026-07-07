# 1. Install Python dependencies
pip install pygame pyinstaller

# 2. (Optional but recommended) Build the standalone EXE
pyinstaller --onefile --noconsole --name "Meridian Explorer" meridian_explorer.py