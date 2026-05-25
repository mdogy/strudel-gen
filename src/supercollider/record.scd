// Reusable recording snippets. Evaluate the block you need in the SC IDE.

// --- Settings (run once per session) ---
(
s.recHeaderFormat = "WAV";
s.recSampleFormat = "int24";
s.recChannels = 2;
)

// --- Timed stereo record (edit path + duration) ---
(
Routine({
    0.5.wait;
    s.record(
        path: "~/Desktop/soundscape.wav".standardizePath,
        duration: 300
    );
}).play;
)

// --- Stop early ---
// s.stopRecording;

// --- Multi-stem (6ch) — requires numOutputBusChannels=6 in startup ---
// s.record(path: "~/Desktop/stems.wav".standardizePath, numChannels: 6, duration: 300);
