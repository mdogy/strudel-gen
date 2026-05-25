# Skill Usage Guide

## Example 1: Quick ambient drone for a meditation video

**User:** "Create 3 minutes of calm ambient drone for a meditation video"

**Session (Claude Code invoking ambient-render):**

```bash
cd /path/to/strudel-gen

# Check prerequisites
make doctor

# Render 3-minute drone
make render ARGS="--mood 'calm meditation drone, soft pads, slow evolving' --duration 180 --out ~/Desktop/meditation-drone.wav"
```

**Output:** `~/Desktop/meditation-drone.wav` (24-bit, normalized to −6 dBFS)  
**Sidecar:** `~/Desktop/meditation-drone.loudness.json`

---

## Example 2: Sci-fi underwater for a video intro

**User:** "I need 30 seconds of mysterious sci-fi underwater ambience"

**Session:**

```bash
make render ARGS="--mood 'mysterious sci-fi underwater, deep drones, bubbling textures' --duration 30 --out ~/Desktop/sci-fi-underwater.wav"
```

**Output:** `~/Desktop/sci-fi-underwater.wav`

---

## Example 3: Dry-run test of the pipeline

**User:** "Test that the pipeline works without actually recording"

**Session:**

```bash
make session ARGS="--dry-run --duration 5"
```

This boots SuperCollider + the OSC bridge, waits 5 seconds, then tears down. If it completes without errors, the pipeline is ready.

---

## Example 4: Custom pattern spec

**User:** "Render a drone with a specific pattern JSON"

**Session:**

```bash
make render ARGS="render-pattern --spec my-pattern.json --out my-pattern.js"
```

Then edit `my-pattern.js` as needed before the full render.

---

## Example 5: Full production render (4 minutes)

**User:** "Generate 4 minutes of cold wind soundscape"

**Session:**

```bash
make render ARGS="--mood 'cold wind, arctic atmosphere, icy drones' --duration 240 --out ~/Desktop/cold-wind.wav --timeout-sc 120"
```

The extended `--timeout-sc` gives SuperCollider more time to boot with large sample libraries.
