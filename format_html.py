from pathlib import Path
from bs4 import BeautifulSoup

root = Path(__file__).resolve().parent
files = sorted(root.rglob('*.html'))
print(f'HTML_FILES {len(files)}')
for path in files:
    text = path.read_text(encoding='utf-8')
    soup = BeautifulSoup(text, 'html.parser')
    path.write_text(soup.decode(formatter='minimal'), encoding='utf-8')
print('FORMATTED')
