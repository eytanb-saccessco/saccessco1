// speech.js
(function(window) {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  const synthesis = window.speechSynthesis;

  const speech = {
    isSetUp: false,
    isListening: false,
    callBack: null,
    recognition: null,
    _listeningBeforeSpeak: false,
    silenceTimeoutId: null,
    silenceTimeoutDuration: 2000, // Adjust as needed (milliseconds)
    listenTimeoutId: null,
    listenTimeoutDuration: 6000, // Maximum listening time without a final result (milliseconds)
    finalTranscript: '',
    timeoutCallback: null, // New callback for timeout
    pendingConfirmationResolver: null, // Resolver for askConfirmation promise

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
          this.silenceTimeoutId = setTimeout(() => {
            console.log("Long pause detected. Processing statement.");
            if (this.isListening && typeof this.callBack === 'function' && this.finalTranscript.trim()) {
              this.callBack(this.finalTranscript.trim());
              this.finalTranscript = ''; // Reset for the next statement
              this.stopListening(); // Stop listening after processing a statement
            } else if (this.isListening && this.pendingConfirmationResolver) {
              this._processConfirmationResponse(this.finalTranscript.trim().toLowerCase());
              this.stopListening();
            }
          }, this.silenceTimeoutDuration);

          // Reset the overall listen timeout as we received a final result
          clearTimeout(this.listenTimeoutId);
          this.listenTimeoutId = setTimeout(() => {
            console.log("Listen timeout reached without a complete statement.");
            if (this.isListening) {
              this.stopListening();
              window.chatModule.addMessage("Saccessco", "Listening timed out.");
              if (this.pendingConfirmationResolver) {
                this.pendingConfirmationResolver(null); // Resolve with null on timeout
                this.pendingConfirmationResolver = null;
              }
            }
          }, this.listenTimeoutDuration);
        }
      };

      this.recognition.onerror = (evt) => {
        console.warn('Speech error:', evt.error);
        if (evt.error === 'no-speech' || evt.error === 'network') {
          return;
        }
        this.isListening = false;
        clearTimeout(this.silenceTimeoutId);
        clearTimeout(this.listenTimeoutId);
        if (this.pendingConfirmationResolver) {
          this.pendingConfirmationResolver(null); // Resolve with null on error
          this.pendingConfirmationResolver = null;
        }
        try { this.recognition.stop(); } catch {}
      };

      this.recognition.onend = () => {
        console.log('Speech recognition ended.');
        if (this.isListening) {
          this.startRecognitionInternal();
        } else {
          let micButton = document.querySelector("#floating-mic-button");
          if (micButton) {
            micButton.classList.remove("mic-active");
            micButton.classList.add("mic-inactive");
          }
        }
      };

      this.isSetUp = true;
    },

    startRecognitionInternal() {
      try {
        this.recognition.start();
        console.log('Speech recognition started.');
        // Set the initial listen timeout
        this.listenTimeoutId = setTimeout(() => {
          console.log("Initial listen timeout reached.");
          if (this.isListening) {
            this.stopListening();
            window.chatModule.addMessage("Saccessco", "Listening timed out.");
            if (typeof this.timeoutCallback === 'function') {
              this.timeoutCallback(); // Call the timeout callback
            }
            if (this.pendingConfirmationResolver) {
              this.pendingConfirmationResolver(null); // Resolve with null on timeout
              this.pendingConfirmationResolver = null;
            }
          }
        }, this.listenTimeoutDuration);
      } catch (e) {
        console.error('Failed to start SpeechRecognition:', e);
        this.isListening = false;
        if (this.pendingConfirmationResolver) {
          this.pendingConfirmationResolver(null); // Resolve with null on start error
          this.pendingConfirmationResolver = null;
        }
      }
    },

    listen(callback = window.backendCommunicatorModule.sendUserPrompt, timeoutCb = null) {
      this.setUp();
      if (!this.recognition || this.isListening) return;

      this.callBack = callback;
      this.timeoutCallback = timeoutCb;
      this.isListening = true;
      this.finalTranscript = ''; // Reset transcript for a new listening session
      this.startRecognitionInternal();
    },

    stopListening() {
      if (this.recognition && this.isListening) {
        this.isListening = false;
        clearTimeout(this.silenceTimeoutId); // Clear any pending silence timeout
        clearTimeout(this.listenTimeoutId); // Clear any pending listen timeout
        try {
          this.recognition.stop();
          console.log('Speech recognition stopped by user or timeout.');
        } catch (e) {
          console.error('Error stopping recognition:', e);
        }
        if (this.pendingConfirmationResolver) {
          this.pendingConfirmationResolver(null); // Resolve with null if stopped externally
          this.pendingConfirmationResolver = null;
        }
      }
    },

    speak(text) { // Remove onEndCallback from signature if you use Promise for completion
      if (!synthesis) {
        console.error('Speech synthesis not supported.');
        // If not supported, we can immediately resolve or reject the promise
        return Promise.reject(new Error('Speech synthesis not supported.'));
      }

      return new Promise((resolve, reject) => { // <-- ADD THIS Promise WRAPPER
          // Stop listening before speaking
          if (this.isListening) {
            this._listeningBeforeSpeak = true;
            this.stopListening();
          } else {
            this._listeningBeforeSpeak = false;
          }

          const utter = new SpeechSynthesisUtterance(text);
          utter.onend = () => {
            console.log('Speech synthesis finished.');
            // Resume listening if it was active before speaking
            if (this._listeningBeforeSpeak) {
              this.listen(this.callBack, this.timeoutCallback);
              this._listeningBeforeSpeak = false;
            }
            resolve(); // <-- Resolve the Promise on end
          };
          utter.onerror = (event) => {
            console.error('Speech synthesis error:', event);
            if (this._listeningBeforeSpeak) {
              this.listen(this.callBack, this.timeoutCallback);
              this._listeningBeforeSpeak = false;
            }
            reject(new Error(event.error || 'Speech synthesis error')); // <-- Reject on error
          };
          synthesis.speak(utter);
      });
    },
    async askConfirmation(prompt) {
      return new Promise(async (resolve) => { // Use async here too
        this.pendingConfirmationResolver = resolve;
        try {
            await this.speak(prompt + ". Please respond with 'yes' or 'no'.");
            // Start listening after the prompt is spoken
            if (!this.isListening) {
                this.listen(this._confirmationCallback.bind(this), () => {
                    // Timeout callback for confirmation
                    if (this.pendingConfirmationResolver) {
                        this.pendingConfirmationResolver(null);
                        this.pendingConfirmationResolver = null;
                    }
                });
            }
        } catch (error) {
            console.error("Error speaking confirmation prompt:", error);
            if (this.pendingConfirmationResolver) {
                this.pendingConfirmationResolver(null); // Resolve with null on speak error
                this.pendingConfirmationResolver = null;
            }
        }
      });
    },

    _confirmationCallback(response) {
      const lowercasedResponse = response.trim().toLowerCase();
      if (this.pendingConfirmationResolver) {
        if (lowercasedResponse === 'yes' || lowercasedResponse === 'yep' || lowercasedResponse === 'affirmative') {
          this.pendingConfirmationResolver(true);
          this.pendingConfirmationResolver = null;
        } else if (lowercasedResponse === 'no' || lowercasedResponse === 'nope' || lowercasedResponse === 'negative') {
          this.pendingConfirmationResolver(false);
          this.pendingConfirmationResolver = null;
        } else {
          // No need for a callback here if speak returns a promise
          this.speak("Sorry, I didn't understand. Please respond with 'yes' or 'no'.")
              .then(() => {
                  // Re-listen if not understood
                  if (!this.isListening) {
                      this.listen(this._confirmationCallback.bind(this), () => {
                          if (this.pendingConfirmationResolver) {
                              this.pendingConfirmationResolver(null);
                              this.pendingConfirmationResolver = null;
                          }
                      });
                  }
              })
              .catch(error => {
                  console.error("Error re-speaking prompt:", error);
                  if (this.pendingConfirmationResolver) {
                      this.pendingConfirmationResolver(null);
                      this.pendingConfirmationResolver = null;
                  }
              });
        }
      }
    },
  };

  // Expose it globally
  window.speechModule = speech;
})(window);