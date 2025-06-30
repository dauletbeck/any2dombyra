from fastapi import FastAPI, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import tempfile, shutil, uuid, json

from backend.transcribe import audio_to_midi, _note_list   # reuse helpers
from backend.fingering import map_midi_to_dombyra

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # dev only – tighten later
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/api/transcribe")
async def transcribe(file: UploadFile):
    # 1) save upload to a temp file
    tmp_audio = Path(tempfile.gettempdir()) / f"{uuid.uuid4()}{Path(file.filename).suffix}"
    with tmp_audio.open("wb") as f:
        shutil.copyfileobj(file.file, f)

    # 2) run Basic Pitch → MIDI
    midi_path = tmp_audio.with_suffix(".mid")
    pm = audio_to_midi(tmp_audio)
    pm.write(str(midi_path))

    # 3) fingering
    fingering = map_midi_to_dombyra(midi_path)

    # 4) send everything back
    return {
        "fingering": fingering,
        # optional: "notes": _note_list(pm)
    }
