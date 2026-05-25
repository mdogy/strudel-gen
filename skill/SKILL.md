---
name: ambient-render
description: >-
  Generate ambient background music, soundscape audio, or atmospheric drone audio
  for videos, games, or meditation. Triggers when user asks for background music,
  ambient audio, a soundscape, atmospheric drone, or environmental audio.
Allowed-Tools: Bash
---

# ambient-render

Generate ambient soundscape WAV files via **Strudel** (JS patterns) → **SuperDirt** (SuperCollider audio engine) → **Recorder**.

## When this skill fires

The description above is the trigger. It fires when a user asks for:

- "background music for a video"
- "ambient soundscape"
- "atmospheric drone audio"
- "soundtrack for a [mood] scene"
- "environmental audio for a game"

## Requirements

- SuperCollider (with sc3-plugins + SuperDirt)
- Node.js + pnpm
- A local Strudel clone (pinned to `8a8ae9ac9659`)
- ffmpeg (optional, for normalization)

## Usage

```bash
# Check prerequisites
cd /path/to/strudel-gen && make doctor

# Full render: boot SC, start bridge, record, normalize
make render ARGS="--mood 'cold underwater drone' --duration 240 --out ~/Desktop/soundscape.wav"

# Boot and teardown without rendering (test the pipeline)
make session ARGS="--dry-run --duration 5"

# Render a pattern spec JSON to a .js file
make render-pattern ARGS="--spec spec.json --out pattern.js"
```

## How it works

1. **Doctor** — detects `sclang`, `node`, `pnpm`, Strudel clone on the system
2. **SCManager** — boots SuperCollider with the project startup file, waits for SuperDirt ready
3. **BridgeManager** — starts the Strudel OSC bridge (`pnpm run osc`)
4. **RecorderScript** — generates a SuperCollider Routine that records to WAV at 24-bit
5. **Normalize** — post-processes with ffmpeg loudnorm to −6 dBFS
6. **Sidecar** — `.loudness.json` written alongside the WAV with measured metrics

## Output

- 24-bit WAV, 48 kHz, stereo (default)
- Sidecar `*.loudness.json` with integrated loudness, true peak, LRA
- Normalized to −6 dBFS integrated loudness

## Troubleshooting

Run `make doctor` first. If prerequisites are missing, run with `--verbose` for platform-specific install hints.
