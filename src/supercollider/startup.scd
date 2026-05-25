// SuperDirt startup — copy this into SC's startup file (File > Open Startup File).
// See docs/guide.md Part 2 for rationale on each value.

(
s.reboot {
    s.options.numBuffers = 1024 * 256;
    s.options.memSize = 8192 * 32;
    s.options.numWireBufs = 128;
    s.options.maxNodes = 1024 * 32;
    s.options.numOutputBusChannels = 2;
    s.options.numInputBusChannels = 2;
    // s.options.sampleRate = 48000;  // uncomment for video-sync sessions

    s.waitForBoot {
        ~dirt = SuperDirt(2, s);
        ~dirt.loadSoundFiles;

        // ~dirt.loadSoundFiles("/path/to/my-samples/*");

        s.sync;

        ~dirt.start(57120, 0 ! 12);

        ~d1 = ~dirt.orbits[0]; ~d2 = ~dirt.orbits[1];
        ~d3 = ~dirt.orbits[2]; ~d4 = ~dirt.orbits[3];
        ~d5 = ~dirt.orbits[4]; ~d6 = ~dirt.orbits[5];
    };

    s.latency = 0.3;
};
)
