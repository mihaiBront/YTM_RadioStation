#!/usr/bin/env python3
"""
Debug script to check model input/output dimensions
"""

import numpy as np
from essentia.standard import TensorflowPredictEffnetDiscogs, TensorflowPredict2D

# Test audio (1 second of silence at 16kHz)
test_audio = np.zeros(16000, dtype=np.float32)

print("=== Testing Embedding Extractor ===")
try:
    embeddings_extractor = TensorflowPredictEffnetDiscogs(
        graphFilename="dataset_enhancing_models/essentia_pb/discogs-effnet-bs64-1.pb")
    embeddings = embeddings_extractor(test_audio)
    print(f"Embeddings shape: {embeddings.shape}")
    print(f"Embeddings type: {type(embeddings)}")
    print(f"Sample values: {embeddings.flatten()[:5]}")
except Exception as e:
    print(f"Error with embeddings extractor: {e}")

print("\n=== Testing Approachability Predictor Input Expectations ===")
try:
    # Try with different embedding dimensions to see what works
    approach_predictor = TensorflowPredict2D(
        graphFilename="dataset_enhancing_models/essentia_pb/approachability_2c-discogs-effnet-1.pb", 
        output="model/Softmax")
    
    # Test with 400-dim embeddings (current output)
    print("Testing with 400-dimensional embeddings...")
    fake_embeddings_400 = np.random.random((64, 400)).astype(np.float32)
    try:
        result = approach_predictor(fake_embeddings_400)
        print(f"✓ 400-dim works! Result shape: {result.shape}")
    except Exception as e:
        print(f"✗ 400-dim failed: {e}")
    
    # Test with 1280-dim embeddings (expected by error message)
    print("Testing with 1280-dimensional embeddings...")
    fake_embeddings_1280 = np.random.random((64, 1280)).astype(np.float32)
    try:
        result = approach_predictor(fake_embeddings_1280)
        print(f"✓ 1280-dim works! Result shape: {result.shape}")
    except Exception as e:
        print(f"✗ 1280-dim failed: {e}")
        
    # Test with the actual embeddings from the extractor
    if 'embeddings' in locals():
        print(f"Testing with actual embeddings (shape: {embeddings.shape})...")
        try:
            result = approach_predictor(embeddings)
            print(f"✓ Actual embeddings work! Result shape: {result.shape}")
        except Exception as e:
            print(f"✗ Actual embeddings failed: {e}")
            
except Exception as e:
    print(f"Error loading approachability predictor: {e}")

print("\n=== Available Models ===")
import os
pb_files = [f for f in os.listdir("dataset_enhancing_models/essentia_pb/") if f.endswith('.pb')]
discogs_models = [f for f in pb_files if 'discogs' in f]
print("Discogs models available:")
for model in sorted(discogs_models):
    print(f"  - {model}")
