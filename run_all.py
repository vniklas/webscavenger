#!/usr/bin/env python3
"""
Run both scrapers and ensure output/ exists.
"""
import subprocess
import sys
from pathlib import Path
import shutil

SCRIPTS = ["scrape_menu.py", "scrape_malva.py"]


def run_scraper(script_name):
    print(f"\n{'='*50}")
    print(f"Kör {script_name}...")
    print('='*50)
    result = subprocess.run(
        [sys.executable, script_name],
        capture_output=False,
        text=True
    )
    if result.returncode != 0:
        print(f"FEL: {script_name} misslyckades med kod {result.returncode}")
        return False
    return True

def copy_latest_files(output_dir: Path):
    """Kopiera varje fil med veckonamn till en -latest version"""
    print("\nSkapar -latest kopior...")
    prefixes = {
        "alsikeskolan": "alsikeskolan_latest",
        "malva_gymnasiet": "malva_gymnasiet_latest",
    }
    for prefix, latest_base in prefixes.items():
        for ext in ["md", "json"]:
            # Hitta alla filer för prefixet och extension
            files = [f for f in output_dir.glob(f"{prefix}*.{ext}") if "latest" not in f.name]
            if not files:
                continue
            # Välj den med högst veckonummer eller senaste datum
            def week_key(f):
                import re
                # Försök hitta vecka_XX_YYYY eller vecka_XX eller meny_f_r_vecka_XX
                m = re.search(r'vecka[_ ]?(\d{1,2})[_ ]?(\d{4})?', f.name)
                if m:
                    week = int(m.group(1))
                    year = int(m.group(2)) if m.group(2) else 0
                    return (year, week)
                m2 = re.search(r'vecka[_ ]?(\d{1,2})', f.name)
                if m2:
                    return (0, int(m2.group(1)))
                return (0, 0)
            latest_file = max(files, key=week_key)
            dest = output_dir / f"{latest_base}.{ext}"
            shutil.copy2(latest_file, dest)
            print(f"  {latest_file.name} -> {dest.name}")

def commit_and_push():
    """Commit and push output/ folder to repo if changed"""
    print("\nCommittar och pushar output/ till repo...")
    try:
        subprocess.run(["git", "add", "output/"], check=True)
        # Kontrollera om det finns staged ändringar
        diff = subprocess.run(["git", "diff", "--staged", "--quiet"])
        if diff.returncode != 0:
            subprocess.run([
                "git", "commit", "-m",
                f"chore(menus): update latest menu files $(date -u +'%Y-%m-%d') [ci skip]"
            ], check=True)
            subprocess.run(["git", "push"], check=True)
            print("✅ Output pushad till repo!")
        else:
            print("Inga ändringar att committa.")
    except Exception as e:
        print(f"Git commit/push misslyckades: {e}")

if __name__ == "__main__":
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)

    success = True
    for script in ["scrape_menu.py", "scrape_malva.py"]:
        if not run_scraper(script):
            success = False

    copy_latest_files(output_dir)
    commit_and_push()

    if success:
        print("\n✅ Alla scrapers körde klart!")
    else:
        print("\n⚠️  En eller flera scrapers misslyckades.")
        sys.exit(1)
