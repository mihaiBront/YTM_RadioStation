from ollama import Client
import json

client = Client(host='http://localhost:11434')

# Define your tools
tools = [
    {
        "name": "get_current_weather",
        "description": "Get the current weather in a given location",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "The city and state, e.g. San Francisco, CA"
                }
            },
            "required": ["location"]
        }
    },
    {
        "name": "get_stock_price",
        "description": "Get the current price of a stock",
        "parameters": {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "The stock symbol, e.g. AAPL"
                }
            },
            "required": ["symbol"]
        }
    }
]

# Tool implementations
def get_current_weather(location):
    """Mock weather function"""
    return {"temperature": "72°F", "conditions": "sunny", "location": location}

def get_stock_price(symbol):
    """Mock stock function"""
    return {"price": 150.25, "currency": "USD", "symbol": symbol}

class ChatSession:
    def __init__(self, model="mistral"):
        self.model = model
        self.message_history = []
        
    def add_message(self, role, content, tool_call=None):
        """Add a message to history"""
        msg = {"role": role, "content": content}
        if tool_call:
            msg["tool_calls"] = tool_call
        self.message_history.append(msg)
    
    def run_tool(self, tool_call):
        """Execute the requested tool"""
        func_name = tool_call['function']['name']
        args = json.loads(tool_call['function']['arguments'])
        
        if func_name == "get_current_weather":
            result = get_current_weather(**args)
        elif func_name == "get_stock_price":
            result = get_stock_price(**args)
        else:
            result = f"Error: Unknown tool {func_name}"
        
        # Add tool response to history
        self.add_message("tool", json.dumps(result), tool_call['function']['name'])
        return result
    
    def chat(self, user_input):
        """Process a user message with context"""
        # Add user message to history
        self.add_message("user", user_input)
        
        # Get model response
        response = client.chat(
            model=self.model,
            messages=self.message_history,
            options={"tools": tools}
        )
        
        # Handle tool calls
        if 'tool_calls' in response:
            tool_call = response['tool_calls'][0]
            self.add_message("assistant", None, response['tool_calls'])
            
            # Execute tool
            tool_result = self.run_tool(tool_call)
            
            # Get model response with tool result
            response = client.chat(
                model=self.model,
                messages=self.message_history
            )
        
        # Add final assistant response to history
        if 'message' in response:
            self.add_message("assistant", response['message']['content'])
            return response['message']['content']
        return "No response generated"