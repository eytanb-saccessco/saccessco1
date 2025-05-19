from selenium import webdriver
from selenium.webdriver.chrome.options import Options

def get_rendered_html(url):
    options = Options()
    options.headless = True
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1280,720')
    options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:110.0) Gecko/20100101 Firefox/110.0")
    driver = webdriver.Chrome(options=options)
    driver.get(url)
    rendered_html = driver.execute_script("return document.documentElement.outerHTML;")
    return rendered_html