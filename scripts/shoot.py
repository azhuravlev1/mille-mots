"""Screenshot sections of index.html in both modes (dev helper).

usage: shoot.py [print|learn] section[:offset_px] ...
"""
import os
import sys

from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
url = 'file://' + os.path.join(ROOT, 'index.html')
mode = sys.argv[1]
targets = sys.argv[2:]
os.makedirs(os.path.join(ROOT, 'shots'), exist_ok=True)

with sync_playwright() as p:
    b = p.chromium.launch(channel='chrome')
    phone = os.environ.get('PHONE')
    if phone:
        page = b.new_page(viewport={'width': 390, 'height': 844}, device_scale_factor=2,
                          is_mobile=True, has_touch=True)
    else:
        page = b.new_page(viewport={'width': 1300 if mode == 'learn' else 900, 'height': 1100},
                          device_scale_factor=2)
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.on('console', lambda m: m.type == 'error' and errors.append(m.text))
    page.goto(url)
    page.evaluate("localStorage.clear()")
    page.reload()
    if mode == 'learn':
        page.click('#modeSwitch button[data-mode=learn]')
        page.wait_for_timeout(500)
    for t in targets:
        sec, _, off = t.partition(':')
        page.evaluate(f"window.scrollTo({{top: document.getElementById('{sec}').getBoundingClientRect().top"
                      f" + window.scrollY + {int(off or 0)} - 60, behavior: 'instant'}})")
        page.wait_for_timeout(250)
        prefix = 'phone_' if phone else ''
        page.screenshot(path=os.path.join(ROOT, 'shots', f'{prefix}{mode}_{sec}_{off or 0}.png'))
    print('errors:', errors)
    b.close()
