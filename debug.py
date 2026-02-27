#!/usr/bin/env python3
"""Debug script to see the HTML structure"""

import requests
from bs4 import BeautifulSoup

url = "https://menu.matildaplatform.com/en/meals/week/67efc392b004f87fee8fa856_alsikeskolan"

headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
}
response = requests.get(url, headers=headers)
soup = BeautifulSoup(response.content, 'html.parser')

# Spara hela HTML
with open('debug.html', 'w', encoding='utf-8') as f:
    f.write(soup.prettify())

print("HTML sparad till debug.html")

# Skriv ut alla headers
print("\n=== Alla headers ===")
for i, header in enumerate(soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])):
    print(f"{i}: {header.name} - {header.get_text(strip=True)[:80]}")
