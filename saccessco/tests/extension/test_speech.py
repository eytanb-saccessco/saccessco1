# saccessco/tests/extension/test_speech.py

import time
import json
import logging
from threading import Thread

from django.urls import reverse
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from django.conf import settings

from saccessco.tests.extension.abstract_extension_page_test import AbstractExtensionPageTest

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Define paths to the JavaScript files
CHAT_MODULE_JS_PATH = settings.BASE_DIR / 'static' / 'js' / 'chrome_extension' / 'chat_module.js'
PAGE_MANIPULATOR_JS_PATH = settings.BASE_DIR / 'static' / 'js' / 'chrome_extension' / 'page_manipulator.js'
SPEECH_JS_PATH = settings.BASE_DIR / 'static' / 'js' / 'chrome_extension' / 'speech.js'


class SpeechModuleTest(AbstractExtensionPageTest):
    JS_FILES = []  # Prevent AbstractExtensionPageTest from auto-injecting its default JS_FILES

    def setUp(self):
        super().setUp()
        # Set a reasonable script timeout for execute_async_script.
        # This is the maximum time Selenium will wait for the JavaScript callback to be invoked.
        self.driver.set_script_timeout(10)  # Set timeout to 10 seconds
        print("INFO: Selenium script timeout set to 10 seconds.")

        # Navigate to a simple test page. This clears previous JS context.
        # This must happen before any mocks are injected to ensure a clean browser state.
        self.driver.get(self.live_server_url + reverse('test_page_manipulator'))

        # CRITICAL: Inject ALL global browser API mocks *immediately* after loading the page
        # and *before* injecting any actual application JavaScript files. This ensures
        # the application code sees the mocks from the very beginning and binds to them.
        self.driver.execute_script("""
            // Aggressively delete native APIs to ensure our mocks are used
            if (window.speechSynthesis) {
                delete window.speechSynthesis;
                console.log('TEST STUB: Deleted native window.speechSynthesis.');
            }
            if (window.SpeechSynthesisUtterance) {
                delete window.SpeechSynthesisUtterance;
                console.log('TEST STUB: Deleted native window.SpeechSynthesisUtterance.');
            }
            if (window.SpeechRecognition) {
                delete window.SpeechRecognition;
                console.log('TEST STUB: Deleted native window.SpeechRecognition.');
            }
            if (window.webkitSpeechRecognition) {
                delete window.webkitSpeechRecognition;
                console.log('TEST STUB: Deleted native window.webkitSpeechRecognition.');
            }

            // Add a dummy mic button to the DOM to prevent 'appendChild' errors
            var micButton = document.createElement('button');
            micButton.id = 'floating-mic-button';
            document.body.appendChild(micButton);
            console.log('TEST STUB: Added floating-mic-button to DOM.');

            // Mock SpeechRecognition API
            window.SpeechRecognition = function() {
                this.continuous = true;
                this.interimResults = true;
                this.maxAlternatives = 1;
                this.lang = 'en-US';
                this.started = false;
                this.stopped = false;
                this.start = function() {
                    this.started = true;
                    this.stopped = false;
                    console.log('TEST STUB: SpeechRecognition.start() called on instance ' + this.__instanceId + '. Now started: ' + this.started);
                    if (this.onstart) this.onstart();
                };
                this.stop = function() {
                    this.stopped = true;
                    this.started = false;
                    console.log('TEST STUB: SpeechRecognition.stop() called on instance ' + this.__instanceId + '. Now stopped: ' + this.stopped);
                    if (this.onend) this.onend();
                };
                this.onresult = null;
                this.onerror = null;
                this.onend = null;
                this.onstart = null;
                this.__instanceId = Math.random().toString(36).substring(7);
                console.log('TEST STUB: New SpeechRecognition instance created with ID: ' + this.__instanceId);
            };
            window.webkitSpeechRecognition = window.SpeechRecognition; // Ensure webkit version is also mocked
            console.log('TEST STUB: window.SpeechRecognition has been mocked.');

            // Mock SpeechSynthesisUtterance to control its behavior
            window.SpeechSynthesisUtterance = function(text) {
                this.text = text;
                this.onend = null;
                this.onerror = null;
                console.log('TEST STUB: New SpeechSynthesisUtterance instance created for text: ' + text);
            };
            console.log('TEST STUB: window.SpeechSynthesisUtterance has been mocked.');

            // Mock speechSynthesis API
            window.speechSynthesis = {
                speak: function(utterance) {
                    console.log('TEST STUB: speechSynthesis.speak called with: ' + utterance.text);
                    window.__speechSynthesisSpeakCalls = window.__speechSynthesisSpeakCalls || [];
                    window.__speechSynthesisSpeakCalls.push(utterance.text);

                    if (typeof utterance.onend === 'function') {
                        console.log('TEST STUB: Calling utterance.onend() synchronously from speechSynthesis.speak mock.');
                        utterance.onend(); // Synchronous call to resolve promise in speech.js
                    } else {
                        console.error('TEST STUB: utterance.onend is NOT a function in speechSynthesis.speak mock. Type: ' + typeof utterance.onend + '. Explicitly rejecting speak promise.');
                        if (typeof utterance.onerror === 'function') {
                            utterance.onerror({ error: 'synthesis-failed-onend-missing' });
                        } else {
                            console.error('TEST STUB: Neither onend nor onerror is a function on utterance. Cannot resolve/reject speak promise.');
                        }
                    }
                },
                cancel: function() { console.log('TEST STUB: speechSynthesis.cancel called.'); },
                getVoices: function() { return []; },
                speaking: false,
                pending: false,
                paused: false
            };
            console.log('TEST STUB: window.speechSynthesis has been mocked.');

            // Mock chatModule.addMessage for testing purposes
            window.chatModule = window.chatModule || {};
            window.chatModule.addMessage = function(sender, message) {
                console.log('TEST STUB: chatModule.addMessage called: [' + sender + '] ' + message);
                window.__chatMessages = window.__chatMessages || [];
                window.__chatMessages.push({ sender: sender, message: message });
            };
            console.log('TEST STUB: window.chatModule.addMessage has been mocked.');

            // Mock backendCommunicatorModule to prevent 'sendUserPrompt' error
            window.backendCommunicatorModule = window.backendCommunicatorModule || {};
            window.backendCommunicatorModule.sendUserPrompt = function(prompt) {
                console.log('TEST STUB: backendCommunicatorModule.sendUserPrompt called with: ' + prompt);
                window.__backendCommunicatorPrompts = window.__backendCommunicatorPrompts || [];
                window.__backendCommunicatorPrompts.push(prompt);
            };
            console.log('TEST STUB: window.backendCommunicatorModule.sendUserPrompt has been mocked.');

            // Override setTimeout/clearTimeout for precise control in tests
            window.__originalSetTimeout = window.setTimeout;
            window.__originalClearTimeout = window.clearTimeout;
            window.__mockTimeouts = []; // Stores {id, callback, delay}
            window.__timeoutIdCounter = 0;

            window.setTimeout = function(callback, delay) {
                const id = 'mock_timeout_' + window.__timeoutIdCounter++;
                console.log('TEST STUB: setTimeout intercepted. ID: ' + id + ', Delay: ' + delay + ', Current mockTimeouts length: ' + window.__mockTimeouts.length);
                window.__mockTimeouts.push({ id: id, callback: callback, delay: delay });
                return id;
            };
            window.clearTimeout = function(id) {
                console.log('TEST STUB: clearTimeout intercepted for ID: ' + id + ', Current mockTimeouts length: ' + window.__mockTimeouts.length);
                const initialLength = window.__mockTimeouts.length;
                window.__mockTimeouts = window.__mockTimeouts.filter(function(t) { return t.id !== id; });
                if (window.__mockTimeouts.length === initialLength) {
                    console.warn('TEST STUB: clearTimeout called for ID ' + id + ' but it was not found in __mockTimeouts.');
                }
            };
            window.__triggerAllTimeouts = function() {
                console.log('TEST STUB: Triggering all ' + window.__mockTimeouts.length + ' active timeouts.');
                // Filter out extremely long timeouts (likely Selenium's internal async script timeout)
                const timeoutsToRun = window.__mockTimeouts.filter(t => t.delay < 1000000);
                // Keep very long ones, or clear them if they are the Selenium script timeout
                window.__mockTimeouts = window.__mockTimeouts.filter(t => t.delay >= 1000000);

                timeoutsToRun.forEach(function(t) {
                    try {
                        t.callback();
                    } catch (e) {
                        console.error('TEST STUB: Error running mocked setTimeout callback: ', e);
                    }
                });
            };
            console.log('TEST STUB: window.setTimeout and window.clearTimeout have been mocked.');


            // Reset any flags or transcripts for a clean start for each test
            window.__chatMessages = [];
            window.__recognizedTranscript = null;
            window.__speechModuleSpeakCalls = [];
            window.__speechSynthesisSpeakCalls = [];
            window.__backendCommunicatorPrompts = [];

            // Explicitly mock window.speechModule before injecting speech.js
            window.speechModule = {};
            console.log('TEST STUB: window.speechModule explicitly mocked before injection.');

            console.log('TEST STUB: Global test state reset in setUp.');
        """)
        time.sleep(0.1)  # Small pause after initial mocks are set up

        # Now, and only now, inject the application's JavaScript files.
        # speech.js will now bind to the *mocked* APIs.
        for js_path in [CHAT_MODULE_JS_PATH, PAGE_MANIPULATOR_JS_PATH, SPEECH_JS_PATH]:
            try:
                with open(js_path, 'r') as f:
                    js_content = f.read()
                self.driver.execute_script(js_content)
                print(f"INFO: Injected {js_path.name} into the page.")
            except Exception as e:
                self.fail(f"Failed to read or inject {js_path.name}: {e}")

        # After injection, ensure speechModule is set up and its recognition instance is exposed
        self.driver.execute_script("""
            if (window.speechModule && !window.speechModule.isSetUp) {
                window.speechModule.setUp();
            }
            window.__speechModuleRecognitionInstance = window.speechModule ? window.speechModule.recognition : null;
            if (window.__speechModuleRecognitionInstance) {
                console.log('TEST STUB: speechModule.recognition instance exposed as __speechModuleRecognitionInstance after setUp.');
                console.log('TEST STUB: __speechModuleRecognitionInstance ID: ' + window.__speechModuleRecognitionInstance.__instanceId);
            } else {
                console.log('TEST STUB: speechModule.recognition instance is not available after setUp.');
            }
        """)
        time.sleep(0.1)  # Small pause after final setup

    def _trigger_all_set_timeouts(self):
        """
        Manually triggers all currently captured setTimeout callbacks.
        Filters out extremely long timeouts (likely Selenium's internal async script timeout).
        """
        self.driver.execute_script("window.__triggerAllTimeouts();")
        time.sleep(0.01)  # Small pause to allow JS to process

    def _simulate_speech_result(self, transcript, is_final=True, after=120):
        """
        Helper to simulate a speech recognition result.
        This is primarily used for test_listen.
        For test_ask_confirmation, simulation is done directly in JS within execute_async_script.
        """

        # Define the inner function that will be executed in a separate thread
        def __inner():
            # time.sleep needs to be here to delay the execution of js_script
            # within the thread, not blocking the main test thread.
            time.sleep(after * 0.001)

            escaped_transcript_js = json.dumps(transcript)

            js_script = f"""
                if (window.__speechModuleRecognitionInstance && typeof window.__speechModuleRecognitionInstance.onresult === 'function') {{
                    const mockEvent = {{
                        results: [
                            [{{ transcript: {escaped_transcript_js}, confidence: 0.9 }}]
                        ],
                        resultIndex: 0
                    }};
                    mockEvent.results[0].isFinal = {str(is_final).lower()};

                    console.log('TEST STUB: Simulating recognition result via __speechModuleRecognitionInstance.onresult with transcript: ' + {escaped_transcript_js} + ' (isFinal: ' + {str(is_final).lower()} + ')');
                    window.__speechModuleRecognitionInstance.onresult(mockEvent);
                }} else {{
                    console.warn('TEST STUB: Could not simulate onresult: __speechModuleRecognitionInstance or onresult is not a function.');
                }}
            """
            # Execute the script to simulate the result in the browser
            # This call is from a separate Python thread, so it won't block the main test thread.
            self.driver.execute_script(js_script)

            # Trigger all currently scheduled timeouts after simulating onresult
            # (speech.js sets new timeouts like silenceTimeout, listenTimeout).
            self._trigger_all_set_timeouts()

        # Create and start the thread
        thread = Thread(target=__inner)
        thread.start()
        # The main thread continues immediately, without waiting for 'thread' to finish.

    def _simulate_speech_end(self):
        """Helper to simulate the onend event for speech recognition."""
        self.driver.execute_script("""
            if (window.__speechModuleRecognitionInstance && typeof window.__speechModuleRecognitionInstance.onend === 'function') {
                console.log('TEST STUB: Simulating recognition onend via __speechModuleRecognitionInstance.onend');
                window.__speechModuleRecognitionInstance.onend();
            } else {
                console.warn('TEST STUB: Could not simulate onend: __speechModuleRecognitionInstance or onend is not a function.');
            }
        """)

    def _get_synthesis_speak_calls(self):
        """Helper to retrieve recorded speechSynthesis.speak calls."""
        return self.driver.execute_script("return window.__speechSynthesisSpeakCalls;")

    def _get_chat_messages(self):
        """Helper to retrieve recorded chat messages."""
        return self.driver.execute_script("return window.__chatMessages;")

    def test_speak(self):
        print("\n--- Running test_speak ---")
        result = self.driver.execute_async_script("""
            const callback = arguments[arguments.length - 1];
            window.speechModule.speak("Hello, world!")
              .then(() => {
                  console.log('speechModule.speak Promise resolved.');
                  callback('done');
              })
              .catch(err => {
                  console.error('speechModule.speak Promise rejected:', err.message || err);
                  callback('error:' + (err.message || err));
              });
        """)
        print(f"Result from execute_async_script: {result}")
        self.assertEqual(result, "done", "Expected speechModule.speak promise to resolve to 'done'.")
        speak_calls = self._get_synthesis_speak_calls()
        self.assertIn("Hello, world!", speak_calls, "Speech synthesis should have spoken 'Hello, world!'.")
        print("SUCCESS: Speak action verified.")

    def test_speak_audibly_and_verify_logs(self):
        print("\n--- Running test_speak_audibly_and_verify_logs ---")
        test_phrase = "This is an audible speech test from Selenium!"

        # Call speechModule.speak with the test phrase.
        # execute_async_script will wait for the promise from speak() to resolve.
        result = self.driver.execute_async_script(f"""
            const callback = arguments[arguments.length - 1];
            const phrase = arguments[0];
            window.speechModule.speak(phrase)
              .then(() => {{
                  console.log('JS TEST: speechModule.speak Promise resolved for audible test.');
                  callback('done');
              }})
              .catch(err => {{
                  console.error('JS TEST: speechModule.speak Promise rejected for audible test:', err.message || err);
                  callback('error:' + (err.message || err));
              }});
        """, test_phrase)

        self.assertEqual(result, "done", "Expected speechModule.speak promise to resolve to 'done' for audible test.")

        # 1. Verify the speak call was registered by our mock speechSynthesis
        speak_calls = self._get_synthesis_speak_calls()
        self.assertIn(test_phrase, speak_calls, f"Speech synthesis mock should have recorded speaking '{test_phrase}'.")
        print(f"INFO: Verified '{test_phrase}' was sent to speechSynthesis.speak mock.")

        # 2. Check browser console logs for any SEVERE or ERROR messages related to speech synthesis.
        # This acts as a check that the *attempt* to synthesize didn't fail internally.
        browser_logs = self.driver.get_log('browser')
        speech_errors = [
            log for log in browser_logs
            if log['level'] == 'SEVERE' and 'speechSynthesis' in log['message']
        ]
        self.assertEqual(len(speech_errors), 0, f"Expected no speech synthesis errors, but found: {speech_errors}")
        print("INFO: No SEVERE errors found in browser console logs related to speech synthesis.")

        print("SUCCESS: Audible speech (via mock and log verification) test passed.")

    def test_listen(self):
        print("\n--- Running test_listen ---")
        self.driver.execute_script("""
            window.currentSpeechCallback = function(transcript) {
                console.log('TEST STUB: currentSpeechCallback received:' + transcript);
                window.__recognizedTranscript = transcript;
            };
            console.log('TEST STUB: window.currentSpeechCallback has been set.');
        """)

        self.driver.execute_script("window.speechModule.listen(null, null);")
        print("INFO: speechModule.listen called.")

        mock_transcript = "Test transcript with 'quotes' and backslashes \\"  # Example to test escaping
        self._simulate_speech_result(mock_transcript)  # This calls onresult and then triggers timers

        try:
            transcript_sent_to_backend = WebDriverWait(self.driver, 5).until(
                lambda d: d.execute_script(
                    "return window.__backendCommunicatorPrompts.length > 0 ? window.__backendCommunicatorPrompts[0] : null;")
            )
            print(f"INFO: Retrieved transcript sent to backend: '{transcript_sent_to_backend}'")
            self.assertEqual(transcript_sent_to_backend, mock_transcript,
                             "Expected the transcript to be sent to backendCommunicatorModule.")
        except TimeoutException:
            self.fail("Timed out waiting for __backendCommunicatorPrompts to be set.")

        is_listening_after_result = self.driver.execute_script("return window.speechModule.isListening;")
        self.assertFalse(is_listening_after_result,
                         "speechModule should stop listening after processing a final result.")
        print("SUCCESS: Listen action verified.")

    def test_stop_listening(self):
        print("\n--- Running test_stop_listening ---")
        self.driver.execute_script("window.speechModule.listen();")
        print("INFO: speechModule.listen() called in test_stop_listening.")

        try:
            WebDriverWait(self.driver, 5).until(
                lambda d: d.execute_script("""
                    return window.__speechModuleRecognitionInstance != null &&
                           window.__speechModuleRecognitionInstance.started === true;
                """)
            )
            print("INFO: __speechModuleRecognitionInstance is available and started is TRUE.")
        except TimeoutException:
            is_rec_null = self.driver.execute_script("return window.__speechModuleRecognitionInstance == null;")
            rec_started_state = self.driver.execute_script(
                "return window.__speechModuleRecognitionInstance ? window.__speechModuleRecognitionInstance.started : 'N/A';");
            rec_instance_id = self.driver.execute_script(
                "return window.__speechModuleRecognitionInstance ? window.__speechModuleRecognitionInstance.__instanceId : 'N/A';");
            print(
                f"ERROR: Timeout waiting for __speechModuleRecognitionInstance to be started. Is null: {is_rec_null}, Started state: {rec_started_state}, Instance ID: {rec_instance_id}")
            self.fail("Timed out waiting for SpeechRecognition instance to be available and started.")

        self.driver.execute_script("window.speechModule.stopListening();")
        print("INFO: speechModule.stopListening() called.")

        stopped = self.driver.execute_script(
            "return window.__speechModuleRecognitionInstance ? window.__speechModuleRecognitionInstance.stopped : null;");
        started = self.driver.execute_script(
            "return window.__speechModuleRecognitionInstance ? window.__speechModuleRecognitionInstance.started : null;");
        is_listening_flag = self.driver.execute_script("return window.speechModule.isListening;")

        print(
            f"DEBUG: Final state: __speechModuleRecognitionInstance.started = {started}, __speechModuleRecognitionInstance.stopped = {stopped}, speechModule.isListening = {is_listening_flag}")

        self.assertTrue(stopped, "Expected SpeechRecognition instance to be stopped.")
        self.assertFalse(is_listening_flag, "speechModule.isListening flag should be false after stopListening.")
        print("SUCCESS: Stop listening action verified.")

    # def test_ask_confirmation(self):
    #     print("\n--- Running test_ask_confirmation ---")
    #     prompt_text = "Do you want to proceed?"
    #
    #     # --- Test "yes" confirmation ---
    #     print("\n--- Testing 'yes' confirmation ---")
    #     # The entire asynchronous flow for this scenario is managed within this one execute_async_script call.
    #     result_yes = self.driver.execute_async_script("""
    #         const seleniumCallback = arguments[arguments.length - 1];
    #         const prompt = arguments[0];
    #         const simulatedResponse = arguments[1]; // e.g., "yes", "no", "maybe"
    #         const delayBeforeSimulating = 100; // Small delay to allow listen() to fully initialize
    #
    #         let isListeningConfirmed = false;
    #
    #         // 1. Call askConfirmation, which starts the prompt and listening
    #         window.speechModule.askConfirmation(prompt)
    #             .then(result => {
    #                 console.log('JS TEST: askConfirmation resolved with: ' + result);
    #                 seleniumCallback(result); // Resolve Selenium's callback with the final result
    #             })
    #             .catch(error => {
    #                 console.error('JS TEST: askConfirmation rejected with: ' + error);
    #                 seleniumCallback('ERROR: ' + error.message); // Resolve Selenium's callback with an error
    #             });
    #
    #         // 2. Schedule the simulation logic to run concurrently/after speechModule starts listening
    #         const waitForListeningAndSimulate = () => {
    #             // Ensure speechModule.isListening is true and recognition instance is ready
    #             if (window.speechModule.isListening && window.__speechModuleRecognitionInstance && !isListeningConfirmed) {
    #                 isListeningConfirmed = true; // Set flag to ensure this part only runs once
    #                 console.log('JS TEST: speechModule detected as listening. Simulating speech result now: ' + simulatedResponse);
    #
    #                 const mockEvent = {
    #                     results: [[{ transcript: simulatedResponse, confidence: 0.9 }]],
    #                     resultIndex: 0
    #                 };
    #                 mockEvent.results[0].isFinal = true;
    #
    #                 // Trigger the onresult handler
    #                 window.__speechModuleRecognitionInstance.onresult(mockEvent);
    #
    #                 // Trigger all currently scheduled timeouts (specifically, the silence timeout from onresult)
    #                 window.__triggerAllTimeouts();
    #
    #             } else if (!isListeningConfirmed) { // Only continue waiting if not yet confirmed as listening
    #                 console.log('JS TEST: Waiting for speechModule to become ready to listen...');
    #                 // Keep checking until speechModule starts listening
    #                 window.setTimeout(waitForListeningAndSimulate, 50); // Check every 50ms
    #             }
    #         };
    #
    #         // Start the simulation check after a slight initial delay
    #         window.setTimeout(waitForListeningAndSimulate, delayBeforeSimulating);
    #     """, prompt_text, "yes")
    #
    #     self.assertTrue(result_yes, "askConfirmation should return true for 'yes'.")
    #     print("SUCCESS: askConfirmation (yes) verified.")
    #
    #     # --- Test "no" confirmation ---
    #     print("\n--- Testing 'no' confirmation ---")
    #     self.driver.execute_script("""
    #         // Reset state for a new confirmation
    #         window.__speechSynthesisSpeakCalls = [];
    #         window.speechModule.pendingConfirmationResolver = null;
    #         window.speechModule.finalTranscript = '';
    #         window.speechModule.isListening = false;
    #         if (window.__speechModuleRecognitionInstance) {
    #             window.__speechModuleRecognitionInstance.started = false;
    #             window.__speechModuleRecognitionInstance.stopped = false;
    #         }
    #         console.log('JS TEST: State reset for next confirmation test.');
    #     """)
    #
    #     result_no = self.driver.execute_async_script("""
    #         const seleniumCallback = arguments[arguments.length - 1];
    #         const prompt = arguments[0];
    #         const simulatedResponse = arguments[1];
    #         const delayBeforeSimulating = 100;
    #
    #         let isListeningConfirmed = false;
    #
    #         window.speechModule.askConfirmation(prompt)
    #             .then(result => {
    #                 console.log('JS TEST: askConfirmation resolved with: ' + result);
    #                 seleniumCallback(result);
    #             })
    #             .catch(error => {
    #                 console.error('JS TEST: askConfirmation rejected with: ' + error);
    #                 seleniumCallback('ERROR: ' + error.message);
    #             });
    #
    #         const waitForListeningAndSimulate = () => {
    #             if (window.speechModule.isListening && window.__speechModuleRecognitionInstance && !isListeningConfirmed) {
    #                 isListeningConfirmed = true;
    #                 console.log('JS TEST: speechModule detected as listening. Simulating speech result now: ' + simulatedResponse);
    #                 const mockEvent = {
    #                     results: [[{ transcript: simulatedResponse, confidence: 0.9 }]],
    #                     resultIndex: 0
    #                 };
    #                 mockEvent.results[0].isFinal = true;
    #                 window.__speechModuleRecognitionInstance.onresult(mockEvent);
    #                 window.__triggerAllTimeouts();
    #             } else if (!isListeningConfirmed) {
    #                 window.setTimeout(waitForListeningAndSimulate, 50);
    #             }
    #         };
    #         window.setTimeout(waitForListeningAndSimulate, delayBeforeSimulating);
    #     """, prompt_text, "no")
    #
    #     self.assertFalse(result_no, "askConfirmation should return false for 'no'.")
    #     print("SUCCESS: askConfirmation (no) verified.")
    #
    #     # --- Test "unrecognized" then "yes" confirmation ---
    #     # This still requires two separate execute_async_script calls because speech.js
    #     # resolves its promise with null on unrecognized input, which means the first
    #     # execute_async_script will complete, and then a new interaction needs to be started.
    #     print("\n--- Testing 'unrecognized' then 'yes' confirmation (Phase 1: Unrecognized) ---")
    #     self.driver.execute_script("""
    #         // Reset state for the first phase of the retry attempt
    #         window.__speechSynthesisSpeakCalls = []; // Clear speak calls from previous attempt
    #         window.speechModule.pendingConfirmationResolver = null;
    #         window.speechModule.finalTranscript = '';
    #         window.speechModule.isListening = false;
    #         if (window.__speechModuleRecognitionInstance) {
    #             window.__speechModuleRecognitionInstance.started = false;
    #             window.__speechModuleRecognitionInstance.stopped = false;
    #         }
    #         console.log('JS TEST: State reset for phase 1 of retry confirmation test.');
    #     """)
    #
    #     # Phase 1: Simulate unrecognized input, which should resolve the promise with null
    #     result_unrecognized = self.driver.execute_async_script("""
    #         const seleniumCallback = arguments[arguments.length - 1];
    #         const prompt = arguments[0];
    #         const simulatedResponse = arguments[1]; // "maybe"
    #         const initialDelay = 100;
    #
    #         let isListeningConfirmed = false;
    #
    #         window.speechModule.askConfirmation(prompt)
    #             .then(result => {
    #                 console.log('JS TEST: askConfirmation resolved with: ' + result + ' (unrecognized)');
    #                 seleniumCallback(result); // This will be null due to unrecognized input
    #             })
    #             .catch(error => {
    #                 console.error('JS TEST: askConfirmation rejected with: ' + error);
    #                 seleniumCallback('ERROR: ' + error.message);
    #             });
    #
    #         const waitForListeningAndSimulate = () => {
    #             if (window.speechModule.isListening && window.__speechModuleRecognitionInstance && !isListeningConfirmed) {
    #                 isListeningConfirmed = true;
    #                 console.log('JS TEST: First listen detected. Simulating unrecognized response: ' + simulatedResponse);
    #                 const mockEvent = {
    #                     results: [[{ transcript: simulatedResponse, confidence: 0.9 }]],
    #                     resultIndex: 0
    #                 };
    #                 mockEvent.results[0].isFinal = true;
    #                 window.__speechModuleRecognitionInstance.onresult(mockEvent);
    #                 window.__triggerAllTimeouts(); // Trigger silence timeout, leading to null resolution
    #             } else if (!isListeningConfirmed) {
    #                 window.setTimeout(waitForListeningAndSimulate, 50);
    #             }
    #         };
    #         window.setTimeout(waitForListeningAndSimulate, initialDelay);
    #     """, prompt_text, "maybe")
    #
    #     self.assertIsNone(result_unrecognized, "askConfirmation for unrecognized input should return None.")
    #     print("INFO: First attempt with unrecognized input returned None as expected.")
    #
    #     # Phase 2: Simulate the retry with a "yes" response
    #     print("\n--- Testing 'unrecognized' then 'yes' confirmation (Phase 2: Retry with 'yes') ---")
    #     self.driver.execute_script("""
    #         // Reset state for the second phase (retry attempt)
    #         window.__speechSynthesisSpeakCalls = []; // Clear speak calls from previous phase
    #         window.speechModule.pendingConfirmationResolver = null;
    #         window.speechModule.finalTranscript = '';
    #         window.speechModule.isListening = false;
    #         if (window.__speechModuleRecognitionInstance) {
    #             window.__speechModuleRecognitionInstance.started = false;
    #             window.__speechModuleRecognitionInstance.stopped = false;
    #         }
    #         console.log('JS TEST: State reset for phase 2 of retry confirmation test.');
    #     """)
    #
    #     result_final_retry = self.driver.execute_async_script("""
    #         const seleniumCallback = arguments[arguments.length - 1];
    #         const prompt = arguments[0];
    #         const simulatedResponse = arguments[1]; // "yes"
    #         const initialDelay = 100;
    #
    #         let isListeningConfirmed = false;
    #
    #         window.speechModule.askConfirmation(prompt)
    #             .then(result => {
    #                 console.log('JS TEST: askConfirmation resolved with: ' + result + ' (final retry)');
    #                 seleniumCallback(result);
    #             })
    #             .catch(error => {
    #                 console.error('JS TEST: askConfirmation rejected with: ' + error);
    #                 seleniumCallback('ERROR: ' + error.message);
    #             });
    #
    #         const waitForListeningAndSimulate = () => {
    #             if (window.speechModule.isListening && window.__speechModuleRecognitionInstance && !isListeningConfirmed) {
    #                 isListeningConfirmed = true;
    #                 console.log('JS TEST: Second listen detected. Simulating final response: ' + simulatedResponse);
    #                 const mockEvent = {
    #                     results: [[{ transcript: simulatedResponse, confidence: 0.9 }]],
    #                     resultIndex: 0
    #                 };
    #                 mockEvent.results[0].isFinal = true;
    #                 window.__speechModuleRecognitionInstance.onresult(mockEvent);
    #                 window.__triggerAllTimeouts();
    #             } else if (!isListeningConfirmed) {
    #                 window.setTimeout(waitForListeningAndSimulate, 50);
    #             }
    #         };
    #         window.setTimeout(waitForListeningAndSimulate, initialDelay);
    #     """, prompt_text, "yes")
    #
    #     self.assertTrue(result_final_retry, "askConfirmation should return true on successful retry.")
    #     print("SUCCESS: askConfirmation (unrecognized then yes) verified.")
