(
s.options.numBuffers           = 1024 * 64;
s.options.memSize              = 8192 * 16;
// 1024 (was 512 → 256 → 64) — supersaw loaded fine at 512 but
// supersine/supermandolin appear to fall later in default-synths.scd
// where the buffer count is exhausted.  1024 is what SuperDirt's own
// example boot file uses.
s.options.numWireBufs          = 1024;
s.options.maxNodes             = 1024 * 8;
s.options.numOutputBusChannels = 2;
s.options.numInputBusChannels  = 2;
s.latency = 0.3;

s.waitForBoot {
    ~dirt = SuperDirt(2, s);
    s.sync;
    ~dirt.start(57120, 0 ! 12);
    // Diagnostic: which super-synths actually registered?
    ["supersaw", "supersine", "superpiano", "supermandolin", "supergong",
     "supersquare", "supertri"].do { |name|
        var loaded = SynthDescLib.global.synthDescs[name.asSymbol].notNil;
        ("DIAG_SYNTH " ++ name ++ " = " ++ loaded).postln;
    };
    ("SuperDirt: listening on port " ++ ~dirt.serverPort).postln;
};
)
