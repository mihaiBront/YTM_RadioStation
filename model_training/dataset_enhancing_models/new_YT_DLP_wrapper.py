#region imports
import yt_dlp
import essentia
import tensorflow as tf
import warnings
from essentia.standard import MonoLoader
import os
import logging as log
import random
import concurrent.futures
from dataclasses import dataclass, field
import logging
import os
import warnings
from typing import Any
import pandas as pd
import gc

import essentia
from essentia.standard import (
    MonoLoader,
    TensorflowPredict2D,
    TensorflowPredictEffnetDiscogs,
    TensorflowPredictTempoCNN,
)
import numpy as np
import tensorflow as tf
from contextlib import contextmanager
#endregion

#region suppress logs
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
#endregion

#region constants
OUT_DIR = "temp/"
EXTENSION = "wav"
QUALITY = "192"
YT_DLP_OPTS = {
    "format": "bestaudio/best",
    "noplaylist": True,
    "quiet": True,
    "outtmpl": None,  # we will handle the temp file
    "default_search": "ytsearch1",
    "postprocessors": [{
        "key": "FFmpegExtractAudio",
        "preferredcodec": EXTENSION,
        "preferredquality": QUALITY,
    }]
}
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
#endregion

@contextmanager
def gpu_model(model: Any):
    try: 
        yield model
    finally:
        del model
        tf.keras.backend.clear_session()
        gc.collect()

#region classes
@dataclass
class YT_DLP_wrapper(object):
    max_simultaneous_downloads: int = field(default=10)
    
    @staticmethod
    def generate_file_name(song_name: str, song_author: str) -> str:
        return f"{song_name}_{song_author}_{random.getrandbits(64):016x}"
    
    @staticmethod
    def generate_query(song_name: str, song_author: str) -> str:
        return f"{song_name} {song_author} audio"
    
    @classmethod
    def download_single_query(cls, song_row: dict[str, Any]) -> dict[str, Any]:
        f_name = cls.generate_file_name(song_row["track_title"], song_row["track_artist"])
        query = cls.generate_query(song_row["track_title"], song_row["track_artist"])
        info = {}
        
        local_opts = YT_DLP_OPTS["outtmpl"].copy()
        local_opts["outtmpl"] = f_name
        
        with yt_dlp.YoutubeDL(local_opts) as ydl:
            info = ydl.extract_info(query, download=True)
        audio = MonoLoader(
            filename=f"{f_name}.{EXTENSION}",
            sampleRate=11025,
            resampleQuality=4
        )()
        os.remove(f"{f_name}.{EXTENSION}")
        
        song_row["_ytdlp_audio"] = audio
        
        entrydata = info.get("entries", [{}])[0]
        song_row["track_viewcount"] = entrydata.get("view_count", None)
        song_row["track_commentCount"] = entrydata.get("comment_count", None)
        song_row["like_count"] = entrydata.get("like_count", None)
        song_row["track_avRating"] = entrydata.get("average_rating", None)
        
        return song_row
        
    def batch_download(self, song_batch: list[dict[str, Any]]) -> list[dict[str, Any]]:
        with concurrent.futures.ProcessPoolExecutor(
            max_workers=self.max_simultaneous_downloads
        ) as process_pool:
            futures = {
                i: process_pool.submit(self.download_single_query, song_batch[i])
                for i in range(len(song_batch))
            }
            results = []
            for future in concurrent.futures.as_completed(futures.values()):
                try:
                    result = future.result()
                    if result is not None:
                        results.append(result)
                except Exception as e:
                    log.error(f"Error processing query: {e}")
            return results

@dataclass
class MLLabellingWrapper(object):
    input_dataframe: pd.DataFrame = field(default=None)
    output_dataframe: str = field(default="")
    max_simultaneous_downloads: int = field(default=10)
    batch_size: int = field(default=10)
    
    __current_song_batch: list[dict[str, Any]] = field(default=[])
    __next_song_batch: list[dict[str, Any]] = field(default=[])
    __downloader: YT_DLP_wrapper = field(default=None)
    
    def __post_init__(self):
        self.__downloader = YT_DLP_wrapper(max_simultaneous_downloads=self.max_simultaneous_downloads)
    
    def pipeline_phase_1(self, song_batch: list[dict[str, Any]]):
        if len(song_batch) == 0:
            return
        
        strat_steps = PB_STRAT[1]
        
        with gpu_model(TensorflowPredictEffnetDiscogs(
            graphFilename=strat_steps["discogs_embeddings_extractor"], 
            output="PartitionedCall:1"
            )) as embeddings_extractor:
            for song in song_batch[:]:
                song["_ml_embeddings"] = embeddings_extractor(song["_ytdlp_audio"])
        
        with gpu_model(TensorflowPredictTempoCNN(
            graphFilename=strat_steps["tempo_predictor"]
            )) as bpm_predictor:
            for song in song_batch[:]:
                song["bpm"] = bpm_predictor(song["_ytdlp_audio"])
                song.pop("_ytdlp_audio") # remove since we don't need it anymore

    def pipeline_phase_2(self, song_batch: list[dict[str, Any]]):
        if len(song_batch) == 0:
            return
        
        strat_steps = PB_STRAT[2]
        
        with gpu_model(TensorflowPredict2D(
            graphFilename=strat_steps["discogs_approach_predictor"], output="model/Softmax")
            ) as approachability_predictor:
            for song in song_batch[:]:
                song["approachability"] = approachability_predictor(song["_ml_embeddings"])
        
        with gpu_model(TensorflowPredict2D(
            graphFilename=strat_steps["discogs_engagement_predictor"], output="model/Softmax")
            ) as engagement_predictor:
            for song in song_batch[:]:
                song["engagement"] = engagement_predictor(song["_ml_embeddings"])
        
        with gpu_model(TensorflowPredict2D(
            graphFilename=strat_steps["discogs_danceability_predictor"], output="model/Softmax")
            ) as danceability_predictor:
            for song in song_batch[:]:
                song["danceability"] = danceability_predictor(song["_ml_embeddings"])
        
        with gpu_model(TensorflowPredict2D(
            graphFilename=strat_steps["discogs_mood_acousticness_predictor"], output="model/Softmax")
            ) as acousticness_predictor:
            for song in song_batch[:]:
                song["acousticness"] = acousticness_predictor(song["_ml_embeddings"])
                
        with gpu_model(TensorflowPredict2D(
            graphFilename=strat_steps["discogs_mood_agressiveness_predictor"], output="model/Softmax")
            ) as agressiveness_predictor:
            for song in song_batch[:]:
                song["agressiveness"] = agressiveness_predictor(song["_ml_embeddings"])
                
        with gpu_model(TensorflowPredict2D(
            graphFilename=strat_steps["discogs_mood_electronicness_predictor"], output="model/Softmax")
            ) as electronicness_predictor:
            for song in song_batch[:]:
                song["electronicness"] = electronicness_predictor(song["_ml_embeddings"])
                
        with gpu_model(TensorflowPredict2D(
            graphFilename=strat_steps["discogs_mood_happy_predictor"], output="model/Softmax")
            ) as happy_predictor:
            for song in song_batch[:]:
                song["happy"] = happy_predictor(song["_ml_embeddings"])
            
        with gpu_model(TensorflowPredict2D(
            graphFilename=strat_steps["discogs_mood_party_predictor"], output="model/Softmax")
            ) as party_predictor:
            for song in song_batch[:]:
                song["party"] = party_predictor(song["_ml_embeddings"])
                
        with gpu_model(TensorflowPredict2D(
            graphFilename=strat_steps["discogs_mood_relaxed_predictor"], output="model/Softmax")
            ) as relaxed_predictor:
            for song in song_batch[:]:
                song["relaxed"] = relaxed_predictor(song["_ml_embeddings"])
                
        with gpu_model(TensorflowPredict2D(
            graphFilename=strat_steps["discogs_mood_sad_predictor"], output="model/Softmax")
            ) as sad_predictor:
            for song in song_batch[:]:
                song["sad"] = sad_predictor(song["_ml_embeddings"])
                
        song.pop("_ml_embeddings")
                
    def process_batch(self):
        self.pipeline_phase_1(self.__current_song_batch)
        self.pipeline_phase_2(self.__current_song_batch)
    
    def append_to_output_dataframe(self):
        include_header = not os.path.exists(self.output_dataframe) or os.path.getsize(self.output_dataframe) == 0
        
        pd.DataFrame(self.__current_song_batch).to_csv(
            self.output_dataframe, mode='a', header=False, index=False)
    
    def create_output_dataframe(self):
        if os.path.exists(self.output_dataframe):
            os.remove(self.output_dataframe)
        with open(self.output_dataframe, 'w') as f:
            f.write('')
        
    def pipeline_orchestrator(self):
        self.create_output_dataframe()
        
        # download first batch
        self.__next_song_batch = self.__downloader.batch_download(self.dataframe.iloc[0:self.batch_size].to_dict()) #TODO: out of bounds
        for i in range(0, len(self.dataframe), self.batch_size):
            self.__current_song_batch = self.__next_song_batch
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                next_batch_future = executor.submit(
                    self.__downloader.batch_download,
                    self.dataframe.iloc[i:i+self.batch_size].to_dict(orient="records") #TODO: out of bounds
                )
                executor.submit(
                    self.process_batch
                )
                
                self.__next_song_batch = next_batch_future.result()
                self.append_to_output_dataframe()
#endregion

if __name__ == "__main__":
    df = pd.read_csv("data/train_data.csv")
    d = MLLabellingWrapper(input_dataframe=df, max_simultaneous_downloads=10, batch_size=10)
    d.pipeline_orchestrator()