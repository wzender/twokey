(function () {
  const state = {
    setup: false,
    stream: null,
    recorder: null,
    recordPromise: null,
    resolve: null,
    reject: null,
    phraseData: null,
    voicesReady: false,
    pendingSpeech: null,
    userActivatedAudio: false,
  };

  const setStatus = (text) => {
    const el = document.getElementById("output-status");
    if (el) el.textContent = text;
  };

  const cleanup = () => {
    if (state.stream) {
      state.stream.getTracks().forEach((track) => track.stop());
    }
    state.stream = null;
    state.recorder = null;
    state.resolve = null;
    state.reject = null;
  };

  const stopRecording = () => {
    if (state.recorder && state.recorder.state !== "inactive") {
      state.recorder.stop();
    }
  };

  const pickHebrewVoice = () => {
    if (!window.speechSynthesis) return null;
    const voices = window.speechSynthesis.getVoices() || [];
    return (
      voices.find((v) => v.lang && v.lang.toLowerCase().startsWith("he")) ||
      voices.find((v) => v.lang && v.lang.toLowerCase().includes("he-il")) ||
      voices.find((v) => v.lang && v.lang.toLowerCase().startsWith("en")) ||
      voices[0] ||
      null
    );
  };

  const speakHebrew = (text) => {
    if (!window.speechSynthesis || !text) return;
    try {
      window.speechSynthesis.resume();
    } catch (e) {
      /* ignore */
    }
    const utterance = new SpeechSynthesisUtterance(String(text));
    utterance.lang = "he-IL";
    utterance.rate = 0.95;
    utterance.pitch = 1.0;
    const voice = pickHebrewVoice();
    if (voice) {
      utterance.voice = voice;
    }
    window.speechSynthesis.cancel();
    window.speechSynthesis.speak(utterance);
  };

  const startRecording = async () => {
    if (state.recorder) return;

    try {
      setStatus("מקליט... שחררו לניתוח.");
      state.stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(state.stream);
      const chunks = [];

      state.recordPromise = new Promise((resolve, reject) => {
        state.resolve = resolve;
        state.reject = reject;
      });

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) chunks.push(event.data);
      };

      recorder.onerror = (event) => {
        state.reject?.(event.error || new Error("Recording failed."));
        cleanup();
      };

      recorder.onstop = async () => {
        try {
          const blob = new Blob(chunks, { type: "audio/wav" });
          const file = new File([blob], "recording.wav", { type: "audio/wav" });

          setStatus("Analyzing...");
          const formData = new FormData();
          formData.append("file", file);
          if (state.phraseData && state.phraseData.native) {
            formData.append("phrase", state.phraseData.native);
          }
          if (state.phraseData && state.phraseData.hint) {
            formData.append("hint", state.phraseData.hint);
          }
          if (state.phraseData && state.phraseData.arabic_transliteration) {
            formData.append(
              "arabic_transliteration",
              state.phraseData.arabic_transliteration
            );
          }

          const response = await fetch("/api/analyze", {
            method: "POST",
            body: formData,
          });

          if (!response.ok) {
            const message = (await response.text()) || "הניתוח נכשל.";
            state.resolve?.({ error: message });
          } else {
            const data = await response.json();
            state.resolve?.(data);
          }
        } catch (err) {
          state.reject?.(err);
        } finally {
          cleanup();
          state.recordPromise = null;
        }
      };

      state.recorder = recorder;
      recorder.start();
    } catch (err) {
      cleanup();
      state.recordPromise = null;
      throw err;
    }
  };

  const attachListeners = () => {
    if (state.setup) return;
    const button = document.getElementById("record-button");
    if (!button) {
      setTimeout(attachListeners, 100);
      return;
    }

    button.addEventListener("pointerdown", (e) => {
      e.preventDefault();
      state.userActivatedAudio = true;
      if (window.speechSynthesis) {
        try {
          window.speechSynthesis.cancel();
          window.speechSynthesis.resume();
        } catch (err) {
          /* ignore */
        }
      }
      startRecording().catch((err) => {
        cleanup();
        state.recordPromise = null;
        state.reject?.(err);
        setStatus(err?.message || "לא ניתן להתחיל הקלטה.");
      });
    });

    const stop = () => stopRecording();
    button.addEventListener("pointerup", stop);
    button.addEventListener("pointercancel", stop);
    button.addEventListener("mouseleave", stop);

    state.setup = true;
  };

  if (window.speechSynthesis) {
    window.speechSynthesis.onvoiceschanged = () => {
      state.voicesReady = true;
      if (state.pendingSpeech) {
        speakHebrew(state.pendingSpeech);
        state.pendingSpeech = null;
      }
    };
  }

  document.addEventListener("DOMContentLoaded", () => {
    attachListeners();
  });

  window.dash_clientside = Object.assign({}, window.dash_clientside, {
    audio: {
      recordAudio: async function (nClicks, phraseData) {
        state.phraseData = phraseData || null;
        attachListeners();

        if (!nClicks) {
          return window.dash_clientside.no_update;
        }

        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
          return { error: "אין גישה למיקרופון בדפדפן זה." };
        }

        if (state.recordPromise) {
          try {
            const result = await state.recordPromise;
            return result;
          } finally {
            state.recordPromise = null;
          }
        }

        return { error: "לחצו והחזיקו את כפתור ההקלטה כדי להתחיל." };
      },
      speakFeedback: function (data) {
        if (!data || !data.feedback || !window.speechSynthesis) {
          return window.dash_clientside.no_update;
        }

        try {
          // Do not autoplay to satisfy browser policies; wait for user click on play.
          state.pendingSpeech = data.feedback;
          setStatus("מוכן לניגון. לחצו על \"נגן משוב קולי\".");
          if (!state.userActivatedAudio) {
            return window.dash_clientside.no_update;
          }
          // If user already interacted, we can preload voices for faster play.
          window.speechSynthesis.getVoices();
        } catch (err) {
          console.error("Speech synthesis failed", err); // eslint-disable-line no-console
        }

        return Date.now().toString();
      },
      playFeedback: function (nClicks, data) {
        if (!nClicks || !data || !data.feedback || !window.speechSynthesis) {
          return window.dash_clientside.no_update;
        }
        try {
          state.userActivatedAudio = true;
          if (state.voicesReady || window.speechSynthesis.getVoices().length > 0) {
            state.voicesReady = true;
            speakHebrew(data.feedback);
          } else {
            state.pendingSpeech = data.feedback;
            window.speechSynthesis.getVoices();
          }
        } catch (err) {
          console.error("Speech synthesis failed", err); // eslint-disable-line no-console
        }
        return Date.now().toString();
      },
      downloadFeedback: async function (nClicks, data) {
        if (!nClicks || !data || !data.feedback) {
          return window.dash_clientside.no_update;
        }

        try {
          const response = await fetch("/api/tts", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text: data.feedback }),
          });

          if (!response.ok) {
            setStatus("לא ניתן להוריד את המשוב הקולי.");
            return window.dash_clientside.no_update;
          }

          const blob = await response.blob();
          const url = URL.createObjectURL(blob);
          const a = document.createElement("a");
          a.href = url;
          a.download = "feedback-hebrew.mp3";
          document.body.appendChild(a);
          a.click();
          document.body.removeChild(a);
          URL.revokeObjectURL(url);
          setStatus("המשוב הקולי ירד בהצלחה.");
        } catch (err) {
          console.error("Download failed", err); // eslint-disable-line no-console
          setStatus("לא ניתן להוריד את המשוב הקולי.");
        }

        return Date.now().toString();
      },
    },
  });
})();
