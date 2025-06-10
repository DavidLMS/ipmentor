#!/usr/bin/env python3
"""
IPMentor Exercise Generator - Agentic Subnetting Exercise Creator
Creates validated subnetting exercises using IPMentor MCP tools
"""

import asyncio
import os
import json
import re
from typing import List, Dict, Any
from dotenv import load_dotenv
import tempfile
from pathlib import Path
import zipfile
import requests

import gradio as gr
from openai import OpenAI
import markdown
import pdfkit

from langchain_mcp_adapters.client import MultiServerMCPClient

# Load environment variables
load_dotenv()

# CONFIGURATION

# Fixed MCP server URL for IPMentor
IPMENTOR_MCP_SERVER_URL = "https://agents-mcp-hackathon-ipmentor.hf.space/gradio_api/mcp/sse"

# Default exercise templates by language
DEFAULT_TEMPLATES = {
    "English": "A company needs to divide the network {network} for its {num_departments} departments. Each department requires approximately {hosts} hosts. Design the appropriate subnetting scheme.",
    "Spanish": "Una empresa necesita dividir la red {network} para sus {num_departments} departamentos. Cada departamento requiere aproximadamente {hosts} hosts. Diseña el esquema de subnetting apropiado.",
    "French": "Une entreprise doit diviser le réseau {network} pour ses {num_departments} départements. Chaque département nécessite environ {hosts} hôtes. Concevez le schéma de sous-réseaux approprié.",
    "German": "Ein Unternehmen muss das Netzwerk {network} für seine {num_departments} Abteilungen aufteilen. Jede Abteilung benötigt etwa {hosts} Hosts. Entwerfen Sie das entsprechende Subnetting-Schema."
}

# Exercise generation prompts by language
EXERCISE_GENERATION_PROMPTS = {
    "English": """Generate {num_exercises} unique subnetting exercises with {difficulty} difficulty level.

Difficulty guidelines:
- easy: 2 subnets, no VLSM (equal subnet sizes)
- medium: 3-4 subnets, mix of max_subnets, max_hosts_per_subnet, and some VLSM
- difficult: 5-10 subnets, primarily VLSM with varied host requirements

Template to follow: {template}

For each exercise, provide:
1. A realistic network scenario (company, school, etc.)
2. Network address (use private ranges: 192.168.x.0/24, 10.x.0.0/16, 172.16-31.x.0/20)
3. Specific subnet requirements (number of hosts per subnet or departments)
4. Clear instructions

Return a JSON array with this structure:
[
  {{
    "exercise_number": 1,
    "title": "Exercise title",
    "scenario": "Detailed scenario description",
    "network": "192.168.1.0/24",
    "requirements": "Specific subnetting requirements",
    "method": "max_subnets|max_hosts_per_subnet|vlsm",
    "hosts_list": "50,30,20" (for VLSM) or empty for other methods,
    "number": 4 (for non-VLSM methods)
  }}
]

Make exercises realistic and educational.""",

    "Spanish": """Genera {num_exercises} ejercicios únicos de subnetting con nivel de dificultad {difficulty}.

Guías de dificultad:
- easy: 2 subredes, sin VLSM (tamaños de subred iguales)
- medium: 3-4 subredes, mezcla de max_subnets, max_hosts_per_subnet, y algo de VLSM
- difficult: 5-10 subredes, principalmente VLSM con requisitos de hosts variados

Plantilla a seguir: {template}

Para cada ejercicio, proporciona:
1. Un escenario de red realista (empresa, escuela, etc.)
2. Dirección de red (usa rangos privados: 192.168.x.0/24, 10.x.0.0/16, 172.16-31.x.0/20)
3. Requisitos específicos de subred (número de hosts por subred o departamentos)
4. Instrucciones claras

Devuelve un array JSON con esta estructura:
[
  {{
    "exercise_number": 1,
    "title": "Título del ejercicio",
    "scenario": "Descripción detallada del escenario",
    "network": "192.168.1.0/24",
    "requirements": "Requisitos específicos de subnetting",
    "method": "max_subnets|max_hosts_per_subnet|vlsm",
    "hosts_list": "50,30,20" (para VLSM) o vacío para otros métodos,
    "number": 4 (para métodos no-VLSM)
  }}
]

Haz los ejercicios realistas y educativos.""",

    "French": """Générez {num_exercises} exercices uniques de sous-réseaux avec un niveau de difficulté {difficulty}.

Directives de difficulté:
- easy: 2 sous-réseaux, pas de VLSM (tailles de sous-réseaux égales)
- medium: 3-4 sous-réseaux, mélange de max_subnets, max_hosts_per_subnet, et un peu de VLSM
- difficult: 5-10 sous-réseaux, principalement VLSM avec des exigences d'hôtes variées

Modèle à suivre: {template}

Pour chaque exercice, fournissez:
1. Un scénario de réseau réaliste (entreprise, école, etc.)
2. Adresse réseau (utilisez des plages privées: 192.168.x.0/24, 10.x.0.0/16, 172.16-31.x.0/20)
3. Exigences spécifiques de sous-réseau (nombre d'hôtes par sous-réseau ou départements)
4. Instructions claires

Retournez un tableau JSON avec cette structure:
[
  {{
    "exercise_number": 1,
    "title": "Titre de l'exercice",
    "scenario": "Description détaillée du scénario",
    "network": "192.168.1.0/24",
    "requirements": "Exigences spécifiques de sous-réseaux",
    "method": "max_subnets|max_hosts_per_subnet|vlsm",
    "hosts_list": "50,30,20" (pour VLSM) ou vide pour d'autres méthodes,
    "number": 4 (pour les méthodes non-VLSM)
  }}
]

Rendez les exercices réalistes et éducatifs.""",

    "German": """Generieren Sie {num_exercises} einzigartige Subnetting-Übungen mit Schwierigkeitsgrad {difficulty}.

Schwierigkeitsrichtlinien:
- easy: 2 Subnetze, kein VLSM (gleiche Subnetzgrößen)
- medium: 3-4 Subnetze, Mischung aus max_subnets, max_hosts_per_subnet, und etwas VLSM
- difficult: 5-10 Subnetze, hauptsächlich VLSM mit unterschiedlichen Host-Anforderungen

Zu befolgende Vorlage: {template}

Für jede Übung stellen Sie bereit:
1. Ein realistisches Netzwerkszenario (Unternehmen, Schule, etc.)
2. Netzwerkadresse (verwenden Sie private Bereiche: 192.168.x.0/24, 10.x.0.0/16, 172.16-31.x.0/20)
3. Spezifische Subnetz-Anforderungen (Anzahl Hosts pro Subnetz oder Abteilungen)
4. Klare Anweisungen

Geben Sie ein JSON-Array mit dieser Struktur zurück:
[
  {{
    "exercise_number": 1,
    "title": "Übungstitel",
    "scenario": "Detaillierte Szenariobeschreibung",
    "network": "192.168.1.0/24",
    "requirements": "Spezifische Subnetting-Anforderungen",
    "method": "max_subnets|max_hosts_per_subnet|vlsm",
    "hosts_list": "50,30,20" (für VLSM) oder leer für andere Methoden,
    "number": 4 (für Nicht-VLSM-Methoden)
  }}
]

Machen Sie die Übungen realistisch und lehrreich."""
}

# UTILITY FUNCTIONS

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
            return safe_json_serialize(obj.__dict__)
        elif hasattr(obj, 'dict') and callable(obj.dict):
            return safe_json_serialize(obj.dict())
        elif hasattr(obj, 'model_dump') and callable(obj.model_dump):
            return safe_json_serialize(obj.model_dump())
        else:
            return str(obj)
    except Exception:
        return str(obj)

def safe_json_dumps(obj, **kwargs):
    """Safe JSON dumps that handles non-serializable objects."""
    try:
        return json.dumps(safe_json_serialize(obj), **kwargs)
    except Exception as e:
        return json.dumps({"error": f"Error serializing: {str(e)}", "data": str(obj)}, **kwargs)

def markdown_to_pdf(markdown_content: str, output_path: str) -> str:
    """Convert markdown to PDF using pdfkit."""
    try:
        # Convert markdown to HTML and add exercise break classes
        html_content = markdown.markdown(markdown_content, extensions=['tables', 'fenced_code'])
        
        # Add CSS classes for better page breaks
        import re
        # Add exercise-break class to h2 elements (exercises)
        html_content = re.sub(r'<h2>', r'<h2 class="exercise-break">', html_content)
        
        # Get the logo path
        logo_path = Path(__file__).parent.parent / "assets" / "logo.svg"
        logo_exists = logo_path.exists()
        
        # Add CSS styling with IPMentor branding colors
        styled_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                @page {{
                    margin: 1in 1in 100px 1in;
                }}
                
                body {{ 
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
                    line-height: 1.6; 
                    margin: 0;
                    padding: 20px;
                    color: #333;
                    background: #fefefe;
                }}
                
                h1 {{ 
                    color: #FC8100; 
                    border-bottom: 4px solid #FED200;
                    padding-bottom: 15px;
                    margin-bottom: 30px;
                    font-size: 2.2em;
                    font-weight: bold;
                }}
                
                h2 {{ 
                    color: #FC8100; 
                    border-bottom: 3px solid #FFCB00;
                    padding-bottom: 8px;
                    margin-top: 40px;
                    margin-bottom: 20px;
                    font-size: 1.5em;
                    page-break-after: avoid;
                }}
                
                h3 {{ 
                    color: #FE8100; 
                    margin-top: 25px;
                    margin-bottom: 15px;
                    font-size: 1.2em;
                }}
                
                p {{
                    margin-bottom: 15px;
                    text-align: justify;
                }}
                
                em {{
                    color: #F05600;
                    font-style: italic;
                }}
                
                strong {{
                    color: #FE8100;
                }}
                
                a {{
                    color: #F05600;
                    text-decoration: none;
                    border-bottom: 1px dotted #F05600;
                }}
                
                a:hover {{
                    border-bottom: 1px solid #F05600;
                }}
                
                img {{ 
                    max-width: 85%; 
                    max-height: 450px;
                    height: auto; 
                    display: block;
                    margin: 25px auto;
                    border: 2px solid #FED200;
                    border-radius: 8px;
                    box-shadow: 0 4px 8px rgba(254, 129, 0, 0.1);
                }}
                
                code {{
                    background: #FFF4E6;
                    color: #FC8100;
                    padding: 2px 6px;
                    border-radius: 4px;
                    font-family: 'Courier New', monospace;
                    border: 1px solid #FED200;
                }}
                
                pre {{ 
                    background: #FFF8F0; 
                    padding: 20px; 
                    border-radius: 8px;
                    border-left: 6px solid #F05600;
                    margin: 20px 0;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }}
                
                hr {{
                    border: none;
                    height: 3px;
                    background: linear-gradient(90deg, #F05600, #FED200, #FFCB00);
                    margin: 30px 0;
                    border-radius: 2px;
                }}
                
                
                .exercise-break {{
                    page-break-before: always;
                    margin-top: 0;
                }}
                
                .exercise-break:first-of-type {{
                    page-break-before: avoid;
                }}
            </style>
        </head>
        <body>
        {html_content}
        
        </body>
        </html>
        """
        
        # Create temporary footer HTML file with logo
        footer_html_path = None
        if logo_exists:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as footer_file:
                footer_html_path = footer_file.name
                footer_content = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <meta charset="UTF-8">
                    <style>
                        body {{
                            margin: 0;
                            padding: 8px;
                            text-align: center;
                        }}
                        .logo {{
                            height: 38px;
                            width: auto;
                        }}
                    </style>
                </head>
                <body>
                    <img src="{logo_path.as_uri()}" alt="IPMentor" class="logo">
                </body>
                </html>
                """
                footer_file.write(footer_content)
        
        # Configure PDF options
        options = {
            'page-size': 'A4',
            'margin-top': '1in',
            'margin-right': '1in',
            'margin-bottom': '1in',
            'margin-left': '1in',
            'encoding': "UTF-8",
            'no-outline': None,
            'enable-local-file-access': None,
            'print-media-type': None,
            'disable-smart-shrinking': None
        }
        
        # Add footer if logo exists
        if footer_html_path:
            options['footer-html'] = footer_html_path
            options['footer-spacing'] = '5'
        
        # Generate PDF
        try:
            pdfkit.from_string(styled_html, output_path, options=options)
        finally:
            # Clean up temporary footer file
            if footer_html_path and os.path.exists(footer_html_path):
                os.remove(footer_html_path)
        
        return output_path
        
    except Exception as e:
        raise Exception(f"PDF generation failed: {str(e)}")

# MCP CLIENT CLASS

class ExerciseGenerator:
    def __init__(self):
        self.mcp_client = None
        self.tools = []
        self.connection_status = "Disconnected"
        
        # Configure OpenAI client for OpenRouter with Mistral Medium 3
        self.openai_client = OpenAI(
            api_key=os.getenv("OPENROUTER_API_KEY"),
            base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
        )
        self.model_name = "mistralai/mistral-medium-3"
    
    async def connect_to_ipmentor(self) -> str:
        """Connect to IPMentor MCP server"""
        try:
            print(f"Connecting to IPMentor server: {IPMENTOR_MCP_SERVER_URL}")
            
            self.mcp_client = MultiServerMCPClient({
                "ipmentor": {
                    "transport": "sse",
                    "url": IPMENTOR_MCP_SERVER_URL
                }
            })
            
            # Get available tools
            mcp_tools = await self.mcp_client.get_tools()
            
            # Convert tools to OpenAI format
            self.tools = []
            for tool in mcp_tools:
                input_schema = {"type": "object", "properties": {}, "required": []}
                
                try:
                    schema_obj = None
                    if hasattr(tool, 'input_schema'):
                        schema_obj = tool.input_schema
                    elif hasattr(tool, 'args_schema') and tool.args_schema:
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
            
            self.connection_status = "Connected"
            tool_names = [tool["function"]["name"] for tool in self.tools]
            return f"✅ Connected to IPMentor. Tools: {', '.join(tool_names)}"
            
        except Exception as e:
            self.connection_status = "Error"
            return f"❌ Connection error: {str(e)}"
    
    async def call_mcp_tool(self, tool_name: str, tool_args: dict) -> Any:
        """Call a tool from the MCP server"""
        try:
            if not self.mcp_client:
                return {"error": "MCP client not initialized"}
            
            mcp_tools = await self.mcp_client.get_tools()
            tool_to_call = None
            
            for tool in mcp_tools:
                if tool.name == tool_name:
                    tool_to_call = tool
                    break
            
            if not tool_to_call:
                return {"error": f"Tool {tool_name} not found"}
            
            # Call the tool
            result = None
            if hasattr(tool_to_call, 'ainvoke'):
                result = await tool_to_call.ainvoke(tool_args)
            elif hasattr(tool_to_call, 'acall'):
                result = await tool_to_call.acall(tool_args)
            elif hasattr(tool_to_call, 'func'):
                result = tool_to_call.func(**tool_args)
            else:
                return {"error": f"No compatible method found for tool {tool_name}"}
            
            # Process result
            if isinstance(result, list) and len(result) == 2:
                # Handle diagram generation result
                image_url = result[0]
                status_msg = result[1]
                
                if '/gradio_api/file=' in image_url:
                    file_path = image_url.split('/gradio_api/file=')[1]
                    base_url = IPMENTOR_MCP_SERVER_URL.replace('/gradio_api/mcp/sse', '')
                    
                    return {
                        "image_path": f"{base_url}/gradio_api/file={file_path}",
                        "status": status_msg,
                        "format": "svg" if file_path.lower().endswith('.svg') else "png"
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
            return {"error": f"Error calling tool {tool_name}: {str(e)}"}
    
    def generate_exercises_with_llm(self, num_exercises: int, difficulty: str, language: str, template: str) -> List[Dict]:
        """Generate exercises using LLM"""
        try:
            print(f"Starting LLM generation: {num_exercises} exercises, {difficulty} difficulty, {language} language")
            
            # Use default template if none provided
            if not template.strip():
                template = DEFAULT_TEMPLATES.get(language, DEFAULT_TEMPLATES["English"])
            
            print(f"Using template: {template[:100]}...")
            
            # Get the prompt for the language
            prompt = EXERCISE_GENERATION_PROMPTS.get(language, EXERCISE_GENERATION_PROMPTS["English"])
            print(f"Using prompt for language: {language}")
            
            formatted_prompt = prompt.format(
                num_exercises=num_exercises,
                difficulty=difficulty,
                template=template
            )
            print(f"Formatted prompt length: {len(formatted_prompt)}")
            
            response = self.openai_client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "You are an expert networking instructor who creates realistic subnetting exercises. Always return valid JSON arrays."},
                    {"role": "user", "content": formatted_prompt}
                ],
                temperature=0.7
            )
            
            if not response.choices or len(response.choices) == 0:
                print("No choices in LLM response")
                return []
            
            print(f"Got response with {len(response.choices)} choices")
            
            content = response.choices[0].message.content
            if not content:
                print("Empty content in LLM response")
                return []
            
            content = content.strip()
            print(f"Response content length: {len(content)}")
            print(f"First 200 chars: {content[:200]}")
            
            # Extract JSON from response (handle markdown code blocks)
            json_match = re.search(r'```(?:json)?\s*(\[.*?\])\s*```', content, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
                print("Found JSON in code blocks")
            else:
                # Try to find JSON array directly
                json_match = re.search(r'(\[.*?\])', content, re.DOTALL)
                if json_match:
                    json_str = json_match.group(1)
                    print("Found JSON array directly")
                else:
                    json_str = content
                    print("Using full content as JSON")
            
            print(f"JSON string length: {len(json_str)}")
            print(f"JSON preview: {json_str[:200]}")
            
            exercises = json.loads(json_str)
            print(f"Successfully parsed JSON. Type: {type(exercises)}")
            
            # Validate that exercises is a list
            if not isinstance(exercises, list):
                print(f"Expected list but got {type(exercises)}")
                return []
            
            print(f"Got {len(exercises)} exercises from LLM")
            
            # Validate each exercise has required fields
            valid_exercises = []
            for i, exercise in enumerate(exercises):
                print(f"Processing exercise {i+1}: {type(exercise)}")
                
                if not isinstance(exercise, dict):
                    print(f"Exercise {i} is not a dictionary")
                    continue
                
                print(f"Exercise {i+1} keys: {list(exercise.keys())}")
                
                required_fields = ['exercise_number', 'title', 'scenario', 'network', 'requirements', 'method']
                missing_fields = [f for f in required_fields if f not in exercise]
                
                if not missing_fields:
                    # Ensure proper data types
                    if 'number' not in exercise:
                        exercise['number'] = 2
                    if 'hosts_list' not in exercise:
                        exercise['hosts_list'] = ""
                    valid_exercises.append(exercise)
                    print(f"Exercise {i+1} is valid")
                else:
                    print(f"Exercise {i+1} missing required fields: {missing_fields}")
            
            print(f"Returning {len(valid_exercises)} valid exercises")
            return valid_exercises
            
        except json.JSONDecodeError as e:
            print(f"JSON parsing error: {e}")
            print(f"Content that failed to parse: {content if 'content' in locals() else 'No content'}")
            return []
        except Exception as e:
            print(f"Error generating exercises: {e}")
            return []
    
    async def validate_and_fix_exercise(self, exercise: Dict) -> Dict:
        """Validate exercise using MCP tools and fix if needed"""
        max_attempts = 3
        
        for attempt in range(max_attempts):
            try:
                print(f"Validating exercise {exercise['exercise_number']} (attempt {attempt + 1})")
                
                # Prepare tool arguments based on method
                if exercise["method"] == "vlsm":
                    tool_args = {
                        "network": exercise["network"],
                        "division_type": "vlsm",
                        "hosts_per_subnet": exercise["hosts_list"],
                        "number": ""  # Not needed for VLSM
                    }
                else:
                    tool_args = {
                        "network": exercise["network"],
                        "division_type": exercise["method"],
                        "number": str(exercise["number"]),
                        "hosts_per_subnet": ""
                    }
                
                # Test subnet calculation
                result = await self.call_mcp_tool("ipmentor_subnet_calculator", tool_args)
                
                if "error" not in result:
                    print(f"✅ Exercise {exercise['exercise_number']} is valid")
                    return exercise
                
                print(f"❌ Exercise {exercise['exercise_number']} failed validation: {result.get('error', 'Unknown error')}")
                
                # Try to fix the exercise
                if attempt < max_attempts - 1:
                    exercise = await self.fix_exercise(exercise, result.get('error', ''))
                
            except Exception as e:
                print(f"Error validating exercise: {e}")
                if attempt < max_attempts - 1:
                    # Simple fallback: reduce requirements
                    if exercise["method"] == "vlsm" and exercise["hosts_list"]:
                        hosts = [max(1, int(h)//2) for h in exercise["hosts_list"].split(",")]
                        exercise["hosts_list"] = ",".join(map(str, hosts))
                    elif exercise["method"] != "vlsm":
                        exercise["number"] = max(2, exercise["number"] // 2)
        
        print(f"⚠️ Could not validate exercise {exercise['exercise_number']} after {max_attempts} attempts")
        return exercise
    
    async def fix_exercise(self, exercise: Dict, error: str) -> Dict:
        """Fix exercise based on validation error"""
        print(f"Attempting to fix exercise {exercise['exercise_number']}: {error}")
        
        # Keep track of what was changed to update the scenario
        changes_made = []
        original_hosts = exercise.get("hosts_list", "")
        original_number = exercise.get("number", 0)
        original_network = exercise.get("network", "")
        
        # Simple heuristic fixes
        if "too many" in error.lower() or "cannot allocate" in error.lower():
            if exercise["method"] == "vlsm" and exercise["hosts_list"]:
                # Reduce host requirements
                hosts = [max(1, int(h)//2) for h in exercise["hosts_list"].split(",")]
                exercise["hosts_list"] = ",".join(map(str, hosts))
                print(f"Reduced VLSM hosts to: {exercise['hosts_list']}")
                changes_made.append("hosts_reduced")
            elif exercise["method"] != "vlsm":
                # Reduce number of subnets
                exercise["number"] = max(2, exercise["number"] // 2)
                print(f"Reduced subnet count to: {exercise['number']}")
                changes_made.append("subnets_reduced")
        
        elif "invalid" in error.lower():
            # Try changing network to a larger one
            if "/24" in exercise["network"]:
                exercise["network"] = exercise["network"].replace("/24", "/22")
            elif "/22" in exercise["network"]:
                exercise["network"] = exercise["network"].replace("/22", "/20")
            print(f"Changed network to: {exercise['network']}")
            changes_made.append("network_expanded")
        
        # Update scenario and requirements to reflect the changes
        if changes_made:
            exercise = await self.update_exercise_description(exercise, changes_made, original_hosts, original_number, original_network)
        
        return exercise
    
    async def update_exercise_description(self, exercise: Dict, changes_made: List[str], original_hosts: str, original_number: int, original_network: str) -> Dict:
        """Update exercise scenario and requirements to reflect corrections made using LLM"""
        try:
            print(f"Updating exercise description for changes: {changes_made}")
            
            # Extract current values
            current_network = exercise.get("network", "")
            current_method = exercise.get("method", "")
            original_scenario = exercise.get("scenario", "")
            original_title = exercise.get("title", "")
            
            # Detect language from existing scenario
            detected_language = "English"  # default
            if "empresa" in original_scenario.lower() or "departamento" in original_scenario.lower() or "universidad" in original_scenario.lower():
                detected_language = "Spanish"
            elif "entreprise" in original_scenario.lower() or "département" in original_scenario.lower() or "université" in original_scenario.lower():
                detected_language = "French"
            elif "unternehmen" in original_scenario.lower() or "abteilung" in original_scenario.lower() or "universität" in original_scenario.lower():
                detected_language = "German"
            
            # Use intelligent number substitution instead of LLM rewriting
            if "hosts_reduced" in changes_made and current_method == "vlsm":
                current_hosts = exercise["hosts_list"]
                
                # Combine scenario and requirements for complete text processing
                original_requirements = exercise.get("requirements", "")
                full_text = f"{original_scenario} {original_requirements}".strip()
                
                # Intelligent number replacement in the complete text
                updated_full_text = self.smart_replace_host_numbers(full_text, exercise["hosts_list"])
                
                # Simple approach: put everything in scenario and clear requirements to avoid duplication
                exercise["scenario"] = updated_full_text
                exercise["requirements"] = ""
                
                print(f"Updated scenario using smart substitution: {exercise['scenario'][:100]}...")
                if exercise.get("requirements"):
                    print(f"Updated requirements: {exercise['requirements'][:100]}...")
            
            elif "subnets_reduced" in changes_made and current_method != "vlsm":
                current_number = exercise["number"]
                
                # Simple update for non-VLSM (less complex)
                # Simple replacement for subnet count
                exercise["scenario"] = original_scenario.replace(str(original_number), str(current_number))
                
                print(f"Updated scenario to reflect corrected subnet count: {current_number}")
            
            elif "network_expanded" in changes_made:
                # Simple network replacement
                exercise["scenario"] = exercise["scenario"].replace(original_network, current_network)
                
                print(f"Updated scenario to reflect expanded network: {current_network}")
            
        except Exception as e:
            print(f"Error updating exercise description: {e}")
            # Fallback to original scenario if LLM fails
            if "scenario" not in exercise or not exercise["scenario"]:
                exercise["scenario"] = original_scenario
        
        return exercise
    
    def smart_replace_host_numbers(self, scenario: str, new_hosts: str) -> str:
        """Replace host numbers by matching largest to largest, avoiding IP addresses"""
        import re
        
        print(f"Smart replacement input - FULL Scenario: {scenario}")
        print(f"New hosts: {new_hosts}")
        
        # Convert new hosts to list and sort descending (largest first)
        new_host_list = sorted([int(h) for h in new_hosts.split(",")], reverse=True)
        print(f"New hosts sorted (largest first): {new_host_list}")
        
        # First, temporarily replace IP addresses to protect them
        ip_pattern = r'\d+\.\d+\.\d+\.\d+(?:/\d+)?'  # Match IP addresses with optional CIDR
        ip_matches = re.findall(ip_pattern, scenario)
        protected_scenario = scenario
        ip_placeholders = {}
        
        for i, ip in enumerate(ip_matches):
            placeholder = f"__IP_PLACEHOLDER_{i}__"
            protected_scenario = protected_scenario.replace(ip, placeholder, 1)
            ip_placeholders[placeholder] = ip
            print(f"Protected IP: {ip} -> {placeholder}")
        
        # Find all numbers that have spaces before and after (standalone numbers)
        # This avoids IP addresses and other connected numbers
        number_pattern = r'\s(\d+)\s'
        number_matches = re.findall(number_pattern, protected_scenario)
        
        print(f"All numbers found: {number_matches}")
        
        # Convert to integers, remove duplicates, and sort descending
        unique_numbers = list(set([int(n) for n in number_matches if n.isdigit()]))
        old_numbers = sorted(unique_numbers, reverse=True)
        print(f"Old numbers sorted (largest first): {old_numbers}")
        
        # Match largest old number with largest new number
        updated_scenario = protected_scenario
        replacements_made = 0
        
        for i, old_num in enumerate(old_numbers):
            if i < len(new_host_list):
                new_num = new_host_list[i]
                
                # Try different replacement patterns in order of specificity
                replacement_patterns = [
                    (f"{old_num} hosts", f"{new_num} hosts"),
                    (f"({old_num} hosts", f"({new_num} hosts"),
                    (f" {old_num} ", f" {new_num} "),
                    (str(old_num), str(new_num))  # Last resort: direct number replacement
                ]
                
                replaced = False
                for old_pattern, new_pattern in replacement_patterns:
                    if old_pattern in updated_scenario and not replaced:
                        # Count occurrences to be careful
                        count = updated_scenario.count(old_pattern)
                        if count == 1:  # Only replace if there's exactly one occurrence
                            updated_scenario = updated_scenario.replace(old_pattern, new_pattern)
                            print(f"Replaced '{old_pattern}' with '{new_pattern}'")
                            replacements_made += 1
                            replaced = True
                            break
                        elif count > 1:
                            # Replace only the first occurrence
                            updated_scenario = updated_scenario.replace(old_pattern, new_pattern, 1)
                            print(f"Replaced first occurrence of '{old_pattern}' with '{new_pattern}' ({count} total found)")
                            replacements_made += 1
                            replaced = True
                            break
                
                if not replaced:
                    print(f"Could not replace {old_num}")
            else:
                print(f"No replacement value for {old_num}")
        
        # Restore IP addresses
        for placeholder, ip in ip_placeholders.items():
            updated_scenario = updated_scenario.replace(placeholder, ip)
            print(f"Restored IP: {placeholder} -> {ip}")
        
        print(f"Made {replacements_made} total replacements")
        print(f"Final result: {updated_scenario}")
        return updated_scenario
    
    async def create_zip_with_images(self, markdown_content: str, image_urls: List[str]) -> str:
        """Create ZIP file with markdown and downloaded images"""
        try:
            # Create temporary directory for files
            temp_dir = tempfile.mkdtemp()
            
            # Download images and update markdown
            updated_markdown = markdown_content
            image_files = []
            
            for i, image_url in enumerate(image_urls, 1):
                try:
                    print(f"Downloading image {i}: {image_url}")
                    response = requests.get(image_url, timeout=30)
                    response.raise_for_status()
                    
                    # Determine file extension
                    if image_url.lower().endswith('.svg'):
                        ext = '.svg'
                    else:
                        ext = '.png'
                    
                    # Create local filename
                    image_filename = f"diagram_{i}{ext}"
                    image_path = Path(temp_dir) / image_filename
                    
                    # Save image
                    with open(image_path, 'wb') as f:
                        f.write(response.content)
                    
                    # Update markdown to reference local file
                    updated_markdown = updated_markdown.replace(image_url, image_filename)
                    image_files.append(image_filename)
                    
                    print(f"Downloaded: {image_filename}")
                    
                except Exception as img_error:
                    print(f"Failed to download image {i}: {img_error}")
            
            # Save updated markdown
            markdown_filename = "exercises.md"
            markdown_path = Path(temp_dir) / markdown_filename
            with open(markdown_path, 'w', encoding='utf-8') as f:
                f.write(updated_markdown)
            
            # Create ZIP file
            zip_filename = tempfile.NamedTemporaryFile(suffix=".zip", delete=False)
            zip_path = zip_filename.name
            zip_filename.close()
            
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Add markdown file
                zipf.write(markdown_path, markdown_filename)
                
                # Add image files
                for image_file in image_files:
                    image_path = Path(temp_dir) / image_file
                    if image_path.exists():
                        zipf.write(image_path, image_file)
            
            print(f"Created ZIP: {zip_path}")
            
            # Clean up temp directory
            import shutil
            shutil.rmtree(temp_dir)
            
            return zip_path
            
        except Exception as e:
            print(f"Error creating ZIP: {e}")
            return ""
    
    async def generate_diagram_for_exercise(self, exercise: Dict) -> tuple[str, str]:
        """Generate network diagram for exercise using requested hosts, not optimal calculated hosts"""
        """Returns tuple of (markdown_for_display, image_url_for_download)"""
        try:
            print(f"Generating diagram for exercise {exercise['exercise_number']}")
            
            # Use the original requested hosts from the exercise, not the optimal calculated ones
            if exercise["method"] == "vlsm":
                # For VLSM, use the original hosts_list directly
                hosts_list = exercise["hosts_list"]
            else:
                # For max_subnets and max_hosts_per_subnet, we need to extract the original requirement
                # Parse the requirements to find the requested host count
                requirements = exercise.get("requirements", "").lower()
                hosts_requested = None
                
                # Look for host requirements in the requirements text
                import re
                host_matches = re.findall(r'(\d+)\s*hosts?', requirements) if requirements else []
                if host_matches:
                    # Use the first host count found
                    hosts_requested = int(host_matches[0])
                else:
                    # Fallback: look in scenario text
                    scenario = exercise.get("scenario", "").lower()
                    host_matches = re.findall(r'(\d+)\s*(?:hosts?|dispositivos?|devices?)', scenario) if scenario else []
                    if host_matches:
                        hosts_requested = int(host_matches[0])
                
                if hosts_requested:
                    # Create host list with the requested count for each subnet
                    num_subnets = exercise.get("number", 2)
                    hosts_list = ",".join([str(hosts_requested)] * num_subnets)
                    print(f"Using requested hosts: {hosts_list} instead of optimal calculation")
                else:
                    print("Could not find requested host count, falling back to calculated optimal")
                    # Fallback to calculated hosts if we can't parse the requirement
                    tool_args = {
                        "network": exercise["network"],
                        "division_type": exercise["method"],
                        "number": str(exercise["number"]),
                        "hosts_per_subnet": ""
                    }
                    
                    calc_result = await self.call_mcp_tool("ipmentor_subnet_calculator", tool_args)
                    if "error" in calc_result or "subnets" not in calc_result:
                        return "![Diagram generation failed]"
                    
                    hosts_per_subnet = [subnet["hosts"] for subnet in calc_result["subnets"]]
                    hosts_list = ",".join(map(str, hosts_per_subnet))
            
            # Generate diagram
            diagram_args = {
                "ip_network": exercise["network"],
                "hosts_list": hosts_list,
                "use_svg": False  # Use PNG for better PDF compatibility
            }
            
            diagram_result = await self.call_mcp_tool("ipmentor_generate_diagram", diagram_args)
            
            if "error" in diagram_result:
                return "![Diagram generation failed]"
            
            image_path = diagram_result.get("image_path", "")
            if image_path:
                return f"![Network Diagram]({image_path})", image_path
            else:
                return "![Diagram not available]", ""
                
        except Exception as e:
            print(f"Error generating diagram: {e}")
            return "![Diagram generation error]", ""
    
    async def generate_complete_exercises(self, num_exercises: int, difficulty: str, language: str, template: str, progress=None) -> tuple[str, str, str]:
        """Generate, validate and create complete exercises with diagrams"""
        try:
            print(f"=== Starting exercise generation ===")
            print(f"Inputs: {num_exercises} exercises, {difficulty}, {language}")
            print(f"Template length: {len(template) if template else 0}")
            # Connect to IPMentor if not connected
            if self.connection_status != "Connected":
                if progress is not None:
                    progress(0.4, desc="Connecting to IPMentor...")
                connect_result = await self.connect_to_ipmentor()
                if self.connection_status != "Connected":
                    return f"❌ Failed to connect to IPMentor: {connect_result}", "", ""
            
            # Generate exercises with LLM
            if progress is not None:
                progress(0.5, desc="Generating exercises with AI...")
            print(f"Generating {num_exercises} exercises with {difficulty} difficulty in {language}")
            
            try:
                exercises = self.generate_exercises_with_llm(num_exercises, difficulty, language, template)
                print(f"LLM returned {len(exercises) if exercises else 0} exercises")
            except Exception as llm_error:
                print(f"LLM generation failed: {llm_error}")
                import traceback
                print(f"LLM error traceback: {traceback.format_exc()}")
                return f"❌ LLM generation failed: {str(llm_error)}", "", ""
            
            if not exercises:
                print("No exercises returned from LLM")
                return "❌ Failed to generate exercises", "", ""
            
            # Validate and fix each exercise
            if progress is not None:
                progress(0.6, desc="Validating exercises...")
            validated_exercises = []
            for i, exercise in enumerate(exercises):
                try:
                    if progress is not None:
                        progress(0.6 + (0.2 * i / len(exercises)), desc=f"Validating exercise {i+1}/{len(exercises)}...")
                    validated_exercise = await self.validate_and_fix_exercise(exercise)
                    if validated_exercise:
                        validated_exercises.append(validated_exercise)
                except Exception as validation_error:
                    print(f"Error validating exercise {i+1}: {validation_error}")
                    # Still add the original exercise if validation fails completely
                    validated_exercises.append(exercise)
            
            # Generate diagrams and create markdown content
            if progress is not None:
                progress(0.8, desc="Generating network diagrams...")
            markdown_content, image_urls = await self.create_markdown_content_with_diagrams(validated_exercises, language, progress)
            
            # Generate PDF
            if progress is not None:
                progress(0.95, desc="Creating PDF document...")
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_pdf:
                pdf_path = tmp_pdf.name
            
            try:
                markdown_to_pdf(markdown_content, pdf_path)
                pdf_success = True
            except Exception as e:
                print(f"PDF generation failed: {e}")
                pdf_success = False
                pdf_path = ""
            
            # Create ZIP file with markdown and images
            zip_path = ""
            if markdown_content and not markdown_content.startswith("❌"):
                try:
                    zip_path = await self.create_zip_with_images(markdown_content, image_urls)
                except Exception as zip_error:
                    print(f"ZIP creation failed: {zip_error}")
            
            return markdown_content, pdf_path if pdf_success else "", zip_path
            
        except Exception as e:
            import traceback
            full_traceback = traceback.format_exc()
            print(f"FULL ERROR TRACEBACK: {full_traceback}")
            return f"❌ Error generating exercises: {str(e)}", "", ""
    
    async def create_markdown_content_with_diagrams(self, exercises: List[Dict], language: str, progress=None) -> str:
        """Create markdown content from validated exercises with actual diagrams"""
        # Title and field labels in the selected language
        titles = {
            "English": "# Subnetting Exercises",
            "Spanish": "# Ejercicios de Subnetting", 
            "French": "# Exercices de Sous-réseaux",
            "German": "# Subnetting-Übungen"
        }
        
        # Field labels and branding by language
        field_labels = {
            "English": {
                "powered_by": "Powered by [IPMentor](https://github.com/DavidLMS/ipmentor)",
                "exercise": "Exercise",
                "scenario": "Scenario",
                "network": "Network",
                "requirements": "Requirements",
                "diagram": "Network Diagram"
            },
            "Spanish": {
                "powered_by": "Ejercicios generados con las herramientas de [IPMentor](https://github.com/DavidLMS/ipmentor)",
                "exercise": "Ejercicio",
                "scenario": "Escenario",
                "network": "Red",
                "requirements": "Requisitos",
                "diagram": "Diagrama de Red"
            },
            "French": {
                "powered_by": "Exercices générés avec les outils d'[IPMentor](https://github.com/DavidLMS/ipmentor)",
                "exercise": "Exercice",
                "scenario": "Scénario",
                "network": "Réseau",
                "requirements": "Exigences",
                "diagram": "Diagramme de Réseau"
            },
            "German": {
                "powered_by": "Übungen erstellt mit den Tools von [IPMentor](https://github.com/DavidLMS/ipmentor)",
                "exercise": "Übung",
                "scenario": "Szenario",
                "network": "Netzwerk",
                "requirements": "Anforderungen",
                "diagram": "Netzwerk-Diagramm"
            }
        }
        
        labels = field_labels.get(language, field_labels["English"])
        
        markdown_lines = [
            titles.get(language, titles["English"]),
            "",
            f"*{labels['powered_by']}*",
            "",
            "---",
            ""
        ]
        
        image_urls = []
        
        for i, exercise in enumerate(exercises, 1):
            if progress is not None:
                progress(0.8 + (0.1 * i / len(exercises)), desc=f"Generating diagram for exercise {i}/{len(exercises)}...")
            print(f"Generating diagram for exercise {i}")
            
            # Generate the actual diagram
            diagram_markdown, image_url = await self.generate_diagram_for_exercise(exercise)
            if image_url:
                image_urls.append(image_url)
            
            # Create a unified exercise statement instead of fragmented fields
            scenario = exercise.get('scenario', '')
            network = exercise.get('network', '')
            requirements = exercise.get('requirements', '')
            
            # Combine scenario and requirements into a single cohesive statement
            if scenario and requirements:
                unified_statement = f"{scenario} {requirements}"
            elif scenario:
                unified_statement = scenario
            elif requirements:
                unified_statement = requirements
            else:
                unified_statement = "N/A"
            
            # Add network information to the statement if not already included
            if network and network not in unified_statement:
                if language == "Spanish":
                    unified_statement += f" Tienen asignado el direccionamiento {network}."
                elif language == "French":
                    unified_statement += f" Ils ont l'adressage {network} assigné."
                elif language == "German":
                    unified_statement += f" Sie haben die Adressierung {network} zugewiesen."
                else:
                    unified_statement += f" They have been assigned the network {network}."
            
            # Create fallback title
            fallback_title = f"{labels['exercise']} {i}"
            exercise_title = exercise.get('title', fallback_title)
            
            markdown_lines.extend([
                f"## {labels['exercise']} {i}: {exercise_title}",
                "",
                unified_statement,
                "",
                diagram_markdown,
                "",
                "---",
                ""
            ])
        
        return "\n".join(markdown_lines), image_urls

# Global instance
generator = ExerciseGenerator()

# GRADIO INTERFACE

async def generate_exercises_async(num_exercises, difficulty, language, template, progress=None):
    """Async wrapper for exercise generation"""
    return await generator.generate_complete_exercises(num_exercises, difficulty, language, template, progress)

def generate_exercises(num_exercises, difficulty, language, template, progress=None):
    """Generate exercises with validation and diagrams"""
    try:
        # Validate inputs
        if not isinstance(num_exercises, int) or num_exercises <= 0:
            return "❌ Error: Invalid number of exercises", None
        if not language or language not in ["English", "Spanish", "French", "German"]:
            return "❌ Error: Invalid language selection", None
        if not difficulty or difficulty not in ["easy", "medium", "difficult"]:
            return "❌ Error: Invalid difficulty level", None
            
        # Run async function
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            if progress is not None:
                progress(0.3, desc="Connecting to IPMentor...")
            markdown_content, pdf_path, zip_path = loop.run_until_complete(
                generate_exercises_async(num_exercises, difficulty, language, template, progress)
            )
        finally:
            loop.close()
        
        return markdown_content, pdf_path if pdf_path else None, zip_path if zip_path else None
        
    except Exception as e:
        import traceback
        error_msg = f"❌ Error: {str(e)}"
        print(f"Full error traceback: {traceback.format_exc()}")
        return error_msg, None, None

def create_interface():
    """Create the Gradio interface"""
    with gr.Blocks(title="IPMentor Exercise Generator") as app:
        # Header
        gr.Image("https://huggingface.co/spaces/davidlms/ipmentor/resolve/main/assets/header.png", show_label=False, interactive=False, container=False, height=80)
        gr.Markdown("""
        # Subnetting Exercise Generator
        
        Generate validated IPv4 subnetting exercises automatically. The agentic system uses AI to create realistic scenarios 
        and validates each exercise using [IPMentor](https://agents-mcp-hackathon-ipmentor.hf.space)'s calculation tools with MCP and Mistral Medium 3 as LLM Client.
        """)
        
        with gr.Row():
            with gr.Column(scale=1):
                # Input controls
                gr.Markdown("### Exercise Configuration")
                
                num_exercises = gr.Dropdown(
                    choices=[1, 2, 3, 4, 5],
                    value=3,
                    label="Number of Exercises",
                )
                
                difficulty = gr.Radio(
                    choices=["easy", "medium", "difficult"],
                    value="medium",
                    label="Difficulty Level"
                )
                
                language = gr.Dropdown(
                    choices=["English", "Spanish", "French", "German"],
                    value="English",
                    label="Language"
                )
                
                template = gr.Textbox(
                    label="Exercise Template (Optional)",
                    value=DEFAULT_TEMPLATES["English"],
                    lines=3,
                    info="Custom template for exercise scenarios. Updates automatically based on language selection.",
                    visible=False
                )
                
                generate_btn = gr.Button(
                    "🎯 Generate Exercises",
                    variant="primary",
                    size="lg"
                )
            
            with gr.Column(scale=2):
                # Output area
                gr.Markdown("### Generated Exercises")
                
                markdown_output = gr.Markdown(
                    value="*Click 'Generate Exercises'*",
                    label="Exercise Content"
                )
                
                with gr.Row():
                    pdf_output = gr.File(
                        label="Download PDF",
                        visible=False
                    )
                    zip_output = gr.File(
                        label="Download ZIP (Markdown + Images)",
                        visible=False
                    )
        
        # Event handlers
        def update_template(language):
            """Update template based on selected language"""
            return DEFAULT_TEMPLATES.get(language, DEFAULT_TEMPLATES["English"])
        
        def handle_generation(num_ex, diff, lang, templ, progress=gr.Progress()):
            progress(0, desc="Starting exercise generation...")
            
            progress(0.2, desc="Generating realistic scenarios...")
            markdown, pdf, zip_file = generate_exercises(num_ex, diff, lang, templ, progress)
            
            progress(1.0, desc="Complete!")
            
            pdf_file = gr.File(value=pdf, visible=True) if pdf else gr.File(visible=False)
            zip_file_ui = gr.File(value=zip_file, visible=True) if zip_file else gr.File(visible=False)
            
            return markdown, pdf_file, zip_file_ui
        
        # Update template when language changes
        language.change(
            fn=update_template,
            inputs=[language],
            outputs=[template]
        )
        
        generate_btn.click(
            fn=handle_generation,
            inputs=[num_exercises, difficulty, language, template],
            outputs=[markdown_output, pdf_output, zip_output],
            show_progress=True
        )
    
    return app

# MAIN APPLICATION

if __name__ == "__main__":
    # Check environment variables
    if not os.getenv("OPENROUTER_API_KEY"):
        print("⚠️  Warning: OPENROUTER_API_KEY not found. Please configure it in your .env file")
        print("   Get your API key from: https://openrouter.ai/")
    
    # Create and launch interface
    interface = create_interface()
    interface.launch(
        server_name="0.0.0.0",
        server_port=7890,
        share=False,
        debug=True
    )