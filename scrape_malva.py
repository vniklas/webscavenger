#!/usr/bin/env python3
"""
Scraper för Malvas matsedel från Uppsala Gymnasieskolans meny
"""
import requests
from bs4 import BeautifulSoup
import re
import json
from pathlib import Path

def scrape_malva_menu(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    soup = BeautifulSoup(response.content, 'lxml')

    # Hitta aktuell vecka
    week_header = soup.find(lambda tag: tag.name in ['h3', 'h2'] and 'vecka' in tag.get_text(strip=True).lower())
    week = week_header.get_text(strip=True) if week_header else "Okänd vecka"

    # Hitta alla dag-rubriker (t.ex. "Måndag 23 feb") och samla rätter mellan dem
    day_regex = re.compile(r'^(Måndag|Tisdag|Onsdag|Torsdag|Fredag)\b', flags=re.IGNORECASE)

    days = []
    headers = soup.find_all(['h4', 'h3', 'h2'])
    ignore_keywords = ['uppdaterad', 'kakor', 'cookies', 'varje dag serveras', 'salladsbord', 'du har valt', 'vi använder', 'meny för vecka']

    for header in headers:
        header_text = header.get_text(strip=True)
        if not day_regex.match(header_text):
            continue
        current_day = {'day': header_text, 'meals': []}

        # samla strukturerade meal items som (category, dish)
        meal_items = []

        # Iterera över siblings efter header tills nästa dag-header
        for sib in header.next_siblings:
            # Stoppa om vi når nästa dag-header
            if getattr(sib, 'name', None) in ['h2', 'h3', 'h4']:
                sib_head_text = sib.get_text(strip=True)
                if day_regex.match(sib_head_text):
                    break

            # Hämta text från sibling
            if hasattr(sib, 'get_text'):
                text = sib.get_text("\n", strip=True)
            else:
                # navigable string
                text = str(sib).strip()
            if not text:
                continue

            lowered = text.lower()
            if any(k in lowered for k in ignore_keywords):
                continue

            # Dela upp i rader och analysera
            lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
            for idx, ln in enumerate(lines):
                ln_low = ln.lower()
                # Matcha 'Dagens ...' med eventuell rätt på samma rad
                m = re.match(r'^(Dagens(?:\s+[^\s]+)*)\s*(.*)$', ln, flags=re.IGNORECASE)
                if m:
                    category = m.group(1).strip()
                    dish = m.group(2).strip()
                    # Om ingen rätt på samma rad, försök hitta i nästa rad
                    if not dish:
                        # kolla nästa rad i samma block
                        if idx + 1 < len(lines):
                            candidate = lines[idx + 1].strip()
                            if candidate and not any(k in candidate.lower() for k in ignore_keywords):
                                dish = candidate
                        else:
                            # kolla följande siblings
                            next_sib = sib.next_sibling
                            while next_sib and not dish:
                                next_text = ''
                                if hasattr(next_sib, 'get_text'):
                                    next_text = next_sib.get_text("\n", strip=True)
                                else:
                                    next_text = str(next_sib).strip()
                                if next_text:
                                    next_lines = [ln2.strip() for ln2 in next_text.splitlines() if ln2.strip()]
                                    if next_lines:
                                        candidate = next_lines[0]
                                        if not any(k in candidate.lower() for k in ignore_keywords):
                                            dish = candidate
                                            break
                                next_sib = next_sib.next_sibling
                    if dish:
                        dish = re.sub(r'\s+', ' ', dish).strip(' .')
                        meal_items.append((category, dish))
                    else:
                        # Om category finns men ingen rätt, lägg ändå till category som egen post
                        meal_items.append((category, ''))
                    continue

                # Om raden inte börjar med 'Dagens' men ser ut som en rätt
                if len(ln) > 5 and not any(k in ln_low for k in ignore_keywords):
                    candidate = re.sub(r'\s+', ' ', ln).strip(' .')
                    # Om tidigare 'Dagens' utan rätt finns, koppla ihop
                    if meal_items and meal_items[-1][1] == '':
                        cat = meal_items[-1][0]
                        meal_items[-1] = (cat, candidate)
                    else:
                        meal_items.append((None, candidate))

        # Normalisera och deduplicera meal_items
        seen = set()
        normalized = []
        for cat, dish in meal_items:
            dish_text = dish or ''
            key = ( (cat.lower() if cat else ''), dish_text.lower() )
            if key in seen:
                continue
            seen.add(key)

            if cat and dish_text:
                # T.ex. 'Dagens gröna: Vegokorv med potatismos'
                normalized_text = f"{cat}: {dish_text}"
            elif cat and not dish_text:
                normalized_text = f"{cat}"
            else:
                normalized_text = dish_text

            normalized.append(normalized_text)

        # Ta bort ospecificerade rätter som duplicerar specificerade ("Vegokorv..." om "Dagens gröna: Vegokorv..." finns)
        dishes_with_category = set()
        for item in normalized:
            if ':' in item:
                # ta text efter första ':' som rättsnamn
                _, right = item.split(':', 1)
                dishes_with_category.add(right.strip().lower())

        filtered = []
        for item in normalized:
            if ':' not in item:
                # ospecificerad rätt
                if item.strip().lower() in dishes_with_category:
                    continue
            filtered.append(item)

        current_day['meals'] = filtered
        days.append(current_day)

    # Rensa bort dagar utan rätter
    days = [d for d in days if d['meals']]

    # Formatera för markdown
    output = [f"# Malvas matsedel - {week}\n"]
    output.append("---\n")
    for day in days:
        output.append(f"\n## {day['day']}\n")
        for meal in day['meals']:
            output.append(f"- {meal}")
        output.append("\n---")
    return "\n".join(output)

def slugify(value: str) -> str:
    import re
    if not value:
        return 'unknown'
    s = value.lower()
    s = re.sub(r'\([^)]*\)', '', s)
    s = re.sub(r'[^a-z0-9]+', '_', s)
    s = s.strip('_')
    return s or 'unknown'

def parse_markdown_to_structured(md_text):
    """Parse markdown produced by scrape_malva_menu into structured dict.
    Returns: {'week': str, 'days': [{'day': str, 'meals': [{'category': str|null, 'dish': str}]}]}"""
    lines = [ln.rstrip() for ln in md_text.splitlines()]
    week = ''
    days = []
    current_day = None

    # Första raden innehåller titeln och veckan
    for i, ln in enumerate(lines):
        if ln.startswith('# '):
            parts = ln.split('-', 1)
            if len(parts) > 1:
                week = parts[1].strip()
            else:
                week = parts[0].replace('#', '').strip()
            break

    for ln in lines:
        ln = ln.strip()
        if ln.startswith('## '):
            if current_day:
                days.append(current_day)
            day_name = ln.replace('## ', '').strip()
            current_day = {'day': day_name, 'meals': []}
        elif ln.startswith('- '):
            entry = ln[2:].strip()
            if ': ' in entry:
                cat, dish = [s.strip() for s in entry.split(':', 1)]
            else:
                cat, dish = None, entry
            if current_day is None:
                continue
            current_day['meals'].append({'category': cat, 'dish': dish})
        else:
            continue

    if current_day:
        days.append(current_day)

    return {'week': week, 'days': days}


if __name__ == "__main__":
    url = "https://maltidsservice.uppsala.se/mat-och-menyer/gymnasieskolans-meny/"
    markdown = scrape_malva_menu(url)

    # bestäm vecka från header (vi har variabel week i funktionen, men här parsar vi från markdown)
    # linje med '# Malvas matsedel - Meny för vecka 9'
    week_slug = 'unknown_week'
    for ln in markdown.splitlines():
        if ln.startswith('# '):
            # dela på '-' och ta andra delen om finns
            parts = ln.split('-', 1)
            if len(parts) > 1:
                week_part = parts[1].strip()
            else:
                week_part = parts[0].replace('#', '').strip()
            week_slug = slugify(week_part)
            break

    school_slug = 'malva_gymnasiet'
    filename_base = f"{school_slug}_{week_slug}"

    md_filename = Path('output') / f"{filename_base}.md"
    json_filename = Path('output') / f"{filename_base}.json"

    # skapa output-mappen om den saknas
    Path('output').mkdir(parents=True, exist_ok=True)

    with open(md_filename, "w", encoding="utf-8") as f:
        f.write(markdown)
    print(f"✅ Sparat till: {md_filename}")

    structured = parse_markdown_to_structured(markdown)
    with open(json_filename, 'w', encoding='utf-8') as jf:
        json.dump(structured, jf, ensure_ascii=False, indent=2)
    print(f'✅ Sparat till: {json_filename}')
