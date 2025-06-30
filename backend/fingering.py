#!/usr/bin/env python3
"""fingering.py – map MIDI notes to dombyra fret positions

✔ Works with NumPy ≥ 2.0 (adds missing `np.int` / `np.float` aliases).

CLI usage
~~~~~~~~~
    python fingering.py song.mid               # prints CSV
    python fingering.py song.mid --json-out song.fingering.json

API usage
~~~~~~~~~
    from fingering import map_midi_to_dombyra
    positions = map_midi_to_dombyra("song.mid")
    # → [(start, end, string_index, fret), ...]
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# 🔧 Hot‑patch NumPy 2.0 deprecations so pretty_midi keeps working
# ---------------------------------------------------------------------------
import numpy as _np
for _alias, _actual in {"int": int, "float": float}.items():
    if not hasattr(_np, _alias):
        setattr(_np, _alias, _actual)

# ---------------------------------------------------------------------------
import argparse
import json
from pathlib import Path
from typing import Any, List, Tuple

import pretty_midi  # must come *after* NumPy patch

# ---------------------------------------------------------------------------
# Dombyra config
# ---------------------------------------------------------------------------
TUNING = [45, 62]  # MIDI numbers of open strings: A2 (45) and d3 (62)
NUM_FRETS = 19

# ---------------------------------------------------------------------------
# Core mapping logic
# ---------------------------------------------------------------------------

def _candidate_frets(pitch: int) -> List[Tuple[int, int]]:
    """Return all (string_index, fret) that can play *pitch*."""
    cands: List[Tuple[int, int]] = []
    for s, open_note in enumerate(TUNING):
        fret = pitch - open_note
        if 0 <= fret <= NUM_FRETS:
            cands.append((s, fret))
    return cands


def map_midi_to_dombyra(midi_path: str | Path) -> List[Tuple[float, float, int, int]]:
    """Return [(start, end, string, fret), …] for the first MIDI track."""
    pm = pretty_midi.PrettyMIDI(str(midi_path))
    if not pm.instruments:
        raise ValueError("No instruments in MIDI file")

    notes = sorted(pm.instruments[0].notes, key=lambda n: n.start)
    result: List[Tuple[float, float, int, int]] = []
    last_fret = 0

    for n in notes:
        cands = _candidate_frets(n.pitch)
        # octave rescue
        if not cands:
            for shift in (-12, 12):
                cands = _candidate_frets(n.pitch + shift)
                if cands:
                    break
        if not cands:
            raise ValueError(f"Note {n.pitch} not playable even after octave shift")

        best_s, best_f = min(cands, key=lambda sf: abs(sf[1] - last_fret))
        result.append((round(float(n.start), 4), round(float(n.end), 4), best_s, best_f))
        last_fret = best_f

    return result

# ---------------------------------------------------------------------------
# CLI helpers
# ---------------------------------------------------------------------------

def _print_csv(rows: List[Tuple[Any, ...]]):
    print("start,end,string,fret")
    for r in rows:
        print(f"{r[0]},{r[1]},{r[2]},{r[3]}")


def _parse_args():
    p = argparse.ArgumentParser(description="Map MIDI notes to dombyra fingering")
    p.add_argument("midi", type=Path, help="Input MIDI file (.mid)")
    p.add_argument("--json-out", type=Path, help="Save fingering to JSON file")
    return p.parse_args()


def main() -> None:
    args = _parse_args()
    rows = map_midi_to_dombyra(args.midi)
    if args.json_out:
        args.json_out.write_text(json.dumps(rows, indent=2), encoding="utf-8")
        print("✔ Fingering JSON saved →", args.json_out)
    else:
        _print_csv(rows)


if __name__ == "__main__":
    main()
