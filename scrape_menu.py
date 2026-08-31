#!/usr/bin/env python3
"""
Web scraper för att hämta matlista från Matilda Platform
och formatera den för ChatGPT Agent Mode
"""

import re
import requests
import json
from datetime import datetime, timedelta, timezone
from collections import defaultdict

API_BASE = "https://menu.matildaplatform.com/api/menu"


def extract_distributor_id(url):
    """Extraherar distributorId från en meals/week-URL, t.ex.
    '.../meals/week/67efc167b004f87fee8f580c_adolfsbergsskolan' -> '67efc167b004f87fee8f580c'

    OBS: Matilda Platform renderar inte längre matsedeln i sidans HTML
    (__NEXT_DATA__). Sidan gör istället ett eget anrop till /api/menu i
    webbläsaren efter sidladdning, så vi anropar samma API direkt.
    """
    m = re.search(r'week/([0-9a-fA-F]+)_', url)
    if not m:
        raise ValueError(f"Kunde inte hitta distributorId i URL: {url}")
    return m.group(1)


def current_week_dates(today=None):
    """Returnerar (startDate, endDate) som ISO-datumsträngar (YYYY-MM-DD)
    för innevarande ISO-vecka (måndag till söndag)."""
    today = today or datetime.now(timezone.utc).date()
    monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)
    return monday.isoformat(), sunday.isoformat()


def scrape_menu(url, start_date=None, end_date=None):
    """Hämtar och parsar matsedeln från Matilda Platforms /api/menu-endpoint"""

    distributor_id = extract_distributor_id(url)
    if not start_date or not end_date:
        start_date, end_date = current_week_dates()

    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    }
    params = {
        'distributorId': distributor_id,
        'startDate': start_date,
        'endDate': end_date,
        'lang': 'sv',
    }
    response = requests.get(API_BASE, headers=headers, params=params)
    response.raise_for_status()

    data = response.json()

    # Extrahera skolinfo
    distributor = data.get('distributor', {})
    school_name = distributor.get('name', 'Adolfsbergsskolan')
    organization = distributor.get('organization', '')
    if organization:
        school_name = f"{school_name} ({organization})"

    message = distributor.get('messageForCustomers', '')

    # Extrahera måltider
    meals_list = data.get('meals', [])

    # Gruppera måltider per dag (använd datum som nyckel för kronologisk sortering)
    days_by_date = {}
    for meal in meals_list:
        date = meal.get('date', '')
        meal_name = meal.get('name', '')
        courses = meal.get('courses', [])

        if date and courses:
            # Formatera datum
            date_obj = datetime.fromisoformat(date.replace('Z', '+00:00'))
            date_key = date_obj.date()
            day_str = date_obj.strftime('%A %d %b').upper()

            # Extrahera rättnamn
            dishes = []
            for course in courses:
                dish_name = course.get('name', '')
                if dish_name and dish_name not in ['Mellanmål', 'Frukost', 'Snack', 'Breakfast']:
                    dishes.append(dish_name)

            if dishes or meal_name in ['Mellanmål', 'Frukost']:
                if date_key not in days_by_date:
                    days_by_date[date_key] = {'day': day_str, 'meals': []}
                days_by_date[date_key]['meals'].append({
                    'category': meal_name,
                    'dishes': dishes if dishes else [meal_name]
                })

    # Sortera dagar kronologiskt och bygg strukturen
    sorted_days = []
    for date_key in sorted(days_by_date.keys()):
        entry = days_by_date[date_key]
        sorted_days.append({
            'day': entry['day'],
            'meals': {m['category']: ', '.join(m['dishes']) for m in entry['meals']}
        })
    
    menu_data = {
        'school': school_name,
        'message': message,
        'weeks': [sorted_days] if sorted_days else [],
        'start_date': start_date,
        'end_date': end_date
    }
    
    return menu_data


def format_for_chatgpt(menu_data):
    """Formaterar matsedeln för ChatGPT Agent Mode"""
    
    output = []
    output.append(f"# Matlista för {menu_data['school']}\n")
    
    if menu_data.get('message'):
        output.append(f"*{menu_data['message']}*\n")
    
    output.append("---\n")
    
    for week in menu_data['weeks']:
        for day_info in week:
            day = day_info['day']
            meals = day_info['meals']
            
            output.append(f"\n## {day}\n")
            
            for meal_type, meal_content in meals.items():
                output.append(f"**{meal_type}:** {meal_content}\n")
            
            output.append("---")
    
    return "\n".join(output)


def format_as_json(menu_data):
    """Formaterar matsedeln som JSON"""
    return json.dumps(menu_data, indent=2, ensure_ascii=False)


def slugify(value: str) -> str:
    """Simple slugify: lowercase, replace non-alnum with underscore"""
    import re
    if not value:
        return 'unknown'
    s = value.lower()
    s = re.sub(r'\([^)]*\)', '', s)  # remove parenthesis content
    s = re.sub(r'[^a-z0-9]+', '_', s)
    s = s.strip('_')
    return s or 'unknown'


def main():
    url = "https://menu.matildaplatform.com/meals/week/67efc167b004f87fee8f580c_adolfsbergsskolan"

    print("Hämtar matlista...")
    menu_data = scrape_menu(url)

    # Bestäm filnamn baserat på school slug och vecka (ISO-week om möjligt)
    school_slug = slugify(menu_data.get('school', 'alsikeskolan'))
    start = menu_data.get('start_date')
    end = menu_data.get('end_date')

    week_slug = 'unknown_week'
    try:
        if start:
            # Försök använda start_date för att räkna ut ISO-week
            from datetime import date
            sd = datetime.fromisoformat(start).date()
            iso_year, iso_week, _ = sd.isocalendar()
            week_slug = f"vecka_{iso_week}_{iso_year}"
        elif end:
            ed = datetime.fromisoformat(end).date()
            iso_year, iso_week, _ = ed.isocalendar()
            week_slug = f"vecka_{iso_week}_{iso_year}"
        else:
            # fallback: använd första dag från data om tillgänglig
            first_day_str = menu_data['weeks'][0][0]['day']
            # Försök extrahera datum från strängen (t.ex. 'MONDAY 23 FEB')
            import re
            m = re.search(r"(\d{1,2})\s+([A-Z]{3})", first_day_str)
            if m:
                day = int(m.group(1))
                month_abbr = m.group(2).title()
                # bygga ett datum med antagande om år (nuvarande år)
                import calendar
                import locale
                from datetime import datetime as _dt
                year_now = _dt.utcnow().year
                try:
                    # försök tolka månadsabbrev på engelska
                    month_num = _dt.strptime(month_abbr, '%b').month
                    sd = date(year_now, month_num, day)
                    iso_year, iso_week, _ = sd.isocalendar()
                    week_slug = f"vecka_{iso_week}_{iso_year}"
                except Exception:
                    week_slug = 'unknown_week'
    except Exception:
        week_slug = 'unknown_week'

    filename_base = f"{school_slug}_{week_slug}"

    # se till att output-mappen finns
    import os
    from pathlib import Path
    out_dir = Path('output')
    out_dir.mkdir(parents=True, exist_ok=True)

    # Spara i olika format
    print("\n=== MARKDOWN FORMAT (för ChatGPT) ===\n")
    markdown_output = format_for_chatgpt(menu_data)
    print(markdown_output)

    md_filename = out_dir / f"{filename_base}.md"
    json_filename = out_dir / f"{filename_base}.json"

    # Spara till fil
    with open(md_filename, 'w', encoding='utf-8') as f:
        f.write(markdown_output)
    print(f"\n✅ Sparat till: {md_filename}")

    # Spara även som JSON
    with open(json_filename, 'w', encoding='utf-8') as f:
        f.write(format_as_json(menu_data))
    print(f"✅ Sparat till: {json_filename}")


if __name__ == "__main__":
    main()
