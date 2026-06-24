// Dr. Who Inspired Ambient Soundscape — self-contained render script.
//
// Usage: sclang dr-who-render.scd [output_path] [duration_seconds]
// Defaults: /tmp/dr-who-soundscape.wav, 120 s
//
// Sound design v5:
//   - No noise-based percussion (was causing static)
//   - Soft sine kick + sine "ping" accent replace hat/snare
//   - Melody uses proper phrases with variations (A A B A C A B)
//     so you hear a recognisable Dr. Who hook that returns and develops
//   - All gate=0 sent explicitly so notes don't hold forever
//   - All var declarations at TOP of each block (SC 3.x requirement)

(
var outPath  = if(thisProcess.argv.size > 0,
    { thisProcess.argv[0] }, { "/tmp/dr-who-soundscape.wav" });
var duration = if(thisProcess.argv.size > 1,
    { thisProcess.argv[1].asFloat }, { 120.0 });

s.options.sampleRate           = 48000;
s.options.numInputBusChannels  = 0;   // don't record input — avoids bleed

s.waitForBoot {

    // ------------------------------------------------------------------ //
    // ALL VAR DECLARATIONS FIRST
    // ------------------------------------------------------------------ //
    var bpm       = 78;                          // relaxed sci-fi pace
    var clock     = TempoClock(bpm / 60.0);

    // E natural minor (E4 F#4 G4 A4 B4 C5 D5 E5)
    var scale     = [329.63, 370.00, 392.00, 440.00, 493.88, 523.25, 587.33, 659.25];

    // Bass figure: E1 D1 E1 D1 E1 D1 C1 D1
    var bassNotes = [82.4, 73.4, 82.4, 73.4, 82.4, 73.4, 65.4, 73.4];

    // Pad roots: E3 G3 B3 E3
    var padFreqs  = [164.8, 196.0, 246.9, 164.8];

    // Kick pattern (16 steps, 16th notes): beats 1 and 3 only
    var kickPat   = [1,0,0,0, 0,0,0,0, 1,0,0,0, 0,0,0,0];

    // Ping accent on the "and" of 2 — like the syncopated Dr. Who pulse
    var pingPat   = [0,0,0,0, 0,0,1,0, 0,0,0,0, 0,0,1,0];

    // ---- Melody phrases (scale degrees, E natural minor) ----
    // Phrase A: main Dr. Who hook  B  D  E  D  B  G  A  B
    var phraseA   = [4, 6, 7, 6, 4, 2, 3, 4];
    // Phrase B: upper variation    E  D  E  D  B  D  E  B
    var phraseB   = [7, 6, 7, 6, 4, 6, 7, 4];
    // Phrase C: lower/sparse       E  G  B  A  E  G  B
    var phraseC   = [0, 2, 4, 3, 0, 2, 4];
    // Phrase D: condensed hook (first 5 notes only, then rest)
    var phraseD   = [4, 6, 7, 6, 4];

    // Sequence of phrases: A A B A C A B D A ...
    var phrases   = [phraseA, phraseA, phraseB, phraseA,
                     phraseC, phraseA, phraseB, phraseD, phraseA];

    // Note rhythm pattern (in beats): short-short-long feel
    var noteDurs  = [1, 1, 2, 1, 2, 1, 1, 3];

    // Gaps between phrases (in beats): max 4 so silence never exceeds ~3 s
    var gaps      = [2, 4, 2, 4, 2, 4, 2, 4];

    // Routine handles + shared reference to the currently-playing lead synth
    var drumRout, bassRout, padRout, melRout;
    var currentLead = nil;   // set by melRout, cleared on release

    // ------------------------------------------------------------------ //
    // SYNTHDEFS
    // ------------------------------------------------------------------ //

    // Sine kick: pure frequency drop, no noise
    SynthDef(\kick, { |out = 0, amp = 0.5|
        var freq = EnvGen.kr(Env([160, 48], [0.1], \exp));
        var sig  = SinOsc.ar(freq) * EnvGen.ar(Env.perc(0.005, 0.32, 1, -4), doneAction: 2);
        Out.ar(out, (sig * amp).dup);
    }).add;

    // Sine "ping": short, bright sine blip — replaces noisy hi-hat
    SynthDef(\ping, { |out = 0, freq = 880, amp = 0.12|
        var sig = SinOsc.ar(freq)
                * EnvGen.ar(Env.perc(0.002, 0.08, 1, -8), doneAction: 2);
        Out.ar(out, (sig * amp).dup);
    }).add;

    // Bass: pure sine + 2nd harmonic, gentle LFO wobble
    SynthDef(\dwBass, { |out = 0, freq = 82.4, amp = 0.48, gate = 1|
        var wobble = SinOsc.kr(0.13, 0, freq * 0.006);
        var osc    = SinOsc.ar(freq + wobble)
                   + (SinOsc.ar((freq * 2) + wobble) * 0.11);
        var env    = EnvGen.kr(Env.adsr(0.06, 0.28, 0.82, 3.5), gate, doneAction: 2);
        Out.ar(out, FreeVerb.ar(osc * env, 0.62, 0.88, 0.3).dup * amp);
    }).add;

    // Theremin lead: pure sine + vibrato.
    // Uses gate=1 input so we can release with synth.set(\gate, 0).
    SynthDef(\dwLead, { |out = 0, freq = 493.9, amp = 0.32, gate = 1|
        var vib  = SinOsc.kr(4.0, 0, freq * 0.009);
        var osc  = SinOsc.ar(freq + vib);
        var env  = EnvGen.kr(Env.adsr(0.25, 0.2, 0.88, 4.5), gate, doneAction: 2);
        var echo = DelayC.ar(osc * env, 1.0, 60.0 / bpm * 0.5) * 0.22;
        Out.ar(out, FreeVerb.ar((osc * env) + echo, 0.86, 0.93, 0.2).dup * amp);
    }).add;

    // Chord pad: E-minor sine triad, slow attack
    SynthDef(\dwPad, { |out = 0, freq = 164.8, amp = 0.13, gate = 1|
        var env  = EnvGen.kr(Env.adsr(3.2, 2.0, 0.65, 11.0), gate, doneAction: 2);
        var oscs = SinOsc.ar(freq * [1.0, 1.189, 1.498, 2.0]) * [0.4, 0.27, 0.2, 0.13];
        Out.ar(out, FreeVerb.ar(Mix(oscs) * env, 0.91, 0.96, 0.2).dup * amp);
    }).add;

    s.sync;

    s.recHeaderFormat = "WAV";
    s.recSampleFormat = "int24";

    // ------------------------------------------------------------------ //
    // ROUTINES
    // ------------------------------------------------------------------ //

    // --- Drums: kick + ping, no noise ---
    drumRout = Routine({
        var i = 0;
        loop {
            var j = i % 16;
            if (kickPat[j] == 1) { Synth(\kick, [\amp, 0.48]) };
            if (pingPat[j] == 1) { Synth(\ping, [\freq, 1200, \amp, 0.09]) };
            0.25.wait;   // 16th note
            i = i + 1;
        };
    }).play(clock);

    // --- Bass ---
    bassRout = Routine({
        var i = 0;
        loop {
            Synth(\dwBass, [\freq, bassNotes[i % 8], \amp, 0.44]);
            2.0.wait;
            i = i + 1;
        };
    }).play(clock);

    // --- Pad ---
    padRout = Routine({
        var i    = 0;
        var prev = nil;
        loop {
            if (prev.notNil) { prev.release(2.0) };
            prev = Synth(\dwPad, [\freq, padFreqs[i % 4], \amp, 0.12]);
            8.0.wait;
            i = i + 1;
        };
    }).play(clock);

    // --- Melody: phrase-based with variations ---
    // Each phrase plays through fully, then rests before the next phrase.
    // The sequence (phraseA, phraseA, phraseB, …) gives the "motive + return"
    // structure the listener can follow.
    melRout = Routine({
        var pIdx = 0;
        loop {
            var phrase  = phrases[pIdx % phrases.size];
            var gap     = gaps[pIdx % gaps.size];
            var noteIdx = 0;

            // Play every note in the phrase with explicit gate release
            phrase.do { |deg|
                var dur   = noteDurs[noteIdx % noteDurs.size];
                var hold  = (dur - 0.18).max(0.1);
                currentLead = Synth(\dwLead, [\freq, scale[deg], \amp, 0.30]);
                hold.wait;
                currentLead.set(\gate, 0);
                currentLead = nil;
                0.18.wait;
                noteIdx = noteIdx + 1;
            };

            gap.wait;                   // breath between phrases
            pIdx = pIdx + 1;
        };
    }).play(clock);

    // ------------------------------------------------------------------ //
    // RECORDING CONTROLLER (AppClock — waits are real seconds)
    // ------------------------------------------------------------------ //
    Routine({
        1.0.wait;
        s.record(path: outPath.standardizePath, duration: duration + 14);
        ("Recording to: " ++ outPath).postln;

        // Stop drums/bass/pad at the nominal end — they've done their job.
        // Keep melody running 5 s into the reverb tail so there's no
        // silent gap before fade-out.
        duration.wait;
        drumRout.stop;
        bassRout.stop;
        padRout.stop;

        // Melody continues 5 more seconds, then releases cleanly
        5.0.wait;
        if (currentLead.notNil) {
            currentLead.set(\gate, 0);
            currentLead = nil;
        };
        melRout.stop;
        clock.stop;

        // Reverb tail
        3.0.wait;
        "Recording complete.".postln;
        1.0.wait;
        0.exit;
    }).play;
};
)
