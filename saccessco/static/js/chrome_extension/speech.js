// speech.js
(function(window) {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  const synthesis = window.speechSynthesis;

  // Debugging: Log the synthesis object captured by speech.js at load time
  console.log("speech.js: Captured synthesis object at load time:", synthesis);


  const speech = {
    isSetUp: false,
    isListening: false,
    callBack: null, // General callback for user prompts
    recognition: null,
    _listeningBeforeSpeak: false,
    silenceTimeoutId: null,
    silenceTimeoutDuration: 3700, // Adjust as needed (milliseconds)
    listenTimeoutId: null,
    listenTimeoutDuration: 7000, // Maximum listening time without a final result (milliseconds)
    finalTranscript: '',
    timeoutCallback: null, // General callback for listen timeout
    pendingConfirmationResolver: null, // Resolver for askConfirmation promise
    pendingUserInputResolver: null, // NEW: Resolver for askUserInput promise

    setUp() {
      if (this.isSetUp) return;
      if (!SpeechRecognition) {
        console.error('SpeechRecognition API not supported.');
        return;
      }

      this.recognition = new SpeechRecognition();
      this.recognition.interimResults = true; // Get interim results for better responsiveness
      this.recognition.continuous = true;   // Keep listening until explicitly stopped
      this.recognition.maxAlternatives = 1;

      this.recognition.onresult = (event) => {
        let interimTranscript = '';
        let currentFinalTranscript = '';

        for (let i = event.resultIndex; i < event.results.length; ++i) {
          if (event.results[i].isFinal) {
            currentFinalTranscript += event.results[i][0].transcript.trim();
          } else {
            interimTranscript += event.results[i][0].transcript.trim();
          }
        }

        console.log("Interim:", interimTranscript);
        console.log("Final:", currentFinalTranscript);

        if (currentFinalTranscript) {
          this.finalTranscript += currentFinalTranscript + ' ';
          // Reset silence timeout on any final result
          clearTimeout(this.silenceTimeoutId);
          console.log("speech.js: Cleared old silenceTimeoutId. Setting new one.");
          this.silenceTimeoutId = setTimeout(() => {
            console.log("speech.js: Long pause detected (silence timeout fired). Processing statement.");
            if (this.isListening) { // Only process if still actively listening
                if (this.pendingConfirmationResolver) {
                    console.log("speech.js: Dispatching to _processConfirmationResponse.");
                    this._processConfirmationResponse(this.finalTranscript.trim().toLowerCase());
                } else if (this.pendingUserInputResolver) {
                    console.log("speech.js: Dispatching to _processUserInputResponse.");
                    this._processUserInputResponse(this.finalTranscript.trim());
                } else if (typeof this.callBack === 'function' && this.finalTranscript.trim()) {
                    // General user prompt
                    console.log("speech.js: Dispatching to general callback.");
                    this.callBack(this.finalTranscript.trim());
                    this.finalTranscript = ''; // Reset for the next statement
                    this.stopListening(); // Stop listening after processing a statement
                }
            }
          }, this.silenceTimeoutDuration);

          // Reset the overall listen timeout as we received a final result
          clearTimeout(this.listenTimeoutId);
          console.log("speech.js: Cleared old listenTimeoutId. Setting new one.");
          this.listenTimeoutId = setTimeout(() => {
            console.log("speech.js: Listen timeout reached without a complete statement (listen timeout fired).");
            if (this.isListening) { // Only process if still actively listening
              this.stopListening();
              window.chatModule.addMessage("Saccessco", "Listening timed out.");
              if (this.pendingConfirmationResolver) {
                console.log("speech.js: Resolving pendingConfirmationResolver with null due to listen timeout.");
                this.pendingConfirmationResolver(null); // Resolve with null on timeout
                this.pendingConfirmationResolver = null;
              }
              if (this.pendingUserInputResolver) { // NEW: Handle user input timeout
                console.log("speech.js: Resolving pendingUserInputResolver with null due to listen timeout.");
                this.pendingUserInputResolver(null);
                this.pendingUserInputResolver = null;
              }
              if (typeof this.timeoutCallback === 'function') {
                console.log("speech.js: Calling general timeoutCallback.");
                this.timeoutCallback(); // Call the general timeout callback
              }
            }
          }, this.listenTimeoutDuration);
        }
      };

      this.recognition.onerror = (evt) => {
        console.warn('Speech error:', evt.error);
        if (evt.error === 'no-speech' || evt.error === 'network') {
          // These errors might be transient, don't necessarily stop listening or resolve immediately
          return;
        }
        this.isListening = false;
        clearTimeout(this.silenceTimeoutId);
        clearTimeout(this.listenTimeoutId);
        if (this.pendingConfirmationResolver) {
          console.log("speech.js: Resolving pendingConfirmationResolver with null due to recognition error.");
          this.pendingConfirmationResolver(null); // Resolve with null on error
          this.pendingConfirmationResolver = null;
        }
        if (this.pendingUserInputResolver) { // NEW: Handle user input error
          console.log("speech.js: Resolving pendingUserInputResolver with null due to recognition error.");
          this.pendingUserInputResolver(null);
          this.pendingUserInputResolver = null;
        }
        try { this.recognition.stop(); } catch {}
      };

      this.recognition.onend = () => {
        console.log('Speech recognition ended.');
        if (this.isListening) {
          // If isListening is still true, it means continuous recognition, so restart
          console.log("speech.js: Recognition ended, but isListening is true. Restarting recognition.");
          this.startRecognitionInternal();
        } else {
          // If isListening is false, it means we explicitly stopped it
          console.log("speech.js: Recognition ended, isListening is false. Not restarting.");
          let micButton = document.querySelector("#floating-mic-button");
          if (micButton) {
            micButton.classList.remove("mic-active");
            micButton.classList.add("mic-inactive");
          }
        }
      };

      this.isSetUp = true;
      console.log("speech.js: setUp complete.");
    },

    startRecognitionInternal() {
      try {
        this.recognition.start();
        console.log('Speech recognition started.');
        // Set the initial listen timeout
        clearTimeout(this.listenTimeoutId); // Clear any existing listen timeout before starting a new one
        console.log("speech.js: Setting initial listen timeout.");
        this.listenTimeoutId = setTimeout(() => {
          console.log("speech.js: Initial listen timeout reached (initial listen timeout fired).");
          if (this.isListening) { // Only process if still actively listening
            this.stopListening();
            window.chatModule.addMessage("Saccessco", "Listening timed out.");
            if (this.pendingConfirmationResolver) {
              console.log("speech.js: Resolving pendingConfirmationResolver with null due to initial listen timeout.");
              this.pendingConfirmationResolver(null); // Resolve with null on timeout
              this.pendingConfirmationResolver = null;
            }
            if (this.pendingUserInputResolver) { // NEW: Handle user input timeout
              console.log("speech.js: Resolving pendingUserInputResolver with null due to initial listen timeout.");
              this.pendingUserInputResolver(null);
              this.pendingUserInputResolver = null;
            }
            if (typeof this.timeoutCallback === 'function') {
              console.log("speech.js: Calling general timeoutCallback due to initial listen timeout.");
              this.timeoutCallback(); // Call the general timeout callback
            }
          }
        }, this.listenTimeoutDuration);
      } catch (e) {
        console.error('Failed to start SpeechRecognition:', e);
        this.isListening = false;
        if (this.pendingConfirmationResolver) {
          console.log("speech.js: Resolving pendingConfirmationResolver with null due to start error.");
          this.pendingConfirmationResolver(null); // Resolve with null on start error
          this.pendingConfirmationResolver = null;
        }
        if (this.pendingUserInputResolver) { // NEW: Handle user input start error
          console.log("speech.js: Resolving pendingUserInputResolver with null due to start error.");
          this.pendingUserInputResolver(null);
          this.pendingUserInputResolver = null;
        }
      }
    },

    // MODIFIED: Removed default parameter for callback
    listen(callback, timeoutCb = null) {
      this.setUp();
      if (!this.recognition || this.isListening) {
        console.log("speech.js: Listen call ignored. Recognition not ready or already listening.");
        return; // Don't start if already listening
      }

      // Assign callback, defaulting to backendCommunicatorModule if not provided
      this.callBack = callback || (window.backendCommunicatorModule && window.backendCommunicatorModule.sendUserPrompt);
      if (!this.callBack) {
        console.warn("speech.js: No valid callback for listen function. backendCommunicatorModule.sendUserPrompt might not be available.");
      }
      this.timeoutCallback = timeoutCb; // Set the general timeout callback
      this.isListening = true;
      this.finalTranscript = ''; // Reset transcript for a new listening session
      console.log("speech.js: Attempting to start recognition from listen().");
      this.startRecognitionInternal();

      let micButton = document.querySelector("#floating-mic-button");
      if (micButton) {
        micButton.classList.remove("mic-inactive");
        micButton.classList.add("mic-active");
      }
    },

    stopListening() {
      if (this.recognition && this.isListening) {
        this.isListening = false;
        clearTimeout(this.silenceTimeoutId); // Clear any pending silence timeout
        clearTimeout(this.listenTimeoutId); // Clear any pending listen timeout
        console.log("speech.js: Cleared all listen timeouts.");
        try {
          this.recognition.stop();
          console.log('Speech recognition stopped by user or timeout.');
        } catch (e) {
          console.error('Error stopping recognition:', e);
        }
        // Resolvers are handled by onend/onerror or when a result is processed
        // No need to resolve with null here, as the intent is to stop listening,
        // and the promise should only resolve with a value if input was received.
        // If stopped externally, the promise will remain pending until a result or timeout.
      } else {
        console.log("speech.js: stopListening called, but not currently listening or recognition not ready.");
      }
    },

    speak(text) {
      if (!synthesis) {
        console.error('Speech synthesis not supported.');
        return Promise.reject(new Error('Speech synthesis not supported.'));
      }
      console.log("speech.js: speak called with text:", text);

      return new Promise((resolve, reject) => {
          // Stop listening before speaking
          if (this.isListening) {
            this._listeningBeforeSpeak = true;
            console.log("speech.js: Was listening before speak. Stopping listening temporarily.");
            this.stopListening(); // This will trigger onend, which will restart recognition if isListening is true
          } else {
            this._listeningBeforeSpeak = false;
          }

          const utter = new SpeechSynthesisUtterance(text);
          utter.onend = () => {
            console.log('speech.js: Speech synthesis finished.');
            // Resume listening if it was active before speaking
            if (this._listeningBeforeSpeak) {
              console.log("speech.js: Resuming listening after speak.");
              this.listen(this.callBack, this.timeoutCallback); // Pass original callbacks back
              this._listeningBeforeSpeak = false;
            }
            resolve();
          };
          utter.onerror = (event) => {
            console.error('speech.js: Speech synthesis error:', event);
            if (this._listeningBeforeSpeak) {
              console.log("speech.js: Resuming listening after speak error.");
              this.listen(this.callBack, this.timeoutCallback); // Pass original callbacks back
              this._listeningBeforeSpeak = false;
            }
            reject(new Error(event.error || 'Speech synthesis error'));
          };
          synthesis.speak(utter);
      });
    },

    async askConfirmation(prompt) {
      console.log("speech.js: askConfirmation called with prompt:", prompt);
      return new Promise(async (resolve) => {
        this.pendingConfirmationResolver = resolve;
        this.finalTranscript = ''; // Reset transcript for new confirmation
        try {
            await this.speak(prompt + ". Please respond with 'yes' or 'no'.");
            // Start listening after the prompt is spoken
            if (!this.isListening) {
                console.log("speech.js: Starting listen for confirmation response.");
                this.listen(); // Just start listening; onresult will handle dispatch to _processConfirmationResponse
            }
        } catch (error) {
            console.error("speech.js: Error speaking confirmation prompt:", error);
            if (this.pendingConfirmationResolver) {
                this.pendingConfirmationResolver(null); // Resolve with null on speak error
                this.pendingConfirmationResolver = null;
            }
        }
      });
    },

    _processConfirmationResponse(response) {
      console.log("speech.js: _processConfirmationResponse received:", response);
      this.stopListening(); // Stop listening once a response is received
      if (this.pendingConfirmationResolver) {
        if (response === 'yes' || response === 'yep' || response === 'affirmative') {
          console.log("speech.js: Confirmation resolved to true.");
          this.pendingConfirmationResolver(true);
          this.pendingConfirmationResolver = null;
        } else if (response === 'no' || response === 'nope' || response === 'negative') {
          console.log("speech.js: Confirmation resolved to false.");
          this.pendingConfirmationResolver(false);
          this.pendingConfirmationResolver = null;
        } else {
          // If not understood, re-prompt and re-listen
          console.log("speech.js: Confirmation not understood. Re-prompting.");
          this.finalTranscript = ''; // Clear transcript for re-prompt
          this.speak("Sorry, I didn't understand. Please respond with 'yes' or 'no'.")
              .then(() => {
                  if (!this.isListening) {
                      console.log("speech.js: Re-listening for confirmation.");
                      this.listen(); // Re-listen
                  }
              })
              .catch(error => {
                  console.error("speech.js: Error re-speaking prompt:", error);
                  if (this.pendingConfirmationResolver) {
                      this.pendingConfirmationResolver(null);
                      this.pendingConfirmationResolver = null;
                  }
              });
        }
      }
    },

    // NEW FUNCTION: askUserInput
    async askUserInput(prompt, sensitive = false) {
      console.log("speech.js: askUserInput called with prompt:", prompt, "sensitive:", sensitive);
      return new Promise(async (resolve) => {
        this.pendingUserInputResolver = resolve;
        this.finalTranscript = ''; // Reset transcript for new user input

        let fullPrompt = prompt;
        if (sensitive) {
          fullPrompt += ". Please spell it out character by character, or type it.";
        } else {
          fullPrompt += ". Please say your response.";
        }

        try {
            await this.speak(fullPrompt);
            // Start listening after the prompt is spoken
            if (!this.isListening) {
                console.log("speech.js: Starting listen for user input response.");
                this.listen(); // Just start listening; onresult will handle dispatch to _processUserInputResponse
            }
        } catch (error) {
            console.error("speech.js: Error speaking user input prompt:", error);
            if (this.pendingUserInputResolver) {
                this.pendingUserInputResolver(null); // Resolve with null on speak error
                this.pendingUserInputResolver = null;
            }
        }
      });
    },

    _processUserInputResponse(response) {
      console.log("speech.js: _processUserInputResponse received:", response);
      this.stopListening(); // Stop listening once a response is received
      if (this.pendingUserInputResolver) {
        console.log("speech.js: User input resolved to:", response);
        this.pendingUserInputResolver(response);
        this.pendingUserInputResolver = null;
      }
    },
  };

  // Expose it globally
  window.speechModule = speech;
  console.log("--DEBUG--: speechModule attached to window");
})(window);
