#!/usr/bin/env python3

from LLMapi.OllamaInterface import OllamaInterface

def test_tool_calls():
    print("Testing OllamaInterface with tool calls...")
    
    # Load the interface
    ollama_interface = OllamaInterface.from_file(
        "LLMapi/res/config_ollama.json"
    )
    
    # Test with a real URL
    print("\nTesting with BBC News URL:")
    response = ollama_interface.chat("Summarize https://www.bbc.com/news")
    print(f"Response: {response}")

if __name__ == "__main__":
    test_tool_calls()
