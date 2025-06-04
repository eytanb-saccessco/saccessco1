# saccessco/tests/extension/abstract_extension_page_test.py
import os
from django.conf import settings
# from channels.testing import ChannelsLiveServerTestCase # This is the correct base class
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException
from django.db import connections, DEFAULT_DB_ALIAS # Needed for internal checks by ChannelsLiveServerTestCase
from django.urls import reverse
from saccessco.tests.extension.custom_channels_live_server_test_case import CustomChannelsLiveServerTestCase


class AbstractExtensionPageTest(CustomChannelsLiveServerTestCase):
    URL_NAME = 'test_page'
    """
    Base class for Selenium-driven extension tests requiring a live server
    and WebSocket capabilities provided by ChannelsLiveServerTestCase.
    Contains all browser-specific setup and teardown.
    """
    # ChannelsLiveServerTestCase handles setUpClass and tearDownClass automatically.
    # DO NOT define your own setUpClass or tearDownClass here unless you have
    # very specific class-level Selenium setup that correctly calls super().

    JS_FILES = [
        os.path.join(settings.BASE_DIR, 'static', 'js', 'chrome_extension', 'configuration.js'),
        os.path.join(settings.BASE_DIR, 'static', 'js', 'chrome_extension', 'speech.js'),
        os.path.join(settings.BASE_DIR, 'static', 'js', 'chrome_extension', 'websocket.js'),
        os.path.join(settings.BASE_DIR, 'static', 'js', 'chrome_extension', 'backend_communicator.js'),
        os.path.join(settings.BASE_DIR, 'static', 'js', 'chrome_extension', 'page_change_observer.js'),
        os.path.join(settings.BASE_DIR, 'static', 'js', 'chrome_extension', 'chat_module.js'),
        # os.path.join(settings.BASE_DIR, 'static', 'js', 'chrome_extension', 'page_manipulator.js'),
        os.path.join(settings.BASE_DIR, 'static', 'js', 'chrome_extension', 'content.js'),
        # Add any other core JS files your modules depend on
    ]

    def setUp(self):
        super().setUp() # This is crucial: it calls ChannelsLiveServerTestCase's setUp,
                        # which in turn handles the live server setup and _pre_setup logic.

        self.chrome_options = Options()
        # self.chrome_options.add_argument("--headless") # Consider enabling for CI/headless environments
        self.chrome_options.add_argument("--no-sandbox")
        self.chrome_options.add_argument("--disable-dev-shm-usage")
        self.chrome_options.add_argument("--window-size=1920,1080")
        self.chrome_options.add_argument("--autoplay-policy=no-user-gesture-required")
        # Disable infobars (like "Chrome is being controlled by automated test software")
        self.chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        self.chrome_options.add_experimental_option('useAutomationExtension', False)
        # self.chrome_options.set_capability("loggingPrefs", {"browser": "ALL", "performance": "ALL"})  # Capture all browser logs
        self.chrome_options.set_capability("goog:loggingPrefs", {"browser": "ALL", "performance": "ALL"})
        self.driver = webdriver.Chrome(options=self.chrome_options)
        self.driver.implicitly_wait(5) # Set a sensible implicit wait

        # Navigate to the test page using the live server URL
        self._load_url()

        # Inject your application's JavaScript files and mocks
        self._inject_initial_browser_mocks()
        self._inject_app_js_files()

        self.driver.execute_script("""
            // This is just a test to see if ANY console.log works after injection
            console.log('--- TEST: Direct console.log after websocket.js injection ---');
            // Your other setup like initializing window.websocket.initializeAIWebSocket()
        """)


        self._set_app_globals()

        # # Wait for key JS modules to be available before proceeding
        # try:
        #     WebDriverWait(self.driver, 10).until(
        #         lambda d: d.execute_script("return window.speechModule != null && window.websocket != null")
        #     )
        #     print("INFO: window.speechModule and window.websocket are available.")
        # except TimeoutException:
        #     self.fail("Timed out waiting for required JavaScript modules to be available.")

    def tearDown(self):
        """
        Quits the Selenium driver and calls the parent's tearDown.
        """
        print("\n--- PERFORMANCE LOGS (Network Activity) ---")
        try:
            for entry in self.driver.get_log("performance"):
                # Filter for WebSocket-related entries
                if 'WebSocket' in entry['message'] or 'network.webSocketFrame' in entry['message']:
                    print(entry)
        except Exception as e:
            print(f"Error retrieving performance logs: {e}")
        print("------------------------------------------")
        if self.driver:
            self.driver.quit()
        super().tearDown() # This is crucial: calls ChannelsLiveServerTestCase's tearDown

    # --- Your existing helper methods (copy them from your old abstract_page_test.py) ---

    def _load_url(self):
        self.driver.get(f"{self.live_server_url}{reverse(self.URL_NAME)}")

    def _inject_initial_browser_mocks(self):
        """Injects mocks for browser APIs like SpeechRecognition/SpeechSynthesis."""
        self.driver.execute_script("""
            // Mock SpeechRecognition and webkitSpeechRecognition
            window.SpeechRecognition = function() {
                this.continuous = true;
                this.interimResults = false;
                this.lang = "en-US";
                this.started = false; // Initialize state
                this.stopped = false; // Initialize state
                this.start = function() {
                    this.started = true;
                    console.log("BASE MOCK: SpeechRecognition.start() called on instance " + this.__instanceId + ". Now started: " + this.started);
                };
                this.stop = function() {
                    this.stopped = true;
                    console.log("BASE MOCK: SpeechRecognition.stop() called on instance " + this.__instanceId + ". Now stopped: " + this.stopped);
                };
                this.onend = null;
                this.onerror = null;
                this.onresult = null;
                this.__instanceId = "base-mock-" + Math.random().toString(36).substring(7);
                console.log("BASE MOCK: New SpeechRecognition instance created with ID: " + this.__instanceId);
            };
            window.webkitSpeechRecognition = window.SpeechRecognition;
            console.log("BASE MOCK: window.SpeechRecognition has been pre-mocked.");

            // Mock SpeechSynthesis (for completeness, though test_speak overrides it)
            window.speechSynthesis = window.speechSynthesis || {
                speak: function(utterance) {
                    console.log("BASE MOCK: speechSynthesis.speak called with:", utterance.text);
                    // Ensure onend is called to resolve promises in speechModule.speak
                    setTimeout(() => {
                        if (utterance.onend) {
                            utterance.onend();
                        }
                    }, 10);
                },
                cancel: function() { console.log("BASE MOCK: speechSynthesis.cancel called."); },
                speaking: false,
                paused: false,
                pending: false
            };
            console.log("BASE MOCK: window.speechSynthesis has been pre-mocked.");
        """)
        print("INFO: Injected initial browser API mocks.")

    def _inject_app_js_files(self, pre_scripts=None):
        if pre_scripts:
            for script in pre_scripts:
                self.driver.execute_script(script)
        """Injects application-specific JavaScript files."""
        print(f"--DEBUG--: _inject_app_js_files called")
        for js_file_path in self.JS_FILES:
            try:
                with open(js_file_path, 'r') as f:
                    js_code = f.read()
                self.driver.execute_script(js_code)
                print(f"INFO: Injected {os.path.basename(js_file_path)} into the page.")
            except FileNotFoundError:
                self.fail(f"ERROR: JS file not found, check path: {js_file_path}")
            except Exception as e:
                self.fail(f"ERROR: Failed to inject {os.path.basename(js_file_path)}: {e}")


    def _set_app_globals(self):
        """Sets global configuration and stubs for application modules."""
        self.conversation_id = "test_conv_selenium_dynamic"
        websocket_url_base = f"ws://{self.live_server_url.split('://')[1]}/ws/saccessco/ai"
        backend_page_change_url = f"http://{self.live_server_url.split('://')[1]}/saccessco/page_change/"
        backend_user_prompt_url = f"http://{self.live_server_url.split('://')[1]}/saccessco/user_prompt/"

        self.driver.execute_script(f"""
            window.configuration = window.configuration || {{}};
            window.configuration.SACCESSCO_WEBSOCKET_URL = "{websocket_url_base}";
            window.configuration.SACCESSCO_USER_PROMPT_URL = "{backend_user_prompt_url}";
            window.configuration.SACCESSCO_PAGE_CHANGE_URL = "{backend_page_change_url}";
            window.conversation_id = "{self.conversation_id}";

            window.speechModule = window.speechModule || {{
                speak: function(text) {{
                    console.log("GLOBAL STUB: speechModule.speak called with:", text);
                    window.__speechModuleSpeakCalls = window.__speechModuleSpeakCalls || [];
                    window.__speechModuleSpeakCalls.push({{ text: text, timestamp: new Date().toISOString() }});
                    return Promise.resolve();
                }},
                listen: function() {{ console.log("GLOBAL STUB: speechModule.listen called."); }},
                stopListening: function() {{ console.log("GLOBAL STUB: speechModule.stopListening called."); }},
                resetRecognition: function() {{ console.log("GLOBAL STUB: speechModule.resetRecognition called."); }}
            }};
            window.__speechModuleSpeakCalls = []; // Initialize for assertion

            window.pageManipulatorModule = window.pageManipulatorModule || {{
                executePlan: function(plan) {{
                    console.log("GLOBAL STUB: pageManipulatorModule.executePlan called:", plan);
                    window.__pageManipulatorExecuteCalls = window.__pageManipulatorExecuteCalls || [];
                    window.__pageManipulatorExecuteCalls.push(plan);
                }}
            }};
            window.__pageManipulatorExecuteCalls = [];

            window.chatModule = window.chatModule || {{
                addMessage: function(sender, message) {{
                    console.log("GLOBAL STUB: chatModule.addMessage:", sender, message);
                    window.__chatModuleMessages = window.__chatModuleMessages || [];
                    window.__chatModuleMessages.push({{ sender: sender, message: message }});
                }}
            }};
            window.backendCommunicatorModule = window.backendCommunicatorModule || {{
                sendUserPrompt: function(prompt) {{
                    console.log("GLOBAL STUB: backendCommunicatorModule.sendUserPrompt:", prompt);
                    window.__backendCommunicatorPrompts = window.__backendCommunicatorPrompts || [];
                    window.__backendCommunicatorPrompts.push(prompt);
                }}
            }};
            console.log("INFO: Configured global variables and stubbed dependent modules.");
        """)
        print("INFO: Configured global variables and stubbed dependent modules.")

    def _get_browser_console_logs(self):
        """
        Retrieves and prints browser console logs since the last retrieval.
        Filters for specific debug messages or prints all.
        """
        try:
            # 'browser' is the log type for console messages
            logs = self.driver.get_log('browser')

            if logs:
                print("\n--- BROWSER LOGS (console.log(...) ---")
                print("----------------------------------------")
                for entry in logs:
                    # Each entry is a dictionary like {'level': 'INFO', 'message': '...', 'timestamp': ...}
                    # You can filter for your specific messages, e.g., messages containing "--DEBUG--"
                    # if "--DEBUG--" in entry['message'] or entry['level'] == 'SEVERE':
                    #     print(f"[{entry['level']}] {entry['message']}")
                    # # Optionally, uncomment the line below to see all INFO, WARNING, etc. messages
                    # else:
                    print(f"[{entry['level']}] {entry['message']}")
                print("=====================================================")
            # Return logs if you need to perform assertions on them
            return logs
        except Exception as e:
            print(f"WARNING: Could not retrieve browser console logs: {e}")
            return []

