"""
IPMentor - IPv4 Networking Assistant with MCP Integration

An experimental chatbot interface that demonstrates IPMentor's networking tools
through the Model Context Protocol (MCP), providing conversational access to
IP analysis, subnet calculations, and network diagram generation.
"""

import asyncio
import os
import json
from typing import Any, Generator
from dotenv import load_dotenv

import gradio as gr
from gradio import ChatMessage
from openai import OpenAI

# MCP imports
from langchain_mcp_adapters.client import MultiServerMCPClient

# Load environment variables
load_dotenv()

##########################################################
# GLOBAL CONFIGURATION
##########################################################

# Control whether to show tool execution details
SHOW_TOOLS = True  # True: shows tool details, False: only typing and response

def load_system_prompt():
    """Load the system prompt from an external .md file."""
    try:
        with open("experimental/system_prompt.md", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        print("Warning: experimental/system_prompt.md not found, using default prompt")
        return "You are an IPv4 networking assistant specialized in subnetting calculations and network analysis."

SYSTEM_PROMPT = load_system_prompt()

##########################################################
# UTILITY FUNCTIONS
##########################################################

def safe_json_serialize(obj):
    """Safely serialize an object to JSON, handling non-serializable types."""
    try:
        if isinstance(obj, (str, int, float, bool, type(None))):
            return obj
        elif isinstance(obj, dict):
            return {k: safe_json_serialize(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [safe_json_serialize(item) for item in obj]
        else:
            # For complex objects, convert to string
            return str(obj)
    except Exception:
        return str(obj)

def safe_json_dumps(obj, **kwargs):
    """Safe JSON dumps that handles non-serializable objects."""
    try:
        return json.dumps(safe_json_serialize(obj), **kwargs)
    except Exception as e:
        return json.dumps({"error": f"Error serializing: {str(e)}", "data": str(obj)}, **kwargs)

##########################################################
# MODEL AND MCP CONFIGURATION
##########################################################

class MCPClientWrapper:
    def __init__(self):
        self.mcp_client = None
        self.tools = []
        self.connection_status = "Disconnected"
        
        # Configure OpenAI client for OpenRouter
        self.openai_client = OpenAI(
            api_key=os.getenv("OPENROUTER_API_KEY"),
            base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
        )
        self.model_name = "google/gemini-2.5-flash-preview-05-20"
    
    async def connect_async(self, server_url: str) -> str:
        """Connect to MCP server via SSE"""
        try:
            print(f"Attempting to connect to: {server_url}")
            
            # Configure MCP client
            self.mcp_client = MultiServerMCPClient({
                "ipmentor": {
                    "transport": "sse",
                    "url": server_url
                }
            })
            
            print("MCP client configured, getting tools...")
            
            # Get available tools
            mcp_tools = await self.mcp_client.get_tools()
            
            print(f"Tools obtained: {len(mcp_tools)}")
            for tool in mcp_tools:
                print(f"- {tool.name}: {tool.description}")
            
            # Convert tools to OpenAI format
            self.tools = []
            for tool in mcp_tools:
                # Get input schema safely
                input_schema = {}
                if hasattr(tool, 'input_schema'):
                    input_schema = safe_json_serialize(tool.input_schema)
                elif hasattr(tool, 'inputSchema'):
                    input_schema = safe_json_serialize(tool.inputSchema)
                
                tool_def = {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": input_schema
                    }
                }
                self.tools.append(tool_def)
                print(f"Tool converted: {tool.name}")
            
            tool_names = [tool["function"]["name"] for tool in self.tools]
            self.connection_status = "Connected"
            return f"✅ Connected to MCP server. Available tools: {', '.join(tool_names)}"
            
        except Exception as e:
            print(f"Detailed connection error: {type(e).__name__}: {str(e)}")
            import traceback
            traceback.print_exc()
            self.connection_status = "Error"
            return f"❌ Connection error: {str(e)}"
    
    def connect(self, server_url: str) -> str:
        """Synchronous wrapper for connecting"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(self.connect_async(server_url))
            return result
        finally:
            loop.close()
    
    async def call_tool_async(self, tool_name: str, tool_args: dict) -> Any:
        """Call a tool from the MCP server"""
        try:
            if not self.mcp_client:
                return {"error": "MCP client not initialized"}
            
            print(f"Calling tool {tool_name} with arguments: {tool_args}")
            
            # Find the tool in available tools
            mcp_tools = await self.mcp_client.get_tools()
            tool_to_call = None
            
            for tool in mcp_tools:
                if tool.name == tool_name:
                    tool_to_call = tool
                    break
            
            if not tool_to_call:
                return {"error": f"Tool {tool_name} not found"}
            
            # Try calling the tool with the most common method
            result = None
            try:
                if hasattr(tool_to_call, 'ainvoke'):
                    result = await tool_to_call.ainvoke(tool_args)
                    print(f"✅ Success with ainvoke() method")
                elif hasattr(tool_to_call, 'acall'):
                    result = await tool_to_call.acall(tool_args)
                    print(f"✅ Success with acall() method")
                elif hasattr(tool_to_call, 'func'):
                    result = tool_to_call.func(**tool_args)
                    print(f"✅ Success with func() method")
                else:
                    return {"error": f"No compatible method found for tool {tool_name}"}
            except Exception as e:
                print(f"Error calling tool {tool_name}: {e}")
                return {"error": f"Error executing tool {tool_name}: {str(e)}"}
            
            # Process result according to its type
            if isinstance(result, list) and len(result) == 2:
                # Handle generate_diagram result: ['Image URL: http://...', 'Success message']
                image_url = result[0]
                status_msg = result[1]
                
                # Extract file path from URL
                import re
                if '/gradio_api/file=' in image_url:
                    file_path = image_url.split('/gradio_api/file=')[1]
                    return {
                        "image_path": file_path,
                        "status": status_msg,
                        "format": "png" if "PNG" in status_msg else "svg"
                    }
                
                return {"result": result}
            
            # Handle string results (JSON from other tools)
            try:
                if isinstance(result, str):
                    parsed_result = json.loads(result)
                    return safe_json_serialize(parsed_result)
                else:
                    return safe_json_serialize(result)
            except json.JSONDecodeError:
                return {"result": str(result)}
            
        except Exception as e:
            print(f"Detailed error in call_tool_async: {type(e).__name__}: {str(e)}")
            import traceback
            traceback.print_exc()
            return {"error": f"Error calling tool {tool_name}: {str(e)}"}
    
    async def process_message_async(self, message: str, history) -> Generator:
        """Process message using OpenAI + MCP tools with streaming"""
        if self.connection_status != "Connected":
            yield history + [{"role": "assistant", "content": "❌ Please connect to the MCP server first."}]
            return
        
        # Create base history with user message included
        current_history = history[:] + [{"role": "user", "content": message}]
        
        # Immediately show user message
        yield current_history
        
        # Convert history to OpenAI format
        openai_messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        
        for msg in history:
            # Handle both dictionaries and message objects
            msg_role = msg.get("role") if isinstance(msg, dict) else getattr(msg, 'role', None)
            msg_content = msg.get("content") if isinstance(msg, dict) else getattr(msg, 'content', None)
            
            if msg_role in ["user", "assistant"] and msg_content:
                # Only skip if it's gr.Image or gr.File
                if str(type(msg_content).__name__) in ['Image', 'File']:
                    print(f"  Skipping Gradio component: {type(msg_content).__name__}")
                    continue
                
                content_str = str(msg_content).strip()
                if content_str:
                    print(f"  ✅ Adding [{msg_role}]: {content_str[:30]}...")
                    openai_messages.append({"role": msg_role, "content": content_str})
        
        # Add current user message
        openai_messages.append({"role": "user", "content": message})
        print(f"  ✅ Adding current message [user]: {message[:30]}...")
        
        print(f"📋 Total Gradio history: {len(history)} messages")
        for i, msg in enumerate(history):
            msg_role = msg.get("role") if isinstance(msg, dict) else getattr(msg, 'role', 'unknown')
            msg_content = msg.get("content") if isinstance(msg, dict) else getattr(msg, 'content', '')
            content_preview = str(msg_content)[:50] + "..." if len(str(msg_content)) > 50 else str(msg_content)
            print(f"  {i}: [{msg_role}] {content_preview}")
        
        print(f"📋 OpenAI history ({len(openai_messages)} messages):")
        for i, msg in enumerate(openai_messages):
            role = msg["role"]
            content = msg["content"][:100] + "..." if len(msg["content"]) > 100 else msg["content"]
            print(f"  {i}: [{role}] {content}")
        
        try:
            # Check if user is trying to directly call an MCP tool
            direct_tool_call = None
            if message.strip().startswith("MCP."):
                # Parse direct call: MCP.tool_name(param1="value1", param2="value2")
                import re
                pattern = r'MCP\.(\w+)\((.*?)\)'
                match = re.match(pattern, message.strip())
                if match:
                    tool_name = match.group(1)
                    params_str = match.group(2)
                    
                    # Parse parameters
                    tool_args = {}
                    if params_str:
                        # Simple parsing for key="value" pairs
                        param_pattern = r'(\w+)="([^"]*)"'
                        for param_match in re.finditer(param_pattern, params_str):
                            key = param_match.group(1)
                            value = param_match.group(2)
                            tool_args[key] = value
                    
                    print(f"🔧 Direct call detected: {tool_name} with args: {tool_args}")
                    direct_tool_call = (tool_name, tool_args)
            
            if direct_tool_call:
                # Process direct call
                tool_name, tool_args = direct_tool_call
                
                if SHOW_TOOLS:
                    current_history.append({
                        "role": "assistant",
                        "content": f"🔧 Executing tool: **{tool_name}**",
                        "metadata": {
                            "title": f"Tool: {tool_name}",
                            "log": f"Parameters: {json.dumps(tool_args, ensure_ascii=False, indent=2)}",
                            "status": "pending",
                            "id": f"tool_call_{tool_name}"
                        }
                    })
                    yield current_history
                
                # Execute the tool
                tool_result = await self.call_tool_async(tool_name, tool_args)
                
                if SHOW_TOOLS and current_history:
                    current_history[-1] = {
                        "role": "assistant",
                        "content": f"✅ Tool executed: **{tool_name}**" if not (isinstance(tool_result, dict) and "error" in tool_result) else f"❌ Tool error: **{tool_name}**",
                        "metadata": {
                            "title": f"Tool: {tool_name}",
                            "log": f"Parameters: {json.dumps(tool_args, ensure_ascii=False, indent=2)}",
                            "status": "done",
                            "id": f"tool_call_{tool_name}"
                        }
                    }
                    yield current_history
                
                # Process result (same code as before for tool results)
                if isinstance(tool_result, dict) and "error" not in tool_result:
                    result_serialized = safe_json_serialize(tool_result)
                    result_str = str(result_serialized)
                    
                    # Look for image file paths
                    import re
                    image_path = None
                    
                    if isinstance(result_serialized, dict):
                        for key in ['image_path', 'svg_path', 'path', 'file_path']:
                            if key in result_serialized:
                                potential_path = result_serialized[key]
                                if isinstance(potential_path, str) and os.path.exists(potential_path):
                                    image_path = potential_path
                                    break
                    
                    if image_path:
                        print(f"🖼️ Image found: {image_path}")
                        current_history.append({
                            "role": "assistant",
                            "content": gr.Image(value=image_path, show_label=False)
                        })
                        yield current_history
                        
                        if isinstance(result_serialized, dict):
                            info_parts = []
                            if 'format' in result_serialized:
                                info_parts.append(f"Format: {result_serialized['format'].upper()}")
                            if 'network' in result_serialized:
                                info_parts.append(f"Network: {result_serialized['network']}")
                            if 'hosts_per_subnet' in result_serialized:
                                hosts = result_serialized['hosts_per_subnet']
                                info_parts.append(f"Subnets: {len(hosts)} ({', '.join(map(str, hosts))} hosts)")
                            
                            if info_parts:
                                current_history.append({
                                    "role": "assistant",
                                    "content": "ℹ️ " + " | ".join(info_parts)
                                })
                                yield current_history
                    else:
                        formatted_result = safe_json_dumps(result_serialized, ensure_ascii=False, indent=2)
                        current_history.append({
                            "role": "assistant",
                            "content": f"```json\n{formatted_result}\n```"
                        })
                        yield current_history
                else:
                    # Tool error
                    if isinstance(tool_result, dict) and "error" in tool_result:
                        error_msg = tool_result["error"]
                    else:
                        error_msg = str(tool_result)
                    
                    current_history.append({
                        "role": "assistant",
                        "content": f"❌ Tool error {tool_name}: {error_msg}"
                    })
                    yield current_history
                
                yield current_history
                return
            
            # Primera llamada al modelo (sin streaming para tool calls)
            response = self.openai_client.chat.completions.create(
                model=self.model_name,
                messages=openai_messages,
                tools=self.tools if self.tools else None,
                stream=False
            )
            
            choice = response.choices[0]
            message_obj = choice.message
            
            # Si hay tool calls
            if message_obj.tool_calls:
                for tool_call in message_obj.tool_calls:
                    tool_name = tool_call.function.name
                    try:
                        tool_args = json.loads(tool_call.function.arguments)
                    except json.JSONDecodeError as e:
                        print(f"Error decoding tool arguments: {e}")
                        tool_args = {}
                    
                    if SHOW_TOOLS:
                        # Show that tool is being used
                        current_history.append({
                            "role": "assistant",
                            "content": f"🔧 Executing tool: **{tool_name}**",
                            "metadata": {
                                "title": f"Tool: {tool_name}",
                                "log": f"Parameters: {safe_json_dumps(tool_args, ensure_ascii=False, indent=2)}",
                                "status": "pending",
                                "id": f"tool_call_{tool_name}"
                            }
                        })
                        yield current_history
                    
                    # Call the tool
                    print(f"🔧 Executing tool: {tool_name}")
                    print(f"📝 Parameters: {tool_args}")
                    
                    tool_result = await self.call_tool_async(tool_name, tool_args)
                    
                    print(f"✅ Result obtained: {type(tool_result)}")
                    
                    if SHOW_TOOLS and current_history:
                        # Update status to completed (Gradio only accepts 'pending' or 'done')
                        current_history[-1] = {
                            "role": "assistant",
                            "content": f"✅ Tool executed: **{tool_name}**" if not (isinstance(tool_result, dict) and "error" in tool_result) else f"❌ Tool error: **{tool_name}**",
                            "metadata": {
                                "title": f"Tool: {tool_name}",
                                "log": f"Parameters: {safe_json_dumps(tool_args, ensure_ascii=False, indent=2)}",
                                "status": "done",
                                "id": f"tool_call_{tool_name}"
                            }
                        }
                        yield current_history
                    
                    # Process tool result
                    if isinstance(tool_result, dict) and "error" not in tool_result:
                        # Safely serialize result
                        result_serialized = safe_json_serialize(tool_result)
                        result_str = str(result_serialized)
                        
                        print(f"🔍 Debug result_serialized: {result_serialized}")
                        print(f"🔍 Debug result_str: {result_str}")
                        
                        # Look for image file paths
                        import re
                        image_path = None
                        
                        # Look in deserialized result first
                        if isinstance(result_serialized, dict):
                            for key in ['image_path', 'svg_path', 'path', 'file_path']:
                                if key in result_serialized:
                                    potential_path = result_serialized[key]
                                    if isinstance(potential_path, str) and os.path.exists(potential_path):
                                        image_path = potential_path
                                        break
                        
                        # If not found in dict, search with text patterns
                        if not image_path:
                            image_patterns = [
                                r'([^"\s]+\.(?:png|jpg|jpeg|gif|svg))',
                                r'image_path["\']?\s*:\s*["\']([^"\']+)["\']',
                                r'/.*?\.(?:png|svg|jpg|jpeg|gif)'
                            ]
                            
                            for pattern in image_patterns:
                                match = re.search(pattern, result_str, re.IGNORECASE)
                                if match:
                                    potential_path = match.group(1) if len(match.groups()) >= 1 else match.group(0)
                                    # Clean quotes
                                    potential_path = potential_path.strip('"\'')
                                    if os.path.exists(potential_path):
                                        image_path = potential_path
                                        break
                        
                        if image_path:
                            print(f"🖼️ Image found: {image_path}")
                            
                            # Show the image using dictionary format and gr.Image
                            current_history.append({
                                "role": "assistant",
                                "content": gr.Image(value=image_path, show_label=False)
                            })
                            yield current_history
                            
                            # Also show additional information if available
                            if isinstance(result_serialized, dict):
                                info_parts = []
                                if 'format' in result_serialized:
                                    info_parts.append(f"Format: {result_serialized['format'].upper()}")
                                if 'network' in result_serialized:
                                    info_parts.append(f"Network: {result_serialized['network']}")
                                if 'hosts_per_subnet' in result_serialized:
                                    hosts = result_serialized['hosts_per_subnet']
                                    info_parts.append(f"Subnets: {len(hosts)} ({', '.join(map(str, hosts))} hosts)")
                                
                                if info_parts:
                                    current_history.append({
                                        "role": "assistant",
                                        "content": "ℹ️ " + " | ".join(info_parts)
                                    })
                                    yield current_history
                        else:
                            if SHOW_TOOLS:
                                current_history.append({
                                    "role": "assistant",
                                    "content": "📊 Result:",
                                    "metadata": {
                                        "title": f"Result from {tool_name}",
                                        "status": "done",
                                        "id": f"result_{tool_name}"
                                    }
                                })
                                yield current_history
                            
                            # Show result in JSON format
                            formatted_result = safe_json_dumps(result_serialized, ensure_ascii=False, indent=2)
                            current_history.append({
                                "role": "assistant",
                                "content": f"```json\n{formatted_result}\n```"
                            })
                            yield current_history
                    else:
                        # Tool error or result with error
                        if isinstance(tool_result, dict):
                            if "error" in tool_result:
                                error_msg = tool_result["error"]
                            elif "result" in tool_result and isinstance(tool_result["result"], list):
                                # Case of ['None', 'Error message'] from generate_diagram
                                result_list = tool_result["result"]
                                if len(result_list) == 2 and result_list[0] in ['None', None]:
                                    error_msg = result_list[1]
                                else:
                                    error_msg = str(tool_result)
                            else:
                                error_msg = str(tool_result)
                        else:
                            error_msg = str(tool_result)
                            
                        current_history.append({
                            "role": "assistant",
                            "content": f"❌ Tool error {tool_name}: {error_msg}"
                        })
                        yield current_history
                    
                    # Send tool result back to model (safe serialization)
                    openai_messages.append({
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [tool_call]
                    })
                    openai_messages.append({
                        "role": "tool",
                        "content": safe_json_dumps(tool_result, ensure_ascii=False),
                        "tool_call_id": tool_call.id
                    })
                
                # Get final response from model with streaming
                final_response = self.openai_client.chat.completions.create(
                    model=self.model_name,
                    messages=openai_messages,
                    stream=True
                )
                
                # Process streaming
                streaming_content = ""
                temp_message = {"role": "assistant", "content": ""}
                current_history.append(temp_message)
                
                for chunk in final_response:
                    if chunk.choices[0].delta.content:
                        streaming_content += chunk.choices[0].delta.content
                        current_history[-1] = {"role": "assistant", "content": streaming_content}
                        yield current_history
            
            else:
                # Direct response without tools - also with streaming
                direct_response = self.openai_client.chat.completions.create(
                    model=self.model_name,
                    messages=openai_messages,
                    stream=True
                )
                
                streaming_content = ""
                temp_message = {"role": "assistant", "content": ""}
                current_history.append(temp_message)
                
                for chunk in direct_response:
                    if chunk.choices[0].delta.content:
                        streaming_content += chunk.choices[0].delta.content
                        current_history[-1] = {"role": "assistant", "content": streaming_content}
                        yield current_history
            
            yield current_history
            
        except Exception as e:
            current_history.append({
                "role": "assistant",
                "content": f"❌ Error processing query: {str(e)}"
            })
            yield current_history
    
    async def process_message_streaming(self, message: str, history):
        """Process message with streaming for Gradio"""
        async for result in self.process_message_async(message, history):
            yield result

# MCP client instance
client = MCPClientWrapper()

def toggle_tools_display(show_tools):
    """Function to change the tool display configuration"""
    global SHOW_TOOLS
    SHOW_TOOLS = show_tools
    return f"🔧 Show tools: {'✅ Enabled' if show_tools else '❌ Disabled'}"

def user(user_message: str, history):
    """Add user message to history"""
    if not user_message.strip():
        return "", history
    
    # Add user message immediately as dictionary
    new_history = history + [{"role": "user", "content": user_message}]
    return "", new_history

async def bot(history):
    """Process bot response with streaming"""
    if not history or len(history) == 0:
        yield history
        return
    
    # Get the last user message (handle both dict and message objects)
    last_user_message = None
    for msg in reversed(history):
        # Handle both dictionaries and message objects
        if isinstance(msg, dict):
            if msg.get("role") == "user":
                last_user_message = msg.get("content")
                break
        elif hasattr(msg, 'role') and msg.role == "user":
            last_user_message = msg.content
            break
    
    if not last_user_message:
        yield history
        return
    
    # Convert history to ChatMessage objects for internal processing
    converted_history = []
    for msg in history[:-1]:  # Exclude the last message (the one we're processing)
        if isinstance(msg, dict):
            converted_history.append(ChatMessage(role=msg["role"], content=msg["content"]))
        else:
            converted_history.append(msg)
    
    print(f"🎯 Processing user message: '{last_user_message}'")
    print(f"📚 Previous history: {len(converted_history)} messages")
    
    # Process with MCP client
    async for result in client.process_message_streaming(last_user_message, converted_history):
        yield result

def gradio_interface():
    with gr.Blocks(title="IPMentor - IPv4 Assistant with MCP") as demo:
        # Header with logo
        gr.Image("assets/header.png", show_label=False, interactive=False, container=False, height=120)
        
        # Description
        gr.Markdown("""
        **IPMentor** is a conversational IPv4 networking assistant powered by MCP (Model Context Protocol).
        
        Connect to the MCP server and chat with the specialized assistant for IP analysis, subnet calculations, and network diagram generation.
        
        Choose the tools you need through natural conversation - the assistant will use the appropriate networking tools automatically.
        """)
        
        with gr.Row(equal_height=True):
            with gr.Column(scale=3):
                server_url = gr.Textbox(
                    label="MCP Server URL (SSE)",
                    placeholder="http://localhost:7860/gradio_api/mcp/sse",
                    value="http://localhost:7860/gradio_api/mcp/sse"
                )
            with gr.Column(scale=1):
                connect_btn = gr.Button("🔌 Connect", variant="primary")
        
        with gr.Row():
            with gr.Column(scale=1):
                tools_toggle = gr.Checkbox(
                    label="Show tool calls",
                    value=SHOW_TOOLS,
                    info="Shows details of the tools used"
                )
            with gr.Column(scale=3):
                status = gr.Textbox(label="Connection Status", interactive=False)
        
        chatbot = gr.Chatbot(
            value=[], 
            height=600,
            type="messages",
            show_copy_button=True,
            show_label=False
        )
        
        with gr.Row(equal_height=True):
            msg = gr.Textbox(
                label="Your Question",
                placeholder="Ask about IPv4 networks, subnetting, or request a diagram generation...",
                scale=4,
                lines=1,
                max_lines=3
            )
            send_btn = gr.Button("📤 Send", variant="primary", scale=1)
            clear_btn = gr.Button("🗑️ Clear", scale=1)
        
        # Examples
        gr.Examples(
            examples=[
                "Analyze the IP 192.168.1.100/24",
                "Calculate 4 subnets for the network 10.0.0.0/16",
                "Generate a diagram of the network 172.16.0.0/20 with 8 subnets",
                "What is the broadcast address of 192.168.50.0/26?",
                "Divide the network 10.10.0.0/22 into subnets of 100 hosts each"
            ],
            inputs=msg,
            label="Query Examples"
        )
        
        # Event handlers
        connect_btn.click(client.connect, inputs=server_url, outputs=status)
        tools_toggle.change(toggle_tools_display, inputs=tools_toggle, outputs=status)
        
        # Message sending (correct Gradio pattern)
        msg.submit(user, [msg, chatbot], [msg, chatbot], queue=False).then(
            bot, chatbot, chatbot
        ).then(lambda: "", None, msg)
        
        send_btn.click(user, [msg, chatbot], [msg, chatbot], queue=False).then(
            bot, chatbot, chatbot
        ).then(lambda: "", None, msg)
        
        clear_btn.click(lambda: ([], ""), None, [chatbot, msg])
        
    return demo

if __name__ == "__main__":
    # Check environment variables
    if not os.getenv("OPENROUTER_API_KEY"):
        print("⚠️  Warning: OPENROUTER_API_KEY not found. Please configure it in your .env file")
    
    if not os.getenv("OPENROUTER_BASE_URL"):
        print("ℹ️  Info: OPENROUTER_BASE_URL not configured, using default URL")
    
    interface = gradio_interface()
    interface.launch(debug=True, share=False, server_port=7880)