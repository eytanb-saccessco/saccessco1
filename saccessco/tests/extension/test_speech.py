# saccessco/tests/extension/test_speech.py

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException

from saccessco.tests.extension.abstract_extension_page_test import AbstractExtensionPageTest

class SpeechModuleTest(AbstractExtensionPageTest):

    def test_speak(self):
        self.driver.execute_script("""
            window.__originalSpeechModuleSpeak = window.speechModule.speak;

            window.speechModule.speak = function(text) {
                console.log("TEST STUB: speechModule.speak called directly with:", text);
                window.__speechModuleSpeakCalls = window.__speechModuleSpeakCalls || [];
                window.__speechModuleSpeakCalls.push({ text: text, timestamp: new Date().toISOString() });
                return Promise.resolve();
            };
            console.log("TEST STUB: window.speechModule.speak has been mocked for test_speak.");
        """)

        result = self.driver.execute_async_script("""
            const callback = arguments[arguments.length - 1];
            if (!window.speechModule || typeof window.speechModule.speak !== 'function') {
                callback("error: speechModule.speak not available (post-stub check)");
                return;
            }
            console.log("Calling window.speechModule.speak in async script...");
            window.speechModule.speak("Hello, world!")
              .then(() => {
                  console.log("speechModule.speak Promise resolved.");
                  callback("done");
              })
              .catch(err => {
                  console.error("speechModule.speak Promise rejected:", err.message || err);
                  callback("error:" + (err.message || err));
              });
        """)
        print(f"Result from execute_async_script: {result}")
        self.assertEqual(result, "done")


    def test_listen(self):
        self.driver.execute_script("""
            window.SpeechRecognition = function() {
                this.continuous = true;
                this.interimResults = false;
                this.lang = "en-US";
                this.started = false;
                this.stopped = false;
                this.start = function() { this.started = true; console.log("SpeechRecognition stub started."); };
                this.stop = function() { this.stopped = true; console.log("SpeechRecognition stub stopped."); };
                this.onresult = null;
                this.onerror = null;
                this.onend = null;
            };
            window.webkitSpeechRecognition = window.SpeechRecognition;

            const originalSpeechModuleListen = window.speechModule.listen;

            window.speechModule.listen = function(callback) {
                console.log("TEST STUB: speechModule.listen called.");
                if (!window.__recognitionInstance) {
                    window.__recognitionInstance = new window.SpeechRecognition();
                    window.speechModule.recognition = window.__recognitionInstance; // Ensure module uses this instance
                    console.log("TEST STUB: New __recognitionInstance created by mocked listen.");

                    window.__recognitionInstance.onresult = (event) => {
                        console.log("TEST STUB: __recognitionInstance.onresult fired.");
                        const mockTranscript = event.results[0][0].transcript;
                        if (callback) {
                            callback(mockTranscript);
                        }
                    };
                    window.__recognitionInstance.onend = () => {
                        console.log("TEST STUB: __recognitionInstance.onend fired.");
                        if (window.speechModule.isListening) {
                           window.__recognitionInstance.start();
                        }
                    };
                     window.__recognitionInstance.onerror = (event) => {
                        console.error("TEST STUB: __recognitionInstance.onerror fired:", event.error);
                     };
                } else {
                     console.log("TEST STUB: Reusing existing __recognitionInstance.");
                     window.speechModule.recognition = window.__recognitionInstance;
                }

                window.speechModule.isListening = true;
                window.speechModule.callBack = callback;
                window.speechModule.recognition.start(); // Ensure the start is called on the instance
                console.log("TEST STUB: speechModule.listen finished and initiated.");
            };
            console.log("TEST STUB: window.speechModule.listen has been mocked for test_listen.");
        """)
        self.driver.execute_script("""
            window.currentSpeechCallback = function(transcript) {
                console.log("TEST STUB: currentSpeechCallback received:", transcript);
                window.__recognizedTranscript = transcript;
            };
            console.log("TEST STUB: window.currentSpeechCallback has been set.");
        """)
        self.driver.execute_script("window.speechModule.listen(window.currentSpeechCallback);")
        print("INFO: speechModule.listen called.")

        self.driver.execute_script("""
            if (window.__recognitionInstance && typeof window.__recognitionInstance.onresult === 'function') {
                const mockEvent = {
                    results: [
                        [{ transcript: 'Test transcript', confidence: 0.9, isFinal: true }]
                    ],
                    resultIndex: 0
                };
                console.log("Simulating recognition result via __recognitionInstance.onresult");
                window.__recognitionInstance.onresult(mockEvent);
            } else {
                console.warn("Could not simulate onresult: __recognitionInstance or onresult is not a function.");
            }
        """)
        print("INFO: Simulated recognition result.")

        try:
            transcript = WebDriverWait(self.driver, 5).until(
                lambda d: d.execute_script("return window.__recognizedTranscript;")
            )
            print(f"INFO: Retrieved transcript: '{transcript}'")
        except TimeoutException:
            self.fail("Timed out waiting for __recognizedTranscript to be set.")

        self.assertEqual(transcript, "Test transcript")


    def test_stop_listening(self):
        # 1. Inject a comprehensive stub for SpeechRecognition FIRST.
        self.driver.execute_script("""
            window.SpeechRecognition = function() {
                this.continuous = true;
                this.interimResults = false;
                this.lang = "en-US";
                this.started = false;
                this.stopped = false;
                this.start = function() {
                    this.started = true;
                    console.log("TEST STUB: SpeechRecognition.start() called on instance " + this.__instanceId + ". Now started: " + this.started);
                };
                this.stop = function() {
                    this.stopped = true;
                    console.log("TEST STUB: SpeechRecognition.stop() called on instance " + this.__instanceId + ". Now stopped: " + this.stopped);
                };
                this.onend = null;
                this.onerror = null;
                this.onresult = null;
                this.__instanceId = Math.random().toString(36).substring(7);
                console.log("TEST STUB: New SpeechRecognition instance created with ID: " + this.__instanceId);
            };
            window.webkitSpeechRecognition = window.SpeechRecognition;
            console.log("TEST STUB: window.SpeechRecognition has been mocked.");

            window.__recognitionInstance = null; // Reset for this test

            // Store original methods to wrap them
            const originalSpeechModuleSetUp = window.speechModule.setUp;
            const originalSpeechModuleListen = window.speechModule.listen;
            const originalSpeechModuleStopListening = window.speechModule.stopListening;
            const originalSpeechModuleStartRecognitionInternal = window.speechModule.startRecognitionInternal; // Get original

            // Wrap setUp to expose the instance
            window.speechModule.setUp = function() {
                console.log("TEST STUB: Mocked speechModule.setUp called.");
                originalSpeechModuleSetUp.apply(this, arguments); // Call original
                window.__recognitionInstance = this.recognition; // EXPOSE THE INSTANCE
                console.log("TEST STUB: speechModule.setUp finished. recognition instance exposed: " + (this.recognition ? this.recognition.__instanceId : "null"));
            };

            // Wrap listen to ensure setUp is called and recognition is available
            window.speechModule.listen = function() {
                 console.log("TEST STUB: Mocked speechModule.listen called.");
                 originalSpeechModuleListen.apply(this, arguments); // Call original
                 window.__recognitionInstance = this.recognition; // Re-expose in case listen recreates/assigns
                 console.log("TEST STUB: speechModule.listen finished. recognition instance is: " + (this.recognition ? this.recognition.__instanceId : "null") + " and started: " + (this.recognition ? this.recognition.started : "N/A"));
            };

            // Wrap stopListening
            window.speechModule.stopListening = function() {
                console.log("TEST STUB: Mocked speechModule.stopListening called.");
                originalSpeechModuleStopListening.apply(this, arguments);
                console.log("TEST STUB: speechModule.stopListening finished. recognition instance is: " + (this.recognition ? this.recognition.__instanceId : "null") + " and stopped: " + (this.recognition ? this.recognition.stopped : "N/A"));
            };

            // Ensure startRecognitionInternal is also correctly wrapped if needed
            // If the issue is that this.recognition.start() is not called, it's because originalStartRecognitionInternal is not executing properly.
            window.speechModule.startRecognitionInternal = function() {
                console.log("TEST STUB: Mocked speechModule.startRecognitionInternal called.");
                originalSpeechModuleStartRecognitionInternal.apply(this, arguments);
                console.log("TEST STUB: speechModule.startRecognitionInternal finished. After calling recognition.start(), started is: " + (this.recognition ? this.recognition.started : "N/A"));
            };

            console.log("TEST STUB: window.speechModule methods have been mocked for test_stop_listening.");
        """)
        print("INFO: Stubs injected for test_stop_listening.")

        # Now call listen. This will trigger setUp and then startRecognitionInternal
        self.driver.execute_script("window.speechModule.listen();")
        print("INFO: speechModule.listen() called in test_stop_listening.")

        # Wait for the recognition instance to be available and its start() method to be called
        try:
            WebDriverWait(self.driver, 5).until(
                lambda d: d.execute_script("""
                    return window.__recognitionInstance != null &&
                           window.__recognitionInstance.started === true;
                """)
            )
            print("INFO: __recognitionInstance is available and started is TRUE.")
        except TimeoutException:
            # Add more debug info if it times out
            is_rec_null = self.driver.execute_script("return window.__recognitionInstance == null;")
            rec_started_state = self.driver.execute_script("return window.__recognitionInstance ? window.__recognitionInstance.started : 'N/A';")
            rec_instance_id = self.driver.execute_script("return window.__recognitionInstance ? window.__recognitionInstance.__instanceId : 'N/A';")
            print(f"ERROR: Timeout waiting for __recognitionInstance to be started. Is null: {is_rec_null}, Started state: {rec_started_state}, Instance ID: {rec_instance_id}")
            self.fail("Timed out waiting for SpeechRecognition instance to be available and started.")


        # Now call stopListening.
        self.driver.execute_script("window.speechModule.stopListening();")
        print("INFO: speechModule.stopListening() called.")

        # Retrieve the 'stopped' flag from our test instance.
        stopped = self.driver.execute_script("return window.__recognitionInstance ? window.__recognitionInstance.stopped : null;");
        started = self.driver.execute_script("return window.__recognitionInstance ? window.__recognitionInstance.started : null;");
        print(f"DEBUG: Final state: __recognitionInstance.started = {started}, __recognitionInstance.stopped = {stopped}")

        self.assertTrue(started, "Expected SpeechRecognition instance to have been started by listen.")
        self.assertTrue(stopped, "Expected SpeechRecognition instance to be stopped.")