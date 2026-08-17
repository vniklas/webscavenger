# Web Scavenger - Matlista Scraper

Detta projekt hämtar matlistan från Matilda Platform och konverterar den till ett format som är lämpligt för ChatGPT Agent Mode.

## Installation

```bash
# Installera beroenden
pip install -r requirements.txt
```

## Användning

```bash
# Kör scriptet
python scrape_menu.py
```

Detta kommer att:
1. Hämta den senaste matlistan från Adolfsbergsskolan
2. Skapa `matlista_chatgpt.md` - formaterad för ChatGPT
3. Skapa `matlista.json` - strukturerad data i JSON-format

## Anpassa URL

Redigera URL:en i `scrape_menu.py` för att hämta från en annan vecka eller skola:

```python
url = "https://menu.matildaplatform.com/meals/week/67efc167b004f87fee8f580c_adolfsbergsskolan"
```

## Använd med ChatGPT Agent Mode

1. Kör scriptet för att generera `matlista_chatgpt.md`
2. Öppna filen och kopiera innehållet
3. Klistra in i ChatGPT Agent Mode för att få hjälp med matplanering, recept, etc.
