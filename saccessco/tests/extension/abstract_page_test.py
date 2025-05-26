
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait

class AbstractPageTest(StaticLiveServerTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        chrome_options = Options()
        # chrome_options.add_argument("--headless")
        chrome_options.add_argument("--enable-speech-dispatcher")
        chrome_options.add_argument("--autoplay-policy=no-user-gesture-required")
        cls.driver = webdriver.Chrome(options=chrome_options)
        cls.driver.implicitly_wait(10)
        # Load the test page (make sure it is served correctly by Django)
        cls.driver.get(f"{cls.live_server_url}/test-page/")

        # Wait until the global object is available.
        WebDriverWait(cls.driver, 10).until(
            lambda d: d.execute_script("return window.pageManipulatorModule != null")
        )

    @classmethod
    def tearDownClass(cls):
        # sleep(20)
        cls.driver.quit()
        super().tearDownClass()
