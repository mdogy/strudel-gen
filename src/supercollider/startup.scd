// SuperDirt startup — copy this into SC's startup file (File > Open Startup File).
// See docs/guide.md Part 2 for rationale on each value.
//
// The server boot always runs so headless render scripts get a live server
// without waiting. SuperDirt sample loading (which takes 60-120 s) is
// skipped in headless mode (argv.size > 0 = a render script was passed).
// In GUI/IDE mode (no script args) SuperDirt loads as usual.

(
var isHeadless = (thisProcess.argv.size > 0);

s.reboot {
    s.options.numBuffers           = 1024 * 64;
    s.options.memSize              = 8192 * 16;
    // 1024 (was 64) — needed for SuperDirt's default-synths.scd to fully load.
    // At 64, supersine / supermandolin / supergong silently fail to register.
    s.options.numWireBufs          = 1024;
    s.options.maxNodes             = 1024 * 8;
    s.options.numOutputBusChannels = 2;
    s.options.numInputBusChannels  = 2;
    // s.options.sampleRate = 48000;  // uncomment for video-sync sessions

    if (isHeadless.not) {
        // GUI / IDE mode: load SuperDirt for Strudel live sessions
        s.waitForBoot {
            ~dirt = SuperDirt(2, s);
            ~dirt.loadSoundFiles;

            // ~dirt.loadSoundFiles("/path/to/my-samples/*");

            s.sync;

            ~dirt.start(57120, 0 ! 12);

            ~d1 = ~dirt.orbits[0]; ~d2 = ~dirt.orbits[1];
            ~d3 = ~dirt.orbits[2]; ~d4 = ~dirt.orbits[3];
            ~d5 = ~dirt.orbits[4]; ~d6 = ~dirt.orbits[5];
            // Diagnostic: confirm which super-synths actually registered.
            // Lets render_tidal.py grep `DIAG_SYNTH` and know exactly what is
            // available before evaluating any pattern that names them.
            ["supersaw", "supersine", "superpiano", "supersquare", "supertri",
             "supermandolin", "supergong", "superpwm", "superhex"].do { |name|
                var loaded = SynthDescLib.global.synthDescs[name.asSymbol].notNil;
                ("DIAG_SYNTH " ++ name ++ " " ++ if(loaded, "ok", "MISSING")).postln;
            };
        };
    };

    s.latency = 0.3;
};
)
