from playwright.sync_api import sync_playwright

URL = "https://cernyrytir.cz/index.php3?akce=3"

username = "chinchila"
password = "veronique"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    page.goto(URL)
    page.fill('input[name="uzivjmeno"]', username)
    page.fill('input[name="uzivheslo"]', password)
    page.wait_for_selector('input[type="image"][alt="Přihlášení"]')
    page.click('input[type="image"][alt="Přihlášení"]')
    page.goto(URL)

    page.type('input[name="jmenokarty"]', "Incinerator of the Guilty - foil")
    page.press('input[name="jmenokarty"]', 'Enter')
    page.wait_for_load_state("domcontentloaded")    

    form = page.query_selector('form[name="objednejkusovku156219"]')
    input_element = form.query_selector('input[type="image"][alt="Vložit do košíku"]')
    input_element.click()

    input("Press Enter to close the browser...")
    browser.close()
