# Quick Start — Get Audio in 15 Minutes

This guide gets you from zero to a rendered Dr. Who-inspired soundscape WAV.
The `.scd` render path does **not** require pnpm or Strudel.

---

## Step 1 — Install SuperCollider

```bash
brew install --cask supercollider   # macOS (Homebrew)
# or download from https://supercollider.github.io/downloads
```

Verify:

```bash
/Applications/SuperCollider.app/Contents/MacOS/sclang --version
# SuperCollider 3.14.x (...)
```

`strudel-gen` finds sclang inside the app bundle automatically — **no symlink needed**.
If you want it on your shell `PATH` for convenience:

```bash
mkdir -p ~/.local/bin
ln -sf /Applications/SuperCollider.app/Contents/MacOS/sclang ~/.local/bin/sclang
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

## Step 2 — Install sc3-plugins

Open SuperCollider IDE (scide / SuperCollider.app). In the editor pane, evaluate:

```supercollider
Quarks.checkForUpdates({
    Quarks.install("SuperDirt", "v1.7.2");
    thisProcess.recompile()
})
```

Wait for the post window to show `SuperDirt installed` and recompile. Also install sc3-plugins:

```bash
brew install sc3-plugins   # macOS
# or follow https://supercollider.github.io/sc3-plugins
```

## Step 3 — Copy the startup file

```bash
# Find SC's startup file location — evaluate this in SC IDE:
#   Platform.userAppSupportDir
# Then copy:
cp src/supercollider/startup.scd \
  ~/Library/Application\ Support/SuperCollider/startup.scd   # macOS
```

From now on SuperDirt starts automatically every time SuperCollider boots.

## Step 4 — Install this project

```bash
cd /path/to/strudel-gen
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

## Step 5 — Verify prerequisites

```bash
make doctor
# or: strudel-gen doctor --verbose
```

For the .scd render path, only `sclang` is required. `pnpm` and the Strudel
clone are only needed for the live-REPL path (see docs/guide.md §6).

---

## Get the Dr. Who soundscape

```bash
make dr-who
```

This runs:

```bash
strudel-gen render \
  --pattern src/supercollider/dr-who-render.scd \
  --duration 120 \
  --out ~/Desktop/dr-who-soundscape.wav
```

What happens:

1. `sclang` boots its own audio server
2. Three SynthDefs load: `dwBass` (sweeping sawtooth), `dwLead` (vibrato sine),
   `dwTexture` (harmonic shimmer)
3. The E-minor Dr. Who bass figure (E D E D E D C D) plays at 1.8 s/step
4. The theremin lead (B D E D B E G A) enters on every other beat
5. FreeVerb + CombC delay create the deep-space reverb tail
6. After 120 s + 5 s reverb tail, recording stops and sclang exits
7. `ffmpeg` normalises to −6 dBFS (if installed)
8. WAV lands at `~/Desktop/dr-who-soundscape.wav`

Open the WAV in QuickTime, VLC, or any audio editor.

---

## Using the Strudel REPL (manual / live session)

To use the full Strudel → SuperDirt pipeline (live-coded session with visual
feedback and real-time editing):

1. Install pnpm: `npm install -g pnpm`
2. Clone Strudel: `git clone https://github.com/tidalcycles/strudel ~/devel/strudel`
3. `cd ~/devel/strudel && git checkout 8a8ae9ac9659 && pnpm install`
4. `make doctor` — should now show 4 ✓
5. Open two terminals:
   - Terminal 1: `make bridge` (or `scripts/bridge.sh`)
   - Terminal 2: `make repl` (or `scripts/repl.sh`)
6. Open `http://localhost:4321` → set audio output to SuperDirt
7. Paste `src/patterns/dr-who-inspired.js` → press Ctrl+Enter to play
8. In SC IDE, run the recording snippet from `src/supercollider/record.scd`

See [docs/guide.md](guide.md) for the complete workflow.
