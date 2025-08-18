# Test suite import 
from unittest import TestCase

# Tested libs imports
from LLMapi.OllamaInterface import OllamaInterface

# Other imports
import os
from lib.LoggingHelper import LoggingHelper
import logging as log
import coloredlogs

coloredlogs.install(level='INFO', fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

class TestOllamaInterface(TestCase):
    def test_ollama_interface(self):
        ollama_interface = OllamaInterface.from_file("LLMapi/res/config_ollama.json")
        log.info(ollama_interface._OllamaInterface__chat_options)
        ollama_interface.chat("{ \"previous-song\": { \"name\": \"Careless Whisper\", \"artist\": \"George Michael\"}, \"next-song\": { \"name\": \"Baby Come Back\", \"artist\": \"Player\"}}")
        log.info(ollama_interface._OllamaInterface__chat_history[-1])
        