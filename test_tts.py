import torch
from TTS.api import TTS
from Models.TTS.MultiSegmentListDeser import MultiSegmentListDeser
import os
import torchaudio

OUTPUT_PATH = "output_fastpitch.wav"

EMOTIONS = {
    "angry": "ref_voices/angry_60.wav",
    "happy": "ref_voices/happy_80.wav",
    "sad": "ref_voices/sad_80.wav",
    "neutral": "ref_voices/happy_0.wav",
    "surprise": "ref_voices/surprise_80.wav",
}

wms = MultiSegmentListDeser.from_file(os.path.join("_samples", "tts_radio_samples", "01_watermelonSugar2Espresso.json"))

# Patch torch.load to use weights_only=False for TTS compatibility
original_torch_load = torch.load

def patched_torch_load(*args, **kwargs):
    kwargs['weights_only'] = False
    return original_torch_load(*args, **kwargs)

torch.load = patched_torch_load

tts = TTS(model_name="tts_models/multilingual/multi-dataset/xtts_v2")

clips = []
for i, segment in enumerate(wms.segments):
    file_path = f".outputs/segment_{i}.wav"
    tts.tts_to_file(
        text=segment.text,
        speaker_wav=EMOTIONS[segment.tone],
        language="en",
        file_path=file_path
    )
    waveform, sr = torchaudio.load(file_path)
    clips.append(waveform)

# Concatenate audio
combined = torch.cat(clips, dim=1)
torchaudio.save("final_mix.wav", combined, sample_rate=sr)