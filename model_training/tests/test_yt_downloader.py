from unittest import TestCase
from dataset_enhancing_models.YT_DLP_wrapper import YT_DLP_wrapper, Query

import logging as log

log.basicConfig(level=log.DEBUG, format='%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d:%(funcName)s - %(message)s')

class TestYTDLPWrapper(TestCase):
    def test_download_single_query(self):
        yt_dlp_wrapper = YT_DLP_wrapper()
        query = Query(id=1, name="Daft Punk Get Lucky", artist="Daft Punk")
        result = yt_dlp_wrapper.download_single_query(query)
        self.assertIsNotNone(result)
        self.assertEqual(result.id, 1)
        self.assertEqual(result.name, "Daft Punk Get Lucky")
        self.assertEqual(result.artist, "Daft Punk")