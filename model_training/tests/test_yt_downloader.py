from unittest import TestCase

from dataset_enhancing_models.new_YT_DLP_wrapper import MLLabellingWrapper
import pandas as pd

import logging as log
import json
import os

TEST_FILE = os.path.basename(__file__)

log.basicConfig(
    level=log.DEBUG, 
    format='%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d:%(funcName)s - %(message)s',
    filename=f"./logs/tests_{TEST_FILE}.log", filemode="a"
)
class TestYTDLPWrapper(TestCase):
    def test_download_batch(self):
        df = pd.read_csv("MixDB_scrapper/output/data/scrapped_combo_filtered_pl_lt_8_10k.csv")
        log.info(f"Starting download batch tests for {TEST_FILE}")
        d = MLLabellingWrapper(
            input_dataframe=df,
            output_dataframe="MixDB_scrapper/output/data/scrapped_combo_filtered_pl_lt_8_10k_labelled.csv",
            max_simultaneous_downloads=10, 
            batch_size=10)
        log.info("Starting download batch tests")
        batch = df.iloc[0:10].to_dict(orient="records")
        batch = d.downloader.batch_download(batch)
        for song in batch[:]:
            try:
                del song["_ytdlp_audio"]
            except Exception as e:
                log.error(f"Error deleting _ytdlp_audio: {e}")
        log.info(f"Songs: {json.dumps(batch)}")
        log.info("Download batch tests completed")

    def test_process_multiple_batches(self):
        df = pd.read_csv("MixDB_scrapper/output/data/scrapped_combo_filtered_pl_lt_8_10k.csv")
        log.info(f"Starting process multiple batches tests for {TEST_FILE}")
        d = MLLabellingWrapper(
            input_dataframe=df,
            output_dataframe="MixDB_scrapper/output/data/scrapped_combo_filtered_pl_lt_8_10k_labelled.csv",
            max_simultaneous_downloads=10, 
            batch_size=10)
        
        for i in range(0, len(df), 10):
            batch = df.iloc[i*10:(i + 1)*10].to_dict(orient="records")
            batch = d.downloader.batch_download(batch)
            for song in batch[:]:
                try:
                    del song["_ytdlp_audio"]
                except Exception as e:
                    log.error(f"Error deleting _ytdlp_audio: {e}")
            
            log.info(f"Batch {i}: {json.dumps(batch)}")

            if i > 100:
                break

        log.info("Process multiple batches tests completed")

    def test_phase_one(self):
        df = pd.read_csv("MixDB_scrapper/output/data/scrapped_combo_filtered_pl_lt_8_10k.csv")
        log.info(f"Starting phase one tests for {TEST_FILE}")
        d = MLLabellingWrapper(
            input_dataframe=df,
            output_dataframe="MixDB_scrapper/output/data/scrapped_combo_filtered_pl_lt_8_10k_labelled.csv",
            max_simultaneous_downloads=10, 
            batch_size=10)
        log.info("Starting phase one tests")
        d.pipeline_orchestrator()
        log.info("Phase one tests completed")
        