"""
IPMentor Chatbot Demo - Hugging Face Space Client

This is a demo MCP client that connects to the IPMentor Space at 
https://davidlms-ipmentor.hf.space to showcase conversational IPv4 networking
assistance using the Model Context Protocol (MCP). 

Powered by Mistral Small 3.1 24B Instruct model.
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

# Fixed MCP server URL for the demo
DEMO_MCP_SERVER_URL = "https://davidlms-ipmentor.hf.space/gradio_api/mcp/sse"

def load_system_prompt():
    """Load the system prompt from an external .md file."""
    try:
        with open("examples/chatbot_system_prompt.md", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        print("Warning: examples/chatbot_system_prompt.md not found, using default prompt")
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
        elif hasattr(obj, '__dict__'):
            # For objects with __dict__, try to serialize their attributes
            return safe_json_serialize(obj.__dict__)
        elif hasattr(obj, 'dict') and callable(obj.dict):
            # For Pydantic models or similar
            return safe_json_serialize(obj.dict())
        elif hasattr(obj, 'model_dump') and callable(obj.model_dump):
            # For newer Pydantic models
            return safe_json_serialize(obj.model_dump())
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
        self.server_url = DEMO_MCP_SERVER_URL
        
        # Configure OpenAI client for OpenRouter
        self.openai_client = OpenAI(
            api_key=os.getenv("OPENROUTER_API_KEY"),
            base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
        )
        self.model_name = "mistralai/mistral-small-3.1-24b-instruct"
    
    async def connect_async(self) -> str:
        """Connect to the demo MCP server"""
        try:
            print(f"Attempting to connect to demo server: {self.server_url}")
            
            # Configure MCP client
            self.mcp_client = MultiServerMCPClient({
                "ipmentor": {
                    "transport": "sse",
                    "url": self.server_url
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
                # Get input schema safely and ensure it's a proper JSON schema
                input_schema = {"type": "object", "properties": {}, "required": []}
                
                try:
                    # Try different ways to get the schema
                    schema_obj = None
                    if hasattr(tool, 'input_schema'):
                        schema_obj = tool.input_schema
                    elif hasattr(tool, 'inputSchema'):
                        schema_obj = tool.inputSchema
                    elif hasattr(tool, 'args_schema') and tool.args_schema:
                        # Get schema from Pydantic model
                        if hasattr(tool.args_schema, 'model_json_schema'):
                            schema_obj = tool.args_schema.model_json_schema()
                        elif hasattr(tool.args_schema, 'schema'):
                            schema_obj = tool.args_schema.schema()
                    
                    if schema_obj:
                        serialized_schema = safe_json_serialize(schema_obj)
                        if isinstance(serialized_schema, dict):
                            input_schema = serialized_schema
                        
                except Exception as e:
                    print(f"Warning: Could not serialize schema for {tool.name}: {e}")
                
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
                print(f"  Schema: {json.dumps(input_schema, indent=2)[:200]}...")
            
            tool_names = [tool["function"]["name"] for tool in self.tools]
            self.connection_status = "Connected"
            return f"✅ Connected to IPMentor demo server. Available tools: {', '.join(tool_names)}"
            
        except Exception as e:
            print(f"Detailed connection error: {type(e).__name__}: {str(e)}")
            import traceback
            traceback.print_exc()
            self.connection_status = "Error"
            return f"❌ Connection error: {str(e)}"
    
    def connect(self) -> str:
        """Synchronous wrapper for connecting"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(self.connect_async())
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
                
                # Extract file path from URL and build proper image URL
                if '/gradio_api/file=' in image_url:
                    file_path = image_url.split('/gradio_api/file=')[1]
                    # Get base URL from current MCP server URL
                    base_url = self.server_url.replace('/gradio_api/mcp/sse', '') if hasattr(self, 'server_url') else ''
                    
                    # Determine format from file extension, not status message
                    file_format = "svg" if file_path.lower().endswith('.svg') else "png"
                    
                    return {
                        "image_path": f"{base_url}/gradio_api/file={file_path}",
                        "status": status_msg,
                        "format": file_format
                    }
                
                return {"result": result}
            
            # Handle string results (JSON from other tools)
            try:
                if isinstance(result, str):
                    parsed_result = json.loads(result)
                    # Check if this is a generate_diagram result in JSON format
                    if isinstance(parsed_result, dict) and "image_path" in parsed_result:
                        # Get base URL from current MCP server URL
                        base_url = self.server_url.replace('/gradio_api/mcp/sse', '') if hasattr(self, 'server_url') else ''
                        # Update image path to full URL if it's a relative path
                        if not parsed_result["image_path"].startswith(('http://', 'https://')):
                            if base_url:
                                parsed_result["image_path"] = f"{base_url}/gradio_api/file={parsed_result['image_path']}"
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
        """Process message using OpenAI + MCP tools with agentic loop"""
        # Auto-connect if not connected
        if self.connection_status != "Connected":
            print("Auto-connecting to demo server...")
            connect_result = await self.connect_async()
            if self.connection_status != "Connected":
                yield history + [{"role": "assistant", "content": f"❌ Failed to connect to demo server: {connect_result}"}]
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
            # Agentic loop for tool calling
            max_iterations = 5  # Prevent infinite loops
            iteration = 0
            
            while iteration < max_iterations:
                iteration += 1
                print(f"🔄 Agentic iteration {iteration}")
                
                # Make LLM call
                response = self.openai_client.chat.completions.create(
                    model=self.model_name,
                    messages=openai_messages,
                    tools=self.tools if self.tools else None,
                    stream=False
                )
                
                choice = response.choices[0]
                message_obj = choice.message
                
                print(f"🔍 Model response: {message_obj}")
                print(f"🔍 Tool calls: {message_obj.tool_calls}")
                print(f"🔍 Message content: {message_obj.content}")
                
                # Check if model wrote JSON tool calls in content instead of using tool_calls
                fake_tool_calls = []
                if message_obj.content and not message_obj.tool_calls:
                    content = message_obj.content.strip()
                    # Look for JSON arrays that look like tool calls (simplified check)
                    if content.startswith('[{') and content.endswith('}]') and '"name"' in content:
                        print(f"🔍 Found potential fake tool calls in content")
                        try:
                            # Try to parse the JSON directly
                            parsed_tools = json.loads(content)
                            
                            # Convert to proper tool calls format
                            if isinstance(parsed_tools, list):
                                for tool_data in parsed_tools:
                                    if isinstance(tool_data, dict) and tool_data.get("name") in [t["function"]["name"] for t in self.tools]:
                                        fake_tool_calls.append({
                                            "function": {
                                                "name": tool_data["name"],
                                                "arguments": json.dumps(tool_data["arguments"])
                                            },
                                            "id": f"fake_call_{tool_data['name']}"
                                        })
                        except Exception as e:
                            print(f"Error parsing fake tool calls: {e}")
                
                # Process tool calls if any
                if message_obj.tool_calls or fake_tool_calls:
                    actual_tool_calls = message_obj.tool_calls or fake_tool_calls
                    
                    # Add assistant message with tool calls to conversation
                    if message_obj.tool_calls:
                        openai_messages.append({
                            "role": "assistant",
                            "content": message_obj.content,
                            "tool_calls": message_obj.tool_calls
                        })
                    else:
                        openai_messages.append({
                            "role": "assistant", 
                            "content": message_obj.content
                        })
                    
                    # Process each tool call sequentially
                    for tool_call in actual_tool_calls:
                        # Handle both real tool_call objects and fake dict tool calls
                        if hasattr(tool_call, 'function'):
                            tool_name = tool_call.function.name
                            tool_args_str = tool_call.function.arguments
                            tool_call_id = tool_call.id
                        else:
                            tool_name = tool_call["function"]["name"]
                            tool_args_str = tool_call["function"]["arguments"]
                            tool_call_id = tool_call.get('id', f'fake_call_{tool_name}')
                        
                        try:
                            tool_args = json.loads(tool_args_str)
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
                                    "id": f"tool_call_{iteration}_{tool_name}"
                                }
                            })
                            yield current_history
                        
                        # Call the tool
                        print(f"🔧 Executing tool (iteration {iteration}): {tool_name}")
                        print(f"📝 Parameters: {tool_args}")
                        
                        tool_result = await self.call_tool_async(tool_name, tool_args)
                        
                        if SHOW_TOOLS:
                            # Update tool status
                            tool_id = f"tool_call_{iteration}_{tool_name}"
                            for i, msg in enumerate(current_history):
                                if (isinstance(msg, dict) and 
                                    msg.get("metadata", {}).get("id") == tool_id and 
                                    msg.get("metadata", {}).get("status") == "pending"):
                                    # Update the existing message status
                                    current_history[i] = {
                                        "role": "assistant",
                                        "content": f"✅ Tool executed: **{tool_name}**" if not (isinstance(tool_result, dict) and "error" in tool_result) else f"❌ Tool error: **{tool_name}**",
                                        "metadata": {
                                            "title": f"Tool: {tool_name}",
                                            "log": f"Parameters: {safe_json_dumps(tool_args, ensure_ascii=False, indent=2)}",
                                            "status": "done",
                                            "id": tool_id
                                        }
                                    }
                                    break
                            yield current_history
                        
                        # Add tool result to conversation
                        openai_messages.append({
                            "role": "tool",
                            "content": safe_json_dumps(tool_result, ensure_ascii=False),
                            "tool_call_id": tool_call_id,
                            "name": tool_name
                        })
                        
                        # Process tool result for display
                        if isinstance(tool_result, dict) and "error" not in tool_result:
                            # Safely serialize result
                            result_serialized = safe_json_serialize(tool_result)
                            
                            # Look for image file paths or URLs
                            image_path = None
                            
                            # Look in deserialized result first
                            if isinstance(result_serialized, dict):
                                for key in ['image_path', 'svg_path', 'path', 'file_path']:
                                    if key in result_serialized:
                                        potential_path = result_serialized[key]
                                        if isinstance(potential_path, str):
                                            # Check if it's a URL or local file that exists
                                            if potential_path.startswith(('http://', 'https://')) or os.path.exists(potential_path):
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
                                
                                # Don't show additional technical information for diagrams
                                # The user can see the diagram directly, no need for technical details
                            else:
                                # Show result in JSON format  
                                formatted_result = safe_json_dumps(result_serialized, ensure_ascii=False, indent=2)
                                json_content = "```json\n" + formatted_result + "\n```"
                                current_history.append({
                                    "role": "assistant",
                                    "content": json_content
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
                
                else:
                    # No tool calls, add final response and break
                    openai_messages.append({
                        "role": "assistant",
                        "content": message_obj.content
                    })
                    
                    # Add final response directly (no streaming to avoid parsing issues)
                    if message_obj.content:
                        current_history.append({
                            "role": "assistant", 
                            "content": message_obj.content
                        })
                        yield current_history
                    
                    break
            
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
    with gr.Blocks(title="IPMentor Chatbot Demo") as demo:
        # Header with logo
        gr.Image("https://huggingface.co/spaces/davidlms/ipmentor/resolve/main/assets/header.png", show_label=False, interactive=False, container=False, height=120)
        
        # Description
        gr.Markdown("""
        **IPMentor Chatbot Demo** - MCP Client Example
        
        This is a demo MCP (Model Context Protocol) client that connects to the **IPMentor Space** at 
        [https://davidlms-ipmentor.hf.space](https://davidlms-ipmentor.hf.space) to showcase conversational 
        IPv4 networking assistance.
        
        **Features:**
        - 🤖 **AI Model**: Mistral Small 3.1 24B Instruct 
        - 🔧 **Tools**: IP analysis, subnet calculations, and network diagram generation
        
        **Getting Started:** Just start chatting! The system will automatically connect to the IPMentor server 
        and provide access to professional networking tools through natural conversation.
        """)
        
        # Tools toggle only (no connection UI)
        with gr.Row():
            tools_toggle = gr.Checkbox(
                label="Show tool execution details",
                value=SHOW_TOOLS,
                info="Shows detailed information about tool calls and parameters"
            )
        
        chatbot = gr.Chatbot(
            value=[], 
            height=400,
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
        tools_toggle.change(toggle_tools_display, inputs=tools_toggle, outputs=[])
        
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
    interface.launch(debug=True, share=False)