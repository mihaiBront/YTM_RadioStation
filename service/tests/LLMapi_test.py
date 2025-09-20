# Test suite import 
from unittest import TestCase
import os

# Tested libs imports
from lib.LanguageModel.OllamaInterface import OllamaInterface
from lib.LoggingHelper import LoggingHelper

# Other imports
from lib.LoggingHelper import LoggingHelper
import logging as log

LoggingHelper.init_logger(level="DEBUG", theme="dark")

class TestOllamaInterface(TestCase):
    def test_ollama_interface(self):
        ollama_interface = OllamaInterface.from_file("lib/LanguageModel/res/config_ollama.json")
        log.info(ollama_interface._OllamaInterface__chat_options)
        ollama_interface.chat("{ \"previous-song\": { \"name\": \"Careless Whisper\", \"artist\": \"George Michael\"}, \"next-song\": { \"name\": \"Baby Come Back\", \"artist\": \"Player\"}}")
        log.info(ollama_interface._OllamaInterface__chat_history[-1])
        