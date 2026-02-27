#!/usr/bin/env python3
"""
Run both scrapers and ensure output/ exists.
"""
import subprocess
import sys
from pathlib import Path

SCRIPTS = ["scrape_menu.py", "scrape_malva.py"]

def main():
    out_dir = Path('output')
    out_dir.mkdir(parents=True, exist_ok=True)

    for script in SCRIPTS:
        print(f"Running {script}...")
        try:
            subprocess.check_call([sys.executable, script])
        except subprocess.CalledProcessError as e:
            print(f"Script {script} failed with exit code {e.returncode}")

    print("Done. Outputs are in ./output/")

if __name__ == '__main__':
    main()
