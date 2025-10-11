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
import json
import shutil

import essentia
from essentia.standard import (
    MonoLoader,
    TensorflowPredict2D,
    TensorflowPredictEffnetDiscogs,
    TensorflowPredictTempoCNN,
)
import numpy as np
import tensorflow as tf
from tensorflow.python.framework.ops import reset_default_graph
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

logger = log.getLogger(__name__)
#endregion

#region constants
OUT_DIR = "temp/"
EXTENSION = "mp3"
QUALITY = "192"
YT_DLP_OPTS = {
    "format": "bestaudio/best",
    "noplaylist": True,
    "quiet": True,
    "outtmpl": None,  # we will handle the temp file
    "default_search": "ytsearch1",
    "cookiesfrombrowser": ("firefox",),
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

TEMPO_CNN_MIN_MAX_BINS = {
    "min": 30,
    "max": 286,
    "bins": 256
}
#endregion

@contextmanager
def gpu_model(model: Any):
    try: 
        yield model
    finally:
        tf.keras.backend.clear_session()
        reset_default_graph()
        del model
        gc.collect()

#region classes
@dataclass
class YT_DLP_wrapper(object):
    max_simultaneous_downloads: int = field(default=10)
    
    @staticmethod
    def generate_file_name(song_name: str, song_author: str) -> str:
        return f"./temp/{song_name}_{song_author}_{random.getrandbits(64):016x}"
    
    @staticmethod
    def generate_query(song_name: str, song_author: str) -> str:
        return f"{song_name} {song_author} audio"
    
    @classmethod
    def download_single_query(cls, song_row: dict[str, Any]) -> dict[str, Any]:
        f_name = cls.generate_file_name(song_row["track_title"], song_row["track_artist"])
        query = cls.generate_query(song_row["track_title"], song_row["track_artist"])
        info = {}
        
        local_opts = YT_DLP_OPTS.copy()
        local_opts["outtmpl"] = f_name
        
        import signal
        class TimeoutException(Exception):
            pass

        def handler(signum, frame):
            raise TimeoutException("YT-DLP download timed out")

        timeout_seconds = 30 # Set your desired timeout here

        signal.signal(signal.SIGALRM, handler)
        signal.alarm(timeout_seconds)

        entrydata = {}
        log.info(f"Trying to download {song_row['track_title']} - {song_row['track_artist']}")
        try:
            with yt_dlp.YoutubeDL(local_opts) as ydl:
                try:
                    info = ydl.extract_info(query, download=False)
                    
                    entrydata = info.get("entries", [{}])[0]

                    if 10*60 > entrydata.get("duration", -1) > 0 and entrydata.get("id", None)!=None:
                        log.info(f"Song {song_row['track_title']} - {song_row['track_artist']} passes filters (less than 10min adn has entrydata)")
                        ydl.extract_info(query, download=True)  

                        audio = MonoLoader(
                            filename=f"{f_name}.{EXTENSION}",
                            sampleRate=11025,
                            resampleQuality=4
                        )()
                        log.info(f"Audio loaded for {song_row['track_title']} - {song_row['track_artist']}")
                        song_row["_ytdlp_audio"] = audio
                    else:
                        log.warning(f"Skipping {song_row['track_title']} {song_row['track_artist']} because it is too long or has no id")
                        song_row["_ytdlp_audio"] = None
                except Exception as e:
                    log.error(f"Error extracting info for {query}: {e}")
                    song_row["_ytdlp_audio"] = None

        except TimeoutException:
            log.error(f"Song {song_row['track_title']} - {song_row['track_artist']} download timed out. Exiting.")
        
        finally:
            signal.alarm(0)
        
        os.remove(f"{f_name}.{EXTENSION}")
        
        song_row["track_viewcount"] = entrydata.get("view_count", None)
        song_row["track_commentCount"] = entrydata.get("comment_count", None)
        song_row["like_count"] = entrydata.get("like_count", None)
        song_row["track_avRating"] = entrydata.get("average_rating", None)

        if "_ytdlp_audio" not in song_row:
            song_row["_ytdlp_audio"] = None

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
                    results.append(result)
                except Exception as e:
                    log.error(f"Error processing query: {e}")
            return results

@dataclass
class MLLabellingWrapper(object):
    input_dataframe: pd.DataFrame = field(default_factory=pd.DataFrame)
    output_dataframe: str = field(default="")
    max_simultaneous_downloads: int = field(default=10)
    batch_size: int = field(default=10)
    
    __current_song_batch: list[dict[str, Any]] = field(default_factory=list)
    __next_song_batch: list[dict[str, Any]] = field(default_factory=list)
    downloader: YT_DLP_wrapper = field(default_factory=YT_DLP_wrapper)
    
    def __post_init__(self):
        self.downloader = YT_DLP_wrapper(max_simultaneous_downloads=self.max_simultaneous_downloads)
    
    @staticmethod
    def interpret_discogs_output(output, isreverted=False):
        reduced = np.mean(output, axis=0)
        if isreverted:
            reduced = np.flip(reduced)
        if len(reduced) == 3:
            return {"low": float(reduced[0]), "medium": float(reduced[1]), "high": float(reduced[2])}
        elif len(reduced) == 2:
            return {"low": float(reduced[0]), "high": float(reduced[1])}
        if len(reduced) > 3:
            return np.argmax([o[0] for o in output]) 
        
        return output

    def pipeline_phase_1(self, song_batch: list[dict[str, Any]]):
        if len(song_batch) == 0:
            return
        
        strat_steps = PB_STRAT[1]
        
        with gpu_model(TensorflowPredictEffnetDiscogs(
            graphFilename=strat_steps["discogs_embeddings_extractor"], 
            output="PartitionedCall:1"
            )) as embeddings_extractor:
            for song in song_batch[:]:
                if song.get("_ytdlp_audio", None) is not None:
                    song["_ml_embeddings"] = embeddings_extractor(song["_ytdlp_audio"])
                    log.info(f"Embeddings extracted for {song['track_title']} - {song['track_artist']}")
                else:
                    song["_ml_embeddings"] = None
                    log.error(f"No audio found for {song['track_title']} - {song['track_artist']}")

        with gpu_model(TensorflowPredictTempoCNN(
            graphFilename=strat_steps["tempo_predictor"]
            )) as bpm_predictor:
            for song in song_batch[:]:
                if song.get("_ytdlp_audio", None) is not None:
                    bpm_pred = bpm_predictor(song["_ytdlp_audio"])
                    global_vector = np.mean(bpm_pred, axis=0)  # shape (256,)
                    bpm_bin_index = np.argmax(global_vector)
                    song["bpm"] = TEMPO_CNN_MIN_MAX_BINS["min"] + (bpm_bin_index / (TEMPO_CNN_MIN_MAX_BINS["bins"] - 1)) * (TEMPO_CNN_MIN_MAX_BINS["max"] - TEMPO_CNN_MIN_MAX_BINS["min"])
                    log.info(f"Bpm extracted for {song['track_title']} - {song['track_artist']}: {song["bpm"]}")
                else:
                    song["bpm"] = None
                    log.error(f"No audio found for {song['track_title']} - {song['track_artist']}")
                
        for song in song_batch[:]:
            del song["_ytdlp_audio"]
        
        return song_batch

    def pipeline_phase_2(self, song_batch: list[dict[str, Any]]):
        if len(song_batch) == 0:
            return
        
        strat_steps = PB_STRAT[2]
        
        # approachability
        with gpu_model(TensorflowPredict2D(
            graphFilename=strat_steps["discogs_approach_predictor"], output="model/Softmax")
            ) as approachability_predictor:
            for song in song_batch[:]:
                if song.get("_ml_embeddings", None) is not None:
                    song["approachability"] = self.interpret_discogs_output(
                        approachability_predictor(song["_ml_embeddings"]))
                    log.info(f"Approachability extracted for {song['track_title']} - {song['track_artist']}: {song["approachability"]}")
                else:
                    song["approachability"] = None
                    log.error(f"No embeddings found for {song['track_title']} - {song['track_artist']}")

        # engagement
        with gpu_model(TensorflowPredict2D(
            graphFilename=strat_steps["discogs_engagement_predictor"], output="model/Softmax")
            ) as engagement_predictor:
            for song in song_batch[:]:
                if song.get("_ml_embeddings", None) is not None:
                    song["engagement"] = self.interpret_discogs_output(
                        engagement_predictor(song["_ml_embeddings"])
                        )
                    log.info(f"Engagement extracted for {song['track_title']} - {song['track_artist']}: {song["engagement"]}")
                else:
                    song["engagement"] = None
                    log.error(f"No embeddings found for {song['track_title']} - {song['track_artist']}")
        
        # danceability
        with gpu_model(TensorflowPredict2D(
            graphFilename=strat_steps["discogs_danceability_predictor"], output="model/Softmax")
            ) as danceability_predictor:
            for song in song_batch[:]:
                if song.get("_ml_embeddings", None) is not None:
                    song["danceability"] = self.interpret_discogs_output(
                        danceability_predictor(song["_ml_embeddings"]), True)
                    log.info(f"Danceability extracted for {song['track_title']} - {song['track_artist']}: {song["danceability"]}")
                else:
                    song["danceability"] = None
                    log.error(f"No embeddings found for {song['track_title']} - {song['track_artist']}")
        
        # acousticness
        with gpu_model(TensorflowPredict2D(
            graphFilename=strat_steps["discogs_mood_acousticness_predictor"], output="model/Softmax")
            ) as acousticness_predictor:
            for song in song_batch[:]:
                if song.get("_ml_embeddings", None) is not None:
                    song["acousticness"] = self.interpret_discogs_output(
                        acousticness_predictor(song["_ml_embeddings"]), True)
                    log.info(f"Acousticness extracted for {song['track_title']} - {song['track_artist']}: {song["acousticness"]}")
                else:
                    song["acousticness"] = None
                    log.error(f"No embeddings found for {song['track_title']} - {song['track_artist']}")
                
        # agressiveness
        with gpu_model(TensorflowPredict2D(
            graphFilename=strat_steps["discogs_mood_agressiveness_predictor"], output="model/Softmax")
            ) as agressiveness_predictor:
            for song in song_batch[:]:
                if song.get("_ml_embeddings", None) is not None:
                    song["agressiveness"] = self.interpret_discogs_output(
                        agressiveness_predictor(song["_ml_embeddings"]), True)
                    log.info(f"Agressiveness extracted for {song['track_title']} - {song['track_artist']}: {song["agressiveness"]}")
                else:
                    song["agressiveness"] = None
                    log.error(f"No embeddings found for {song['track_title']} - {song['track_artist']}")
                
        # electronicness
        with gpu_model(TensorflowPredict2D(
            graphFilename=strat_steps["discogs_mood_electronicness_predictor"], output="model/Softmax")
            ) as electronicness_predictor:
            for song in song_batch[:]:
                if song.get("_ml_embeddings", None) is not None:
                    song["electronicness"] = self.interpret_discogs_output(
                        electronicness_predictor(song["_ml_embeddings"]), True)
                    log.info(f"Electronicness extracted for {song['track_title']} - {song['track_artist']}: {song["electronicness"]}")
                else:
                    song["electronicness"] = None
                    log.error(f"No embeddings found for {song['track_title']} - {song['track_artist']}")
                
        # happy
        with gpu_model(TensorflowPredict2D(
            graphFilename=strat_steps["discogs_mood_happy_predictor"], output="model/Softmax")
            ) as happy_predictor:
            for song in song_batch[:]:
                if song.get("_ml_embeddings", None) is not None:
                    song["happy"] = self.interpret_discogs_output(
                        happy_predictor(song["_ml_embeddings"]), True)
                    log.info(f"Happy extracted for {song['track_title']} - {song['track_artist']}: {song["happy"]}")
                else:
                    song["happy"] = None
                    log.error(f"No embeddings found for {song['track_title']} - {song['track_artist']}")
            
        # party
        with gpu_model(TensorflowPredict2D(
            graphFilename=strat_steps["discogs_mood_party_predictor"], output="model/Softmax")
            ) as party_predictor:
            for song in song_batch[:]:
                if song.get("_ml_embeddings", None) is not None:
                    song["party"] = self.interpret_discogs_output(
                        party_predictor(song["_ml_embeddings"]), True)
                    log.info(f"Party extracted for {song['track_title']} - {song['track_artist']}: {song["party"]}")
                else:
                    song["party"] = None
                    log.error(f"No embeddings found for {song['track_title']} - {song['track_artist']}")

        # relaxed
        with gpu_model(TensorflowPredict2D(
            graphFilename=strat_steps["discogs_mood_relaxed_predictor"], output="model/Softmax")
            ) as relaxed_predictor:
            for song in song_batch[:]:
                if song.get("_ml_embeddings", None) is not None:
                    song["relaxed"] = self.interpret_discogs_output(
                        relaxed_predictor(song["_ml_embeddings"]), True)
                    log.info(f"Relaxed extracted for {song['track_title']} - {song['track_artist']}: {song["relaxed"]}")
                else:
                    song["relaxed"] = None
                    log.error(f"No embeddings found for {song['track_title']} - {song['track_artist']}")

        # sad     
        with gpu_model(TensorflowPredict2D(
            graphFilename=strat_steps["discogs_mood_sad_predictor"], output="model/Softmax")
            ) as sad_predictor:
            for song in song_batch[:]:
                if song.get("_ml_embeddings", None) is not None:
                    song["sad"] = self.interpret_discogs_output(
                        sad_predictor(song["_ml_embeddings"]), True)
                    log.info(f"Sad extracted for {song['track_title']} - {song['track_artist']}: {song["sad"]}")
                else:
                    song["sad"] = None
                    log.error(f"No embeddings found for {song['track_title']} - {song['track_artist']}")
                
        for song in song_batch[:]:
            del song["_ml_embeddings"]
        
        return song_batch
                
    def process_batch(self):
        log.info("Starting phase 1 pipeline")
        self.__current_song_batch = self.pipeline_phase_1(self.__current_song_batch)
        log.info("Starting phase 2 pipeline")
        self.__current_song_batch = self.pipeline_phase_2(self.__current_song_batch)
        log.info("Phase 1 and 2 pipelines completed")
    
    def append_to_output_dataframe(self):
        include_header = not os.path.exists(self.output_dataframe) or os.path.getsize(self.output_dataframe) == 0
        
        pd.DataFrame(self.__current_song_batch).to_csv(
            self.output_dataframe, mode='a', header=include_header, index=False)
    
    def create_output_dataframe(self):
        if os.path.exists(self.output_dataframe):
            os.remove(self.output_dataframe)
        with open(self.output_dataframe, 'w') as f:
            f.write('')
        
    def pipeline_orchestrator(self):
        self.create_output_dataframe()
        
        # download first batch
        batch = self.input_dataframe.iloc[0:self.batch_size].to_dict(orient="records")
        self.__next_song_batch = self.downloader.batch_download(batch) #TODO: out of bounds
        log.info(f"Downloaded first batch successfully [{",".join([f"{s['track_title']} - {s['track_artist']}" for s in self.__next_song_batch])}]")

        for i in range(0, len(self.input_dataframe), self.batch_size):
            self.__current_song_batch = self.__next_song_batch

            nextbatch = self.input_dataframe.iloc[(i+1)*self.batch_size:(i+2)*self.batch_size].to_dict(orient="records")
            log.info(f"Queuing download of next batch ({i+1}) [{",".join([f"{s['track_title']} - {s['track_artist']}" for s in nextbatch])}]")
            log.info(f"Starting process of current batch ({i}) [{",".join([f"{s['track_title']} - {s['track_artist']}" for s in self.__current_song_batch])}]")
            with concurrent.futures.ProcessPoolExecutor(max_workers=10) as executor:
                next_batch_future = executor.submit(
                    self.downloader.batch_download,
                    nextbatch
                )
                
                self.process_batch()
                
                self.__next_song_batch = next_batch_future.result()
                self.append_to_output_dataframe()
                shutil.rmtree("./temp", ignore_errors=True)
                os.makedirs("./temp", exist_ok=True)
#endregion

if __name__ == "__main__":
    df = pd.read_csv("MixDB_scrapper/output/data/scrapped_combo_filtered_pl_lt_8_10k.csv")
    d = MLLabellingWrapper(input_dataframe=df, output_dataframe="MixDB_scrapper/output/data/scrapped_combo_filtered_pl_lt_8_10k_labelled.csv", max_simultaneous_downloads=10, batch_size=10)
    
    # d.pipeline_orchestrator()
    