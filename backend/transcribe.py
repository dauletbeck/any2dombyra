#!/usr/bin/env python3
"""transcribe.py – robust Basic‑Pitch wrapper

Turn **any audio file** (wav | mp3 | flac | ogg …) into:
    • <input>.mid   – standard MIDI file
    • <input>.notes.json – flat note list (start, end, pitch, name)

The script copes with *all* known Basic‑Pitch return formats (tuple, list, dict)
across versions 0.2 → 1.x, so you don’t have to care which wheel is installed.

──────────────────────────────  Setup  ──────────────────────────────
(conda) $ conda create -n dombyra python=3.11 -y && conda activate dombyra
(conda) $ conda install -c conda-forge pretty_midi pysoundfile tqdm ffmpeg
(conda) $ conda install -c pytorch pytorch torchaudio cpuonly          # GPU? add cudatoolkit=<ver>
(conda) $ pip install basic-pitch   # not yet on conda‑forge

──────────────────────────────  Usage  ──────────────────────────────
(dombyra) $ python transcribe.py audio.wav [--midi out.mid] [--json out.json]

First run downloads the model (~30 s); afterwards it’s instant.
"""
from __future__ import annotations

import argparse
import io
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Sequence

import pretty_midi
from basic_pitch.inference import predict

def audio_to_midi(audio_path: str | Path) -> pretty_midi.PrettyMIDI:
    """
    Run Basic-Pitch on *audio_path* and return a PrettyMIDI object.
    """
    bp_out = predict(str(audio_path))          # may return tuple or dict
    pm = _find_pretty_midi(bp_out)             # you already have this helper
    if pm is None:
        raise RuntimeError("Basic-Pitch returned no MIDI data")
    return pm

###############################################################################
# Helpers                                                                     #
###############################################################################

def _find_pretty_midi(obj: Any) -> pretty_midi.PrettyMIDI | None:
    """Return a PrettyMIDI from *obj* if possible, else None.

    Handles:
      • PrettyMIDI instance → itself
      • dict → keys [pretty_midi | pm | midi]
      • bytes→ MIDI, str path→ MIDI, Path→ MIDI
      • tuple/list → search elements recursively
    """
    # direct hit ----------------------------------------------------------------
    if isinstance(obj, pretty_midi.PrettyMIDI):
        return obj

    # dict variants -------------------------------------------------------------
    if isinstance(obj, Dict):
        for k in ("pretty_midi", "pm"):
            if k in obj:
                return _find_pretty_midi(obj[k])
        if "midi" in obj:
            val = obj["midi"]
            if isinstance(val, (bytes, bytearray)):
                return pretty_midi.PrettyMIDI(io.BytesIO(val))
            if isinstance(val, (str, Path)) and Path(val).exists():
                return pretty_midi.PrettyMIDI(val)

    # tuple / list --------------------------------------------------------------
    if isinstance(obj, Sequence) and not isinstance(obj, (str, bytes, bytearray)):
        for item in obj:
            pm = _find_pretty_midi(item)
            if pm is not None:
                return pm

    return None


def _note_list(pm: pretty_midi.PrettyMIDI) -> List[Dict[str, Any]]:
    """Flatten all tracks to JSON‑serialisable dicts, sorted by start."""
    events: List[Dict[str, Any]] = []
    for inst in pm.instruments:
        for n in inst.notes:
            events.append(
                {
                    "instrument": inst.name or "unknown",
                    "start": float(round(n.start, 4)),
                    "end": float(round(n.end, 4)),
                    "pitch": int(n.pitch),  # ensure native int, not numpy int64
                    "name": pretty_midi.note_number_to_name(int(n.pitch)),
                }
            )
    return sorted(events, key=lambda e: e["start"])

###############################################################################
# CLI                                                                         #
###############################################################################

def _parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="Transcribe audio to MIDI + JSON using Spotify Basic‑Pitch",
    )
    ap.add_argument("audio", type=Path, help="Input audio file")
    ap.add_argument("--midi", type=Path, help="Output .mid path (default <audio>.mid)")
    ap.add_argument("--json", type=Path, help="Output .json path (default <audio>.notes.json)")
    return ap.parse_args()


def main() -> None:
    args = _parse_args()
    audio_path = args.audio.expanduser().resolve()
    if not audio_path.exists():
        sys.exit(f"[❌] File not found: {audio_path}")

    midi_out = (args.midi or audio_path.with_suffix(".mid")).expanduser().resolve()
    json_out = (args.json or audio_path.with_suffix(".notes.json")).expanduser().resolve()

    print("🎧  Loading  :", audio_path)
    print("🎶  Running Basic‑Pitch (first run downloads model)…")
    bp_result = predict(str(audio_path))
    pm = _find_pretty_midi(bp_result)
    if pm is None:
        sys.exit("[❌] Couldn’t locate PrettyMIDI in Basic‑Pitch output – please update script.")

    print("💾  MIDI  →", midi_out)
    pm.write(str(midi_out))

    print("💾  JSON →", json_out)
    json_out.write_text(json.dumps(_note_list(pm), indent=2), encoding="utf‑8")

    print("✅  Done.  Open the .mid in MuseScore or inspect the JSON for debugging.")


if __name__ == "__main__":
    main()
