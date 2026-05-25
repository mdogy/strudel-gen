// Dr. Who Inspired Ambient Soundscape — self-contained render script.
//
// Usage (from terminal):
//   sclang dr-who-render.scd [output_path] [duration_seconds]
//
// Defaults: output = /tmp/dr-who-soundscape.wav, duration = 120 s
//
// What it does:
//   1. Boots scsynth with resources for generative audio
//   2. Defines three SynthDefs (bass, theremin lead, eerie texture)
//   3. Plays the Dr. Who-inspired pattern via SC Routines
//   4. Records to WAV (24-bit, 48 kHz, stereo)
//   5. Exits cleanly after recording finishes

(
var outPath = if(thisProcess.argv.size > 0,
    { thisProcess.argv[0] },
    { "/tmp/dr-who-soundscape.wav" }
);
var duration = if(thisProcess.argv.size > 1,
    { thisProcess.argv[1].asFloat },
    { 120.0 }
);

s.options.numBuffers      = 1024 * 64;
s.options.memSize         = 8192 * 16;
s.options.numOutputBusChannels = 2;
s.options.numInputBusChannels  = 2;
s.options.sampleRate      = 48000;

s.waitForBoot {

    // --- SynthDefs ---

    // Sweeping sawtooth bass (the iconic "woo" pulse)
    SynthDef(\dwBass, { |out = 0, freq = 82.4, amp = 0.38, gate = 1|
        var osc  = Mix([Saw.ar(freq) * 0.45,
                        Saw.ar(freq * 0.998) * 0.3,
                        SinOsc.ar(freq) * 0.25]);
        var env  = EnvGen.kr(Env.adsr(0.06, 0.4, 0.72, 5.0), gate, doneAction: 2);
        var filt = RLPF.ar(osc, LFNoise1.kr(0.18).exprange(180, 560), 0.35);
        var rev  = FreeVerb.ar(filt * env, 0.82, 0.91, 0.4);
        Out.ar(out, (filt * env * 0.28 + rev * 0.72).dup * amp);
    }).add;

    // Sine-wave theremin lead (the melodic line)
    SynthDef(\dwLead, { |out = 0, freq = 493.9, amp = 0.22, gate = 1|
        var vib = SinOsc.kr(4.8, 0, freq * 0.011);
        var osc = SinOsc.ar(freq + vib);
        var env = EnvGen.kr(Env.adsr(1.4, 0.6, 0.82, 7.0), gate, doneAction: 2);
        var del = CombC.ar(osc * env, 0.75, 0.333, 4.5, 0.38);
        var rev = FreeVerb.ar(osc * env + del, 0.88, 0.95, 0.28);
        Out.ar(out, rev.dup * amp);
    }).add;

    // Spectral texture chord (the eerie, alien "shimmer")
    SynthDef(\dwTexture, { |out = 0, freq = 329.6, amp = 0.16, gate = 1|
        var osc = SinOsc.ar(freq * [1, 1.5, 2, 3]) * [0.42, 0.3, 0.18, 0.1];
        var env = EnvGen.kr(Env.adsr(3.2, 2.0, 0.6, 12.0), gate, doneAction: 2);
        var mix = Mix(osc) * env;
        var rev = FreeVerb.ar(mix, 0.91, 0.96, 0.25);
        Out.ar(out, rev.dup * amp);
    }).add;

    s.sync;

    s.recHeaderFormat = "WAV";
    s.recSampleFormat = "int24";

    Routine({

        // Dr. Who — E minor
        // Bass figure:  E1  D1  E1  D1  E1  D1  C1  D1
        var bassFreqs = #[82.4, 73.4, 82.4, 73.4, 82.4, 73.4, 65.4, 73.4];
        // Lead melody:  B4    D5    E5    D5    B4    E4    G4    A4
        var leadFreqs = #[493.9, 587.3, 659.3, 587.3, 493.9, 329.6, 392.0, 440.0];
        // Texture root: E3    G3    B3    E4
        var texFreqs  = #[164.8, 196.0, 246.9, 329.6];

        var beatDur = 1.8;   // seconds per bass step — slow, glacial
        var steps   = (duration / beatDur).asInteger;

        // Let SynthDefs register
        1.0.wait;

        // Start recording
        s.record(path: outPath.standardizePath, duration: duration + 5);
        ("Recording to: " ++ outPath).postln;
        0.6.wait;

        steps.do { |i|
            Synth(\dwBass, [\freq, bassFreqs[i % 8], \amp, 0.38]);

            if ((i % 2) == 0) {
                Synth(\dwLead, [\freq, leadFreqs[i % 8], \amp, 0.22]);
            };

            if ((i % 4) == 0) {
                Synth(\dwTexture, [\freq, texFreqs[i % 4], \amp, 0.16]);
            };

            beatDur.wait;
        };

        // Tail — let reverb decay
        5.0.wait;
        "Recording complete.".postln;
        1.0.wait;
        0.exit;

    }).play;
};
)
