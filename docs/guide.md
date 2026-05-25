# Strudel → SuperDirt → SuperCollider Recorder: Complete Soundscape Production Guide

## Overview

This guide describes a fully local, code-driven pipeline for generating ambient soundscape audio files suitable for video backgrounds. The architecture has three layers that work together:

1. **Strudel** — a JavaScript live-coding environment that generates OSC (Open Sound Control) pattern messages[^1]
2. **SuperDirt** — an audio engine running inside SuperCollider that receives those OSC messages and synthesizes or plays back sounds[^2]
3. **SuperCollider Recorder** — SuperCollider's built-in recording class that writes the final audio to disk as a `.wav` file[^3]

The AI coder's job is to write Strudel pattern code. Everything else in this guide is setup and infrastructure that only needs to be done once.

***

## Part 1: Prerequisites and Installation

### 1.1 Install SuperCollider

Download the official installer for your OS from `https://supercollider.github.io/downloads`:[^4]

- **macOS**: Download the `.dmg`, drag `SuperCollider.app` to `/Applications`
- **Windows**: Download and run the `.exe` installer
- **Linux (Ubuntu/Debian)**: `sudo apt install supercollider`

After installing, open the SuperCollider IDE (`scide`). In the editor pane, type and evaluate (`Ctrl+Enter` / `Cmd+Enter`):

```supercollider
s.boot
```

Then test audio with:

```supercollider
{ SinOsc.ar(440) * 0.1 }.play;
```

You should hear a sine tone. If you do not, check `Language > Preferences > Audio` to select the correct sound device.[^4]

**macOS M1/M2 note**: You may need to manually switch your audio device to headphones in System Preferences the first time.[^4]

### 1.2 Install sc3-plugins

sc3-plugins extend SuperCollider with additional synthesizer UGens used by SuperDirt.[^5]

- **macOS/Windows**: Download the binary release from `https://supercollider.github.io/sc3-plugins`, unzip, and copy the `SC3plugins` folder to SuperCollider's Extensions directory. Find that directory by evaluating `Platform.userExtensionDir` in SC.[^6]
- **Linux (Ubuntu)**: `sudo apt install sc3-plugins`[^7]

After installing, restart SuperCollider and recompile the class library via `Language > Recompile Class Library`.

### 1.3 Install SuperDirt

SuperDirt is installed as a SuperCollider Quark (package). In the SuperCollider IDE, evaluate:

```supercollider
Quarks.checkForUpdates({ Quarks.install("SuperDirt", "v1.7.2"); thisProcess.recompile() })
```

Wait for the post window to confirm installation is complete. Alternatively, install manually by downloading these three repositories and placing them in your Extensions folder:[^8][^9]

- `https://github.com/musikinformatik/SuperDirt`
- `https://github.com/tidalcycles/Dirt-Samples` (rename folder to exactly `Dirt-Samples`)
- `https://github.com/supercollider-quarks/Vowel`

### 1.4 Install Node.js and pnpm

Strudel's OSC bridge requires Node.js:[^10]

```bash
# Install Node.js via nvm (recommended for macOS/Linux)
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
nvm install --lts

# Install pnpm
npm install -g pnpm
```

**Windows**: Download the Node.js installer from `https://nodejs.org` and install it.[^11]

### 1.5 Clone Strudel Repository

The OSC bridge requires a local clone of Strudel — it is not available from the hosted `strudel.cc` site:[^1]

```bash
git clone https://github.com/tidalcycles/strudel.git
cd strudel
pnpm install
```

***

## Part 2: SuperDirt Startup Configuration

### 2.1 The Startup File

SuperCollider has a startup file that runs automatically every time it boots. Open it from: `File > Open Startup File`.[^12]

Replace any existing contents with the following complete startup script. This configures SuperDirt with enough resources for generative soundscapes and exposes all 12 orbit buses:

```supercollider
(
s.reboot {
    s.options.numBuffers = 1024 * 256;    // sample buffer space
    s.options.memSize = 8192 * 32;        // RAM for synths
    s.options.numWireBufs = 128;          // internal audio routing buffers
    s.options.maxNodes = 1024 * 32;       // max simultaneous synth nodes
    s.options.numOutputBusChannels = 2;   // stereo output (increase for multi-stem)
    s.options.numInputBusChannels = 2;

    s.waitForBoot {
        ~dirt = SuperDirt(2, s);          // 2 channels per orbit (stereo)
        ~dirt.loadSoundFiles;             // load default Dirt-Samples library

        // Optional: load your own custom samples
        // ~dirt.loadSoundFiles("/path/to/your/samples/*");

        s.sync;

        ~dirt.start(57120, 0 ! 12);       // listen on OSC port 57120, 12 orbits

        // Named orbit references (optional convenience)
        ~d1 = ~dirt.orbits;  ~d2 = ~dirt.orbits[^1];
        ~d3 = ~dirt.orbits[^2];  ~d4 = ~dirt.orbits[^3];
        ~d5 = ~dirt.orbits[^4];  ~d6 = ~dirt.orbits[^5];
    };

    s.latency = 0.3;
};
)
```

Save the file. From this point on, SuperDirt starts automatically every time you open SuperCollider.[^12]

**Verifying startup**: After booting, the SC post window should show lines like `SuperDirt started listening on port 57120` and sample loading progress. No red error lines should appear.

### 2.2 Custom Sample Packs

To add your own samples (WAV or AIFF files), organize them into named subfolders:

```
/my-samples/
  drones/        <- each subfolder becomes a sample name
    drone1.wav
    drone2.wav
  pads/
    pad1.wav
  textures/
    texture1.wav
```

Then add this line inside `s.waitForBoot` in your startup file:[^13][^12]

```supercollider
~dirt.loadSoundFiles("/path/to/my-samples/*");
```

In Strudel, you then reference them as `s("drones")`, `s("pads")`, etc.

***

## Part 3: Running the OSC Bridge

The OSC bridge is a small Node.js server that forwards Strudel's pattern events (sent as OSC over UDP) to SuperDirt.[^14][^1]

### 3.1 Start the Bridge

In a terminal, from inside your cloned `strudel` folder:

```bash
pnpm run osc
```

You should see output like:

```
OSC bridge running, listening on localhost:57120
```

Leave this terminal window open for the entire session.[^1]

### 3.2 Open the Strudel REPL

In the same strudel folder, in a second terminal, start the local dev server:

```bash
pnpm run dev
```

Open your browser to `http://localhost:4321`. This is your Strudel code editor.[^10]

### 3.3 Switch Strudel's Audio Output to SuperDirt

By default, Strudel uses Web Audio API for sound. To route audio through SuperDirt instead, you must select the SuperDirt output in the REPL settings, or add this at the top of your pattern file:[^1]

In the Strudel REPL settings panel (gear icon), set Audio Output to **SuperDirt / OSC**.

Alternatively, when running the REPL in developer mode with the OSC bridge active, SuperDirt is automatically used as the audio destination.

**Connectivity check**: Play a simple test pattern in Strudel:

```javascript
s("bd sd bd sd")
```

You should hear drum sounds coming through SuperCollider's audio output, not the browser's Web Audio. The SC post window will show incoming OSC activity.

***

## Part 4: Recording the Output

All recording commands are run in the **SuperCollider IDE**, not in Strudel.

### 4.1 Basic Recording

```supercollider
// Start recording — specify output path and duration in seconds
s.record(path: "/Users/yourname/Desktop/soundscape.wav", duration: 300);
```

- `path`: full file path including filename; SuperCollider infers WAV format from the `.wav` extension[^15]
- `duration`: seconds of audio to record; recording stops automatically when complete[^16]

After issuing this command, go to Strudel and start playing your pattern. SuperCollider captures everything the audio server outputs. When `duration` seconds elapse, the post window shows `Recording stopped` and the file is ready.[^16]

**Important**: Each new recording needs a unique filename, or the previous file will be silently overwritten without warning.[^16]

### 4.2 Recording with a Script (Automated / Headless)

For a fully scripted workflow — start playing, wait, then stop — wrap recording inside a `Routine`:

```supercollider
(
Routine({
    // Prepare — give SuperDirt time to receive first OSC events
    0.5.wait;

    // Start writing to disk
    s.record(
        path: "/Users/yourname/Desktop/soundscape_v1.wav",
        duration: 600   // 10-minute recording
    );

    // The routine can now exit; recording continues in background
    // SC posts "Recording stopped." when done
}).play;
)
```

To stop recording early:

```supercollider
s.stopRecording;
```

### 4.3 Recording Settings

Set these **before** calling `s.record`:[^3]

```supercollider
// 24-bit WAV (better quality than default 32-bit float for most uses)
s.recHeaderFormat = "WAV";
s.recSampleFormat = "int24";

// Number of channels to record (match your output channel count)
s.recChannels = 2;
```

### 4.4 Multi-Stem Recording (Advanced)

For video post-production, recording separate stems (e.g., pads separate from textures) gives full mixing control. Each Strudel pattern layer can be assigned to a different orbit, and orbits can be recorded to separate audio buses.[^17][^18]

Modify the startup file to route orbits to separate stereo channels (e.g., 3 stereo stems = 6 channels total):

```supercollider
s.options.numOutputBusChannels = 6;   // 3 stereo outputs
// ...
~dirt.start(57120, [0, 2, 4]);        // orbits 0,1,2 → channels 0-1, 2-3, 4-5
```

In Strudel, assign patterns to orbits explicitly:

```javascript
// Orbit 0 → channel 0-1 (pads)
$: note("3 eb3 g3>").s("pad").slow(4).orbit(0)

// Orbit 1 → channel 2-3 (texture/drone)  
$: s("drones:2").slow(8).room(0.9).orbit(1)

// Orbit 2 → channel 4-5 (subtle percussion)
$: s("hh(3,8)").gain(0.3).orbit(2)
```

Record with `numChannels` set to 6:

```supercollider
s.record(path: "/path/to/stems.wav", numChannels: 6, duration: 300);
```

Split the resulting multichannel WAV into separate stereo files with any DAW or with `ffmpeg`:

```bash
# Extract channel pair 0-1 (pads)
ffmpeg -i stems.wav -filter_complex "[0:a]pan=stereo|c0=c0|c1=c1[out]" -map "[out]" pads.wav

# Extract channel pair 2-3 (drone)
ffmpeg -i stems.wav -filter_complex "[0:a]pan=stereo|c0=c2|c1=c3[out]" -map "[out]" drone.wav
```

***

## Part 5: Writing Soundscape Patterns in Strudel

The AI coder writes patterns in Strudel. Below are the key syntax elements and techniques specifically useful for ambient/soundscape composition.

### 5.1 Pattern Syntax Reference

```javascript
// --- Sound sources ---
s("pad")              // play sample named "pad" (index 0)
s("pad:2")            // play sample index 2 in the "pad" folder
s("sine")             // built-in sine wave oscillator
note("c3").s("sawtooth")  // synth with specified note

// --- Note/pitch ---
note("c3 eb3 g3")     // play chord tones in sequence
note("3 eb3 g3>")   // slow-cycle through values (one per cycle)
note("c3").scale("C:minor")  // use scale degrees

// --- Time modifiers ---
.slow(4)              // stretch pattern 4x longer
.fast(2)              // play pattern 2x faster
.cpm(30)              // set cycles per minute (tempo)

// --- Stacking layers ---
stack(
  note("c3").s("pad").slow(8),
  s("drone:1").slow(16),
  note("<g2 f2>").s("bass").slow(4)
)

// --- Effects (work with both Web Audio and SuperDirt) ---
.room(0.8)            // reverb: 0.0 dry to 1.0 very wet
.size(0.9)            // reverb room size
.delay(0.5)           // delay send amount
.delayt(0.375)        // delay time in seconds
.delayfb(0.6)         // delay feedback (0–1)
.lpf(800)             // low-pass filter cutoff Hz
.hpf(200)             // high-pass filter cutoff Hz
.gain(0.7)            // volume (0.0–2.0)
.pan("<0 0.5 1>")     // stereo pan position

// --- Pattern variation ---
.sometimes(x => x.room(0.9))   // apply effect randomly ~50% of events
.sometimes(x => x.rev())       // sometimes reverse playback
.jux(rev)             // play original left, reversed right (wide stereo)
.off(1/4, x => x.gain(0.3))   // ghost echo offset by 1/4 cycle

// --- Euclidean rhythms (for organic pulsing textures) ---
s("texture(3,8)")     // 3 hits distributed across 8 steps (Euclidean)
note("c3").euclid(5,13)       // irregular organic rhythm

// --- Silence and space ---
s("pad ~ ~ pad ~ pad ~ ~")    // ~ = rest/silence
```

### 5.2 Soundscape Pattern Templates

These are ready-to-use starting patterns. The AI coder should modify pitches, samples, effects depths, and timing to fit the video's mood.

**Slow drone pad (cinematic/atmospheric):**

```javascript
setcpm(20)
stack(
  // Root drone — very slow sustain
  note("2 c2 g2 f2>").s("sawtooth")
    .lpf(400).room(0.9).size(0.95)
    .gain(0.4).slow(8),

  // Sparse melodic gesture
  note("4 ~ eb4 ~ g4 ~ f4 ~>").s("sine")
    .room(0.8).gain(0.3).slow(4),

  // Textural pad layer
  note("c3,g3,eb3").s("pad")
    .room(0.85).delay(0.4).delayt(0.5).delayfb(0.5)
    .gain(0.5).slow(6)
)
```

**Alien/sci-fi ambience:**

```javascript
setcpm(15)
stack(
  // Metallic resonant drone
  note("1 ~ c1 ~>").s("metal")
    .lpf("<200 400 800>").room(0.95).gain(0.6).slow(16),

  // High shimmer
  note("c5,g5").s("sine")
    .sometimes(x => x.speed("<0.5 2>"))
    .room(0.9).gain(0.2).slow(8),

  // Sparse random ping
  s("pluck(2,16)").note("5 g4 eb5>")
    .delay(0.6).room(0.7).gain(0.3).slow(4)
)
```

**Nature-adjacent organic texture:**

```javascript
setcpm(25)
stack(
  // Breath-like low-frequency pulse
  note("2 d2 c2 bb1>").s("sine")
    .lpf(300).room(0.7).gain(0.35).slow(6),

  // Mid-register evolving pad
  note("c3,eb3,g3,bb3").s("pad")
    .room(0.8).size(0.9).gain(0.45).slow(8),

  // Sparse high texture (bird-like)
  s("flute(3,16)").note("5 g5 eb5 f5>")
    .room(0.9).gain(0.25).jux(rev).slow(5)
)
```

### 5.3 Prompt Template for the AI Coder

When instructing an AI coder to generate a soundscape, provide this prompt structure:

```
Generate a Strudel soundscape pattern for the following video context:

VIDEO MOOD: [e.g., "mysterious and slowly evolving, sci-fi underwater"]
VIDEO LENGTH: [e.g., "4 minutes"]
TEMPO (cpm): [e.g., "15 to 20 cycles per minute — very slow"]
KEY/SCALE: [e.g., "C minor" or "leave to your discretion"]
AVOID: [e.g., "drums, percussion, anything rhythmically regular"]
INCLUDE: [e.g., "at least 3 layered elements, reverb-heavy, slow filter movement"]

Rules:
- Use `setcpm()` to set tempo
- Use `stack()` to layer all patterns
- All patterns should use `.slow()` of at least 4
- Add `.room()` of 0.7 or above on all layers
- Use `.orbit()` to assign layers: 0 for main pad, 1 for drone, 2 for texture
- Output only the Strudel code block, no explanation
```

***

## Part 6: The Full Session Workflow

This is the step-by-step sequence to run for every recording session.

### Step 1 — Start SuperCollider

Open the SuperCollider IDE. The startup file runs automatically, booting the server and starting SuperDirt. Verify in the post window:

```
SuperDirt: listening to Tidal on port 57120
```

If this line does not appear, evaluate the startup block manually by selecting it all and pressing `Ctrl+Enter`.

### Step 2 — Start the OSC Bridge

In a terminal:

```bash
cd /path/to/strudel
pnpm run osc
```

### Step 3 — Open Strudel REPL

In a second terminal:

```bash
pnpm run dev
```

Open `http://localhost:4321` in your browser. Set the audio output to SuperDirt in settings.

### Step 4 — Test Connectivity

In the Strudel REPL, type and run:

```javascript
s("bd")
```

You should hear a kick drum through SuperCollider, not the browser. If no sound, check: (a) OSC bridge is running, (b) SuperDirt reports no errors, (c) Strudel output is set to OSC/SuperDirt.

### Step 5 — Paste and Iterate the Soundscape Pattern

Paste the AI-generated pattern into Strudel. Press `Ctrl+Enter` to evaluate. Listen critically. Common adjustments:

| Issue | Fix |
|---|---|
| Too busy / rhythmic | Increase `.slow()` multiplier on busy layers |
| Too thin / sparse | Add another `stack()` layer |
| Too dry | Increase `.room()` toward 1.0 and `.size()` toward 0.95 |
| Too muddy | Add `.lpf(800)` to cut highs; `.hpf(100)` to cut rumble |
| Volume uneven | Adjust `.gain()` per layer (pads: 0.4–0.6, textures: 0.2–0.35) |
| Loop feels too short | Increase overall `.slow()` or use `setcpm(15)` or lower |

### Step 6 — Prepare Recording Settings in SuperCollider

Before recording, set output quality:

```supercollider
s.recHeaderFormat = "WAV";
s.recSampleFormat = "int24";
```

Evaluate with `Ctrl+Enter`.

### Step 7 — Start Recording

In SuperCollider, evaluate:

```supercollider
s.record(
    path: "/Users/yourname/Desktop/video_soundscape_v1.wav",
    duration: 300  // set to your video length + 10 seconds padding
);
```

The post window shows `Recording: /path/to/file`. Recording is now active.

### Step 8 — Let It Run

Do not touch the pattern while recording unless intentional evolution is desired. The recording captures everything from `s.record` forward.

### Step 9 — Verify and Export

When the recording stops (automatically after `duration` seconds), the post window shows:

```
Recording stopped. Wrote N samples.
```

The file is at the path you specified. Open it in any audio editor (Audacity, Logic, Reaper) to trim, normalize, or adjust levels before dropping it into your video timeline.[^15]

***

## Part 7: Troubleshooting

| Symptom | Likely Cause | Fix |
|---|---|---|
| No sound in SuperCollider | Wrong audio device | `Language > Preferences > Audio`, select correct output device[^4] |
| SC post window shows "alloc failed" | Not enough memory | Increase `s.options.memSize` in startup file[^9] |
| SC post window shows "too many nodes" | Too many synth layers | Increase `s.options.maxNodes`; simplify pattern |
| OSC bridge exits immediately | Port conflict | Another process uses port 57120; stop it or run `pnpm run osc -- --port 57121` and update startup file accordingly[^14] |
| Strudel plays in browser but SC is silent | OSC output not selected | Check Strudel settings panel; ensure OSC/SuperDirt output is active |
| SuperDirt not found on boot | Installation path wrong | Evaluate `Quarks.gui` in SC to verify SuperDirt is installed and enabled |
| Recording is silent | `s.record` called before pattern plays | Add `0.5.wait` before `s.record` in a Routine, or use the GUI Record button |
| `.wav` file not recognized by video editor | Recorded as AIFF or 32-bit float | Set `s.recHeaderFormat = "WAV"` and `s.recSampleFormat = "int24"` before recording[^19] |
| Samples not loading | Wrong path or missing wildcard | Ensure path ends in `/*` and folder contains named subfolders, not loose WAV files[^13][^12] |

***

## Part 8: Output File Specifications

| Parameter | Recommended Value |
|---|---|
| Format | WAV (not AIFF) |
| Sample rate | 44100 Hz (SC default) or 48000 Hz (for video sync) |
| Bit depth | 24-bit (`int24`) |
| Channels | Stereo (2) for final mix; multi-channel for stems |
| Duration | Video length + 10s padding |
| Normalization | Normalize to -6 dBFS before video import |

To record at 48 kHz (preferred for video), add to your startup file before `s.reboot`:

```supercollider
s.options.sampleRate = 48000;
```

***

## Quick Reference Card

```
SESSION STARTUP CHECKLIST
──────────────────────────
□ 1. Open SuperCollider → startup file auto-runs SuperDirt
□ 2. Check post window: "SuperDirt: listening on port 57120"
□ 3. Terminal 1: cd strudel && pnpm run osc
□ 4. Terminal 2: cd strudel && pnpm run dev
□ 5. Browser → http://localhost:4321 → set output to SuperDirt
□ 6. Test: s("bd") → hear kick from SC, not browser
□ 7. Paste soundscape pattern → iterate
□ 8. SC: s.recHeaderFormat="WAV"; s.recSampleFormat="int24";
□ 9. SC: s.record(path:"~/Desktop/out.wav", duration:300);
□ 10. Wait for "Recording stopped." in SC post window
```

---

## References

1. [MIDI & OSC Strudel - GitHub Pages](https://urswilke.github.io/strudel/learn/input-output/) - The default audio output of Strudel uses the Web Audio API. It is also possible to use Strudel with ...

2. [SuperCollider / SuperDirt - Sardine Documentation](https://sardine.raphaelforment.fr/configuration/superdirt.html) - The SuperDirt repository is a good place to start, especially the hacks/ folder. It will teach you h...

3. [Recorder | SuperCollider 3.14.0 Help](https://doc.sccode.org/Classes/Recorder.html) - A Recorder allows you to write audio to harddisk, reading from a given bus and a certain number of c...

4. [Install SuperCollider - Renardo (code > music)](https://renardo.org/install/01-install-supercollider/) - Launch SuperCollider and make it work! If it does not work you may need to select the proper sound d...

5. [Deploying supercollider (sclang) standalone apps - scsynth](https://scsynth.org/t/deploying-supercollider-sclang-standalone-apps/4030) - SuperDirt depends on sc3plugins for extended functionality which is another hurdle. There are instal...

6. [Building SuperCollider (and plugins) on Mac M1 - Development](https://scsynth.org/t/building-supercollider-and-plugins-on-mac-m1/4626) - That sounds fine - but odds are, youve probably installed SuperCollider by downloading the prebuilt ...

7. [is copying sc3-plugins into supercollider's extensions folder ... - Reddit](https://www.reddit.com/r/TidalCycles/comments/qi8di9/is_copying_sc3plugins_into_supercolliders/) - I'm on a Linux machine using Ubuntu 20.04. To install sc3-plugins, I simplied downloaded and unzippe...

8. [GitHub - daslyfe/StrudelDirt: Super dirt fork intended to have feature ...](https://github.com/daslyfe/StrudelDirt) - If you want SuperDirt to start automatically, you can load it from the startup file. To do this, ope...

9. [with-superdirt [konduktiva]](https://konduktiva.org/doku.php?id=with-superdirt) - This tutorial will teach you how to use SuperDirt with Konduktiva. Installation instructions for Sup...

10. [Live Coding - Strudel Setup - Teaching](https://teaching.alptugan.com/Tutorials/Live-Coding---Strudel-Setup) - This tutorial showcases the installation of Strudel Live Coding tool on your local device. 1. Depend...

11. [Installation | STRUDEL Kit](https://strudel.science/strudel-kit/docs/getting-started/installation/) - STRUDEL Kit requires Node.js with npm to run the web applications you build. If you don't already ha...

12. [[TidalClub] Loading sample packs in SuperDirt - YouTube](https://www.youtube.com/watch?v=nzKjNlgOkTk) - Part of the TidalCycles online live coding course - https://club.tidalcycles.org/t/weeks-1-4-index/

13. [Custom Samples | Tidal Cycles](https://tidalcycles.org/docs/configuration/AudioSamples/audiosamples/) - Adding and using your own custom samples in Tidal Cycles is relatively easy. You don't actually add ...

14. [@strudel/osc - npm](https://npmjs.com/package/@strudel/osc) - By default it will use port 57120 for the osc client, which is what superdirt uses. You can change i...

15. [Recording in SuperCollider - GitHub](https://github.com/supercollider/supercollider/wiki/Recording-in-SuperCollider) - The timer for the "duration" argument waits for paused recordings. "duration" the length of the outp...

16. [SuperCollider Mini Tutorial: 1. Recording to an Audio File - YouTube](https://www.youtube.com/watch?v=HCRXImVxgxw) - Support these tutorials on Patreon for early access, shout-outs at the end of each video, and other ...

17. [Separate audio outputs - TidalCycles userbase](https://userbase.tidalcycles.org/Separate_audio_outputs.html) - ... record all the channels straight from supercollider into a single multichannel file. Have a look...

18. [Multichannel routing to Ableton via Soundflower - TidalCycles](https://forum.toplap.org/t/multichannel-routing-to-ableton-via-soundflower/398) - Routing in Windows is problematic so I decided to record as separet channels in Supercollider. I've ...

19. [Incorrect encoding of "WAV" recordings? - Questions - scsynth](https://scsynth.org/t/incorrect-encoding-of-wav-recordings/3390) - I've recorded some of my SuperCollider pieces as “WAV” files from SuperCollider. And those files are...

