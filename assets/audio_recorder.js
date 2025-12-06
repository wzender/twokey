(function () {
  const state = {
    setup: false,
    stream: null,
    recorder: null,
    recordPromise: null,
    resolve: null,
    reject: null,
    phraseData: null,
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

  const startRecording = async () => {
    if (state.recorder) return;

    try {
      setStatus("Recording... release to analyze.");
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

          const response = await fetch("/api/analyze", {
            method: "POST",
            body: formData,
          });

          if (!response.ok) {
            const message = (await response.text()) || "Analysis failed.";
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
      startRecording().catch((err) => {
        cleanup();
        state.recordPromise = null;
        state.reject?.(err);
        setStatus(err?.message || "Unable to start recording.");
      });
    });

    const stop = () => stopRecording();
    button.addEventListener("pointerup", stop);
    button.addEventListener("pointercancel", stop);
    button.addEventListener("mouseleave", stop);

    state.setup = true;
  };

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
          return { error: "Microphone access is unavailable in this browser." };
        }

        if (state.recordPromise) {
          try {
            const result = await state.recordPromise;
            return result;
          } finally {
            state.recordPromise = null;
          }
        }

        return { error: "Press and hold the record button to start." };
      },
    },
  });
})();
