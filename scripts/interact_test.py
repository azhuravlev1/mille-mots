"""Smoke-test Learn-mode interactions (dev helper)."""
import os

from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
url = 'file://' + os.path.join(ROOT, 'index.html')

with sync_playwright() as p:
    b = p.chromium.launch(channel='chrome')
    page = b.new_page(viewport={'width': 1300, 'height': 1000}, device_scale_factor=2)
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.goto(url)
    page.evaluate('localStorage.clear()')
    page.reload()
    visible = lambda: page.evaluate("document.querySelectorAll('.entry:not(.hidden)').length")  # noqa: E731
    print('print mode entries:', visible())
    page.click('#modeSwitch button[data-mode=learn]')
    page.wait_for_timeout(400)
    print('slider transform:', page.evaluate("getComputedStyle(document.querySelector('.mode-slider')).transform"))
    page.fill('#search', 'wait')
    page.wait_for_timeout(300)
    print('search "wait":', visible(), page.evaluate("[...document.querySelectorAll('.entry:not(.hidden) .fw')].map(e=>e.textContent).slice(0,8)"))
    page.fill('#search', '')
    page.wait_for_timeout(300)
    page.evaluate("document.getElementById('verb').scrollIntoView({behavior:'instant'})")
    item = page.locator('#verb .legend-item').first
    print('legend item:', item.text_content()[:60])
    item.click()
    page.wait_for_timeout(300)
    print('after pattern filter:', visible(), '| highlighted:', page.evaluate("document.querySelectorAll('.hp').length"))
    page.screenshot(path=os.path.join(ROOT, 'shots', 'learn_filter.png'))
    page.click('#filterPill')
    page.wait_for_timeout(300)
    print('after clearing filter:', visible())
    page.check('#quiz')
    page.evaluate("document.getElementById('adj').scrollIntoView({behavior:'instant'})")
    page.wait_for_timeout(200)
    page.locator('#adj .entry').nth(1).click()
    page.screenshot(path=os.path.join(ROOT, 'shots', 'learn_quiz.png'))
    page.uncheck('#quiz')
    page.locator('#noun .known-btn').first.click()
    page.check('#hideKnown')
    page.wait_for_timeout(200)
    print('after marking 1 known + hide:', visible(), page.text_content('#knownCount'))
    page.select_option('select[data-groupby=verb]', 'type')
    page.wait_for_timeout(300)
    print('verb groups by type:', page.evaluate("[...document.querySelectorAll('#verb .group-head h3')].map(h=>h.textContent+' '+h.parentNode.querySelector('.gcount').textContent)"))
    page.screenshot(path=os.path.join(ROOT, 'shots', 'learn_vtype.png'))
    print('errors:', errors)
    b.close()
