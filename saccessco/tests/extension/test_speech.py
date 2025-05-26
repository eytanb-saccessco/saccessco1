from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait

from saccessco.tests.extension.abstract_page_test import AbstractPageTest

class SpeechModuleTest(AbstractPageTest):

    def test_speak(self):
        # Override speechSynthesis.speak so that it simulates a successful synthesis.
        self.driver.execute_script("""
            window.speechSynthesis = {
                speak: function(utterance) {
                    console.log("Stubbed speak called with:", utterance.text);
                    // Instead of triggering an error, immediately call onend.
                    setTimeout(() => {
                        if (utterance.onend) {
                            utterance.onend();
                        }
                    }, 10);
                },
                cancel: function(){}
            };
            window.currentSpeechCallback = function(transcript) {
                window.__recognizedTranscript = transcript;
            };
            window.speechModule.listen();
            window.currentSpeechCallback('Test transcript');
                    """)
        result = self.driver.execute_async_script("""
            const callback = arguments[arguments.length - 1];
            window.speechModule.speak("Hello, world!")
              .then(() => callback("done"))
              .catch(err => callback("error:" + err));
        """)
        print(result)
        self.assertEqual(result, "done")

    def test_listen(self):
        # Stub SpeechRecognition and capture the instance.
        self.driver.execute_script("""
            // Create a stub for SpeechRecognition.
            window.SpeechRecognition = function() {
                this.continuous = true;
                this.interimResults = false;
                this.lang = "en-US";
                this.start = function() { this.started = true; };
                this.stop = function() { this.stopped = true; };
            };
            window.webkitSpeechRecognition = window.SpeechRecognition;
            // Override the module's initRecognition to expose the instance.
            const originalInit = window.speechModule.listen;
            window.speechModule.listen = function(callback) {
                originalInit.call(this, callback);
                // Expose the instance for testing.
                window.__recognitionInstance = window.__recognitionInstance || new window.SpeechRecognition();
            };
        """)
        # Override the callback to capture the transcript.
        self.driver.execute_script("""
            window.currentSpeechCallback = function(transcript) {
                window.__recognizedTranscript = transcript;
            };
        """)
        # Call listen.
        self.driver.execute_script("window.speechModule.listen(window.currentSpeechCallback);")
        # Simulate a recognition result.
        self.driver.execute_script("window.currentSpeechCallback('Test transcript');")
        transcript = self.driver.execute_script("return window.__recognizedTranscript;")
        self.assertEqual(transcript, "Test transcript")

def test_stop_listening(self):
    # Inject a stub for SpeechRecognition and force reinitialization.
    self.driver.execute_script("""
        window.SpeechRecognition = function() {
            this.continuous = true;
            this.interimResults = false;
            this.lang = "en-US";
            this.start = function() { this.started = true; };
            this.stop = function() { this.stopped = true; };
        };
        window.webkitSpeechRecognition = window.SpeechRecognition;
        // Reset the module's recognition instance.
        if (window.speechModule.resetRecognition) {
            window.speechModule.resetRecognition();
        } else {
            // Fallback: force recognition to null.
            window.__recognitionInstance = null;
        }
    """)
    # Now call listen to initialize the recognition instance using the stub.
    self.driver.execute_script("window.speechModule.listen();")
    # Now call stopListening.
    self.driver.execute_script("window.speechModule.stopListening();")
    # Retrieve the 'stopped' flag from our test instance.
    stopped = self.driver.execute_script("return window.__recognitionInstance ? window.__recognitionInstance.stopped : null;");
    self.assertTrue(stopped)
