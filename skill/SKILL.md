---
name: ambient-render
description: |
  Use this skill when the user asks for ambient background music,
  a soundscape for a video, generative drone audio, or a sci-fi /
  underwater / forest / etc. audio bed. Produces a rendered WAV file
  on the user's machine. Triggers on phrases like
  "background music for", "ambient soundscape", "drone audio",
  "make a soundtrack", "underwater ambience", "forest atmosphere",
  "space drone", "make me something dark and cinematic".
  Do NOT use for vocal music, songs with lyrics, pop tracks, beat-driven
  EDM, or any request that names a copyrighted artist or requests a
  specific song/theme from an existing work.
allowed-tools: Bash
---

# ambient-render

You are about to produce a rendered ambient soundscape WAV file by writing
a short Strudel `.js` pattern and running the project's render pipeline.

## Inputs you need (ask if missing)

- **Mood description**: 1-2 sentences ("cold underwater", "alien forest at dawn").
- **Duration**: seconds. Default 120 if unspecified.
- **Output path**: default `~/Desktop/<mood-slug>.wav`.

## Steps

1. Generate a slug from the mood (kebab-case, ≤ 32 chars). Call it `<slug>`.
2. Write a Strudel `.js` file to `src/patterns/<slug>.js` following the
   conventions in CLAUDE.md and the templates in docs/redesign-tidal.md §6.
3. Run:

       strudel-gen render \
         --engine tidal \
         --pattern src/patterns/<slug>.js \
         --duration <seconds> \
         --out <output_path>

4. Report the output paths back to the user.

## Constraints (binding)

- Use only Strudel methods listed in §4 of the cheat sheet (docs/redesign-tidal.md).
- Every layer must have `.slow(>=4)` and `.room(>=0.7)`.
- Use `.orbit(N)` for layer separation, N ∈ {0..5}.
- No arrow-function modifiers beyond single-call: `x => x.<method>(<args>)`.
