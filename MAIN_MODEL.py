import requests
import json
import LOGS
from SYSTEM_CALLS import *

OLLAMA_API_URL = "http://localhost:11434/api/chat"

SYSTEM_PROMPT = """You are Luma, a helpful AI assistant that can control system functions.
You have access to tools for controlling screen brightness, volume, media playback, and power management.

IMPORTANT: Only use tools when the user explicitly asks you to perform a system action like:
- Adjusting brightness or volume
- Playing/pausing media
- Locking the screen, suspending, or shutting down

For normal conversation, greetings, questions, or general chat, respond naturally WITHOUT using any tools.
Do not call tools unless the user's request clearly requires a system action."""

class MAIN_MODEL:
    def __init__(self, model_name="llama3.2", temperature=0.7, max_tokens=512, use_tools=False):
        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.use_tools = use_tools
        self.messages = []  # Conversation history
        
        # Add system prompt if using tools
        if self.use_tools:
            self.messages.append({"role": "system", "content": SYSTEM_PROMPT})
        
        # Define all available tools
        self.tools = [
            # Screen brightness
            {
                "type": "function",
                "function": {
                    "name": "set_screen_brightness",
                    "description": "Sets the screen brightness to a specified level (0-100).",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "level": {
                                "type": "integer",
                                "description": "Brightness level from 0 (darkest) to 100 (brightest)",
                            },
                        },
                        "required": ["level"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_screen_brightness",
                    "description": "Gets the current screen brightness level (0-100).",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": [],
                    },
                },
            },
            # Volume controls
            {
                "type": "function",
                "function": {
                    "name": "set_volume",
                    "description": "Sets the system volume to a specified level (0-100).",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "level": {
                                "type": "integer",
                                "description": "Volume level from 0 (muted) to 100 (max)",
                            },
                        },
                        "required": ["level"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_volume",
                    "description": "Gets the current system volume level (0-100).",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": [],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "mute_volume",
                    "description": "Mutes the system volume.",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": [],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "unmute_volume",
                    "description": "Unmutes the system volume.",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": [],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "toggle_mute",
                    "description": "Toggles the mute state of system volume.",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": [],
                    },
                },
            },
            # Media controls
            {
                "type": "function",
                "function": {
                    "name": "media_play_pause",
                    "description": "Toggles play/pause for the current media player.",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": [],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "media_next",
                    "description": "Skips to the next track in the media player.",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": [],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "media_previous",
                    "description": "Goes to the previous track in the media player.",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": [],
                    },
                },
            },
            # Power controls
            {
                "type": "function",
                "function": {
                    "name": "lock_screen",
                    "description": "Locks the screen.",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": [],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "suspend",
                    "description": "Puts the system to sleep/suspend mode.",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": [],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "reboot",
                    "description": "Reboots the system. Use with caution.",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": [],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "shutdown",
                    "description": "Shuts down the system. Use with caution.",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": [],
                    },
                },
            },
        ]
        
        # Map function names to actual functions
        self.available_functions = {
            "set_screen_brightness": set_screen_brightness,
            "get_screen_brightness": get_screen_brightness,
            "set_volume": set_volume,
            "get_volume": get_volume,
            "mute_volume": mute_volume,
            "unmute_volume": unmute_volume,
            "toggle_mute": toggle_mute,
            "media_play_pause": media_play_pause,
            "media_next": media_next,
            "media_previous": media_previous,
            "lock_screen": lock_screen,
            "suspend": suspend,
            "reboot": reboot,
            "shutdown": shutdown,
        }

    def _execute_tool_call(self, tool_call: dict) -> str:
        """Execute a tool call and return the result as a string."""
        function_name = tool_call["function"]["name"]
        arguments = tool_call["function"].get("arguments", {})
        
        if function_name not in self.available_functions:
            return json.dumps({"error": f"Unknown function: {function_name}"})
        
        try:
            func = self.available_functions[function_name]
            # Parse arguments if they're a string
            if isinstance(arguments, str):
                arguments = json.loads(arguments) if arguments else {}
            
            # Convert numeric string arguments to proper types
            for key, value in arguments.items():
                if isinstance(value, str) and value.isdigit():
                    arguments[key] = int(value)
                elif isinstance(value, str):
                    try:
                        arguments[key] = float(value)
                    except ValueError:
                        pass  # Keep as string
            
            LOGS.log_info(f"Executing function: {function_name}({arguments})")
            result = func(**arguments)
            
            # Format result based on type
            if result is None:
                return json.dumps({"status": "completed", "result": None})
            elif isinstance(result, bool):
                return json.dumps({"status": "success" if result else "failed", "result": result})
            else:
                return json.dumps({"status": "success", "result": result})
                
        except Exception as e:
            LOGS.log_error(f"Tool execution error: {e}")
            return json.dumps({"error": str(e)})

    def _call_api(self, payload: dict, stream: bool = False):
        """Make a request to the Ollama API."""
        payload["stream"] = stream
        response = requests.post(OLLAMA_API_URL, json=payload, stream=stream)
        response.raise_for_status()
        return response

    def generate_response(self, prompt):
        """Generate a response, handling tool calls if enabled."""
        # Add user message to history
        self.messages.append({"role": "user", "content": prompt})
        
        # Build request payload
        payload = {
            "model": self.model_name,
            "messages": self.messages,
        }
        if self.use_tools:
            payload["tools"] = self.tools
        
        if self.use_tools:
            # Stream the response and collect tool calls if any
            response = self._call_api(payload, stream=True)
            
            full_response = ""
            tool_calls = []
            
            for line in response.iter_lines():
                if line:
                    chunk = json.loads(line)
                    message = chunk.get("message", {})
                    
                    # Collect content
                    content = message.get("content", "")
                    if content:
                        full_response += content
                        yield content
                    
                    # Collect tool calls from the stream
                    if message.get("tool_calls"):
                        tool_calls.extend(message.get("tool_calls", []))
            
            # If there were tool calls, execute them and get final response
            if tool_calls:
                # Add assistant message with tool calls to history
                self.messages.append({
                    "role": "assistant",
                    "content": full_response,
                    "tool_calls": tool_calls
                })
                
                # Execute each tool call
                for tool_call in tool_calls:
                    result = self._execute_tool_call(tool_call)
                    
                    # Add tool response to messages
                    self.messages.append({
                        "role": "tool",
                        "content": result,
                    })
                
                # Get final response after tool execution (streaming)
                payload["messages"] = self.messages
                response = self._call_api(payload, stream=True)
                
                final_response = ""
                for line in response.iter_lines():
                    if line:
                        chunk = json.loads(line)
                        content = chunk.get("message", {}).get("content", "")
                        if content:
                            final_response += content
                            yield content
                
                # Add final response to history
                self.messages.append({"role": "assistant", "content": final_response})
            else:
                # No tool calls - just add the response to history
                self.messages.append({"role": "assistant", "content": full_response})
            return
        
        # No tools enabled - stream the response directly
        response = self._call_api(payload, stream=True)
        
        full_response = ""
        for line in response.iter_lines():
            if line:
                chunk = json.loads(line)
                content = chunk.get("message", {}).get("content", "")
                if content:
                    full_response += content
                    yield content
        
        # Add assistant response to history
        self.messages.append({"role": "assistant", "content": full_response})

    def clear_history(self):
        """Clear conversation history, keeping system prompt if tools are enabled."""
        if self.use_tools:
            self.messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        else:
            self.messages = []


if __name__ == "__main__":
    # Test with function calling
    model = MAIN_MODEL(model_name="llama3.2", temperature=0.5, max_tokens=256, use_tools=True)
    
    print("Testing function calling...")
    print("-" * 40)
    
    # Test a simple query that should trigger a tool call
    prompt = "What is the current screen brightness?"
    print(f"User: {prompt}")
    print("AI: ", end='', flush=True)
    for chunk in model.generate_response(prompt):
        print(chunk, end='', flush=True)
    print("\n")
    
    # Test setting brightness
    prompt = "Set the screen brightness to 50%"
    print(f"User: {prompt}")
    print("AI: ", end='', flush=True)
    for chunk in model.generate_response(prompt):
        print(chunk, end='', flush=True)
    print("\n")