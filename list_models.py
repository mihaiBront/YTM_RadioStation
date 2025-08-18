import torch
from TTS.api import TTS

# Patch torch.load to use weights_only=False for TTS compatibility
original_torch_load = torch.load

def patched_torch_load(f, map_location=None, pickle_module=None, **kwargs):
    # Force weights_only=False for TTS model loading
    kwargs['weights_only'] = False
    return original_torch_load(f, map_location=map_location, pickle_module=pickle_module, **kwargs)

# Apply the patch
torch.load = patched_torch_load

# Get available models
tts = TTS(model_name="tts_models/en/ljspeech/fast_pitch")
model_manager = tts.list_models()

print("All available TTS models:")
print("=" * 50)

# Get the list of models from the model manager
models = model_manager.list_models()

# Print all models and look for emotion-related ones
emotion_models = []
for model in models:
    print(model)
    if 'emotion' in model.lower() or 'fastspeech' in model.lower():
        emotion_models.append(model)

print("\n" + "=" * 50)
print("Emotion/FastSpeech related models:")
print("=" * 50)
for model in emotion_models:
    print(f"✅ {model}") 