import concurrent.futures
from dataclasses import dataclass
from dis import disco
import json
import logging
import multiprocessing
import os
import time
import warnings
from typing import Any

import essentia
from essentia.standard import (
    MonoLoader,
    TensorflowPredict2D,
    TensorflowPredictEffnetDiscogs,
    TensorflowPredictTempoCNN,
)
import numpy as np
import tensorflow as tf

from YT_DLP_wrapper import YT_DLP_wrapper, Query
# Suppress Essentia logs
essentia.log.infoActive = False
essentia.log.warningActive = False
essentia.log.errorActive = False

# Suppress TensorFlow logs
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'  # 0=all, 1=info, 2=warnings, 3=errors
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'  # Disable oneDNN optimizations logging # 0=all, 1=info, 2=warnings, 3=errors

tf.get_logger().setLevel('ERROR')

# Optional: Suppress warnings module

warnings.filterwarnings('ignore')

labelling_model_orchestrator = None


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

PB_STAGE_1: dict[str, str] = {
    "tempo_predictor": os.path.join(SCRIPT_DIR, "essentia_pb", "deeptemp-k16-3.pb"),
    "discogs_embeddings_extractor": os.path.join(SCRIPT_DIR, "essentia_pb", "discogs-effnet-bs64-1.pb"),
}
PB_STAGE_2: dict[str, str] = {
    "discogs_approach_predictor": os.path.join(SCRIPT_DIR, "essentia_pb", "approachability_2c-discogs-effnet-1.pb"),
    "discogs_engagement_predictor": os.path.join(SCRIPT_DIR, "essentia_pb", "engagement_2c-discogs-effnet-1.pb"),
    "discogs_danceability_predictor": os.path.join(SCRIPT_DIR, "essentia_pb", "danceability-discogs-effnet-1.pb"),
    "discogs_mood_acousticness_predictor": os.path.join(SCRIPT_DIR, "essentia_pb", "mood_acoustic-discogs-effnet-1.pb"),
    "discogs_mood_agressiveness_predictor": os.path.join(SCRIPT_DIR, "essentia_pb", "mood_aggressive-discogs-effnet-1.pb"),
    "discogs_mood_electronicness_predictor": os.path.join(SCRIPT_DIR, "essentia_pb", "mood_electronic-discogs-effnet-1.pb"),
    "discogs_mood_happy_predictor": os.path.join(SCRIPT_DIR, "essentia_pb", "mood_happy-discogs-effnet-1.pb"),
    "discogs_mood_relaxed_predictor": os.path.join(SCRIPT_DIR, "essentia_pb", "mood_relaxed-discogs-effnet-1.pb"),
    "discogs_mood_sad_predictor": os.path.join(SCRIPT_DIR, "essentia_pb", "mood_sad-discogs-effnet-1.pb"),
    "discogs_mood_party_predictor": os.path.join(SCRIPT_DIR, "essentia_pb", "mood_party-discogs-effnet-1.pb")
}

PB_STRAT: dict[int, dict[str, str]] = {
    1: PB_STAGE_1,
    2: PB_STAGE_2,
}

@dataclass
class SongRow:
    id: int = -1
    mix_id: int = -1
    path: str = ""
    audio: Any = None
    

@dataclass
def ModelLabellingOrchestrator(object):
    batch_size: int = 10
    
    __downloader: YT_DLP_wrapper = None
    __pb_strat: dict[str, dict[str, str]] = PB_STRAT
    
    __song_pipeline: list[SongRow] = []
    
    def __post_init__(self):
        # Initialize YT_DLP_wrapper
        if self.__downloader is None:
            self.__downloader = YT_DLP_wrapper(max_simultaneous_downloads=self.max_simultaneous_downloads)
            
    def pipeline_phase_1(self, downloaded_songs: list[SongRow]):
        if len(downloaded_songs) == 0:
            return

    def pipeline_phase_2(self, downloaded_songs: list[SongRow]):
        if len(downloaded_songs) == 0:
            return

    
    def process_batch(self):
        # downloa songs
        downloaded_songs = []
        
        # process songs
        self.pipeline_phase_1(downloaded_songs)
        self.pipeline_phase_2(downloaded_songs)
        pass