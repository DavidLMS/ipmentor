"""
Gradio UI for IPMentor.
"""

import gradio as gr
import json
from .tools import (
    generate_diagram as generate_diagram_core,
    ip_info,
    subnet_calculator,
    generate_subnetting_exercise as generate_exercise_core
)

def generate_diagram(ip_network: str, hosts_list: str, use_svg: bool = False):
    """
    Generate a network diagram in PNG or SVG format.
    
    Args:
        ip_network (str): Network IP with mask in CIDR format (e.g., "192.168.1.0/24")
        hosts_list (str): Comma-separated list of host counts per subnet (e.g., "50,20,10,5")
        use_svg (bool): Whether to generate SVG format (default: PNG)
    
    Returns:
        tuple: (image_path, status_message) for Gradio outputs
    """
    try:
        if not ip_network.strip() or not hosts_list.strip():
            return None, "❌ Error: Please provide both network and hosts list"
        
        result_json = generate_diagram_core(ip_network.strip(), hosts_list.strip(), use_svg)
        result = json.loads(result_json)
        
        if "error" in result:
            return None, f"❌ Error: {result['error']}"
        
        format_type = "SVG" if use_svg else "PNG"
        hosts_count = len(result.get("hosts_per_subnet", []))
        return result.get("image_path"), f"✅ Success: {format_type} diagram generated for {hosts_count} subnets"
        
    except Exception as e:
        return None, f"❌ Error: {str(e)}"


def generate_exercise(num_subnets: str, use_vlsm: bool = False):
    """
    Generate a subnetting exercise.

    Args:
        num_subnets (str): Number of subnets to generate
        use_vlsm (bool): Whether to use VLSM (different host counts per subnet)

    Returns:
        str: Exercise specification in JSON format
    """
    try:
        num_subnets_int = int(num_subnets.strip())
        if num_subnets_int < 1:
            return json.dumps({"error": "Number of subnets must be at least 1"}, indent=2)

        result_json = generate_exercise_core(num_subnets_int, use_vlsm)
        return result_json

    except ValueError:
        return json.dumps({"error": "Invalid number of subnets"}, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)}, indent=2)


def create_interface():
    """Create the Gradio interface."""
    
    # Create separate interfaces for MCP tools only
    ip_interface = gr.Interface(
        fn=ip_info,
        api_name="ip_info",
        inputs=[
            gr.Textbox(label="IP Address", placeholder="192.168.1.10"),
            gr.Textbox(label="Subnet Mask", placeholder="/24 or 255.255.255.0")
        ],
        outputs=gr.Textbox(label="Analysis Result"),
        title="IP Info",
        description="Analyze IPv4 addresses with subnet masks"
    )
    
    subnet_interface = gr.Interface(
        fn=subnet_calculator,
        api_name="subnet_calculator",
        inputs=[
            gr.Textbox(label="Network", placeholder="192.168.1.0/24"),
            gr.Textbox(label="Number", placeholder="4", value=""),
            gr.Dropdown(label="Division Type", choices=["max_subnets","max_hosts_per_subnet","vlsm"], value="max_subnets"),
            gr.Textbox(label="Hosts per Subnet", placeholder="100,50,25,10", value="")
        ],
        outputs=gr.Textbox(label="Calculation Result"),
        title="Subnet Calculator",
        description="Calculate subnets using different methods"
    )
    
    diagram_interface = gr.Interface(
        fn=generate_diagram,
        api_name="generate_diagram",
        inputs=[
            gr.Textbox(label="Network", placeholder="192.168.1.0/24"),
            gr.Textbox(label="Hosts per Subnet", placeholder="50,20,10,5"),
            gr.Checkbox(label="Generate as SVG", value=False)
        ],
        outputs=[
            gr.Image(label="Network Diagram", type="filepath"),
            gr.Textbox(label="Status", lines=2, interactive=False)
        ],
        title="Network Diagram Generator",
        description="Generate network diagrams (PNG by default, SVG optional)"
    )

    exercise_interface = gr.Interface(
        fn=generate_exercise,
        api_name="generate_exercise",
        inputs=[
            gr.Textbox(label="Number of Subnets", placeholder="4", value="4"),
            gr.Checkbox(label="Use VLSM (Variable Length Subnet Mask)", value=False)
        ],
        outputs=gr.Textbox(label="Exercise", lines=20, interactive=False),
        title="Subnetting Exercise Generator",
        description="Generate random subnetting exercises. Enable VLSM for variable host requirements per subnet, or disable for equal division."
    )

    # Create main interface with custom header and description
    with gr.Blocks() as combined_app:
        # Header with logo
        gr.Image("assets/header.png", show_label=False, interactive=False, container=False, height=120)
        
        # Description
        gr.Markdown("""
        **IPMentor** is a comprehensive IPv4 networking toolkit that provides four powerful tools:

        - **IP Info**: Analyze IPv4 addresses with subnet masks, supporting decimal, binary, and CIDR formats
        - **Subnet Calculator**: Calculate subnets using different methods (max subnets, max hosts per subnet, and VLSM)
        - **Network Diagram**: Generate visual network diagrams with automatic subnet validation
        - **Exercise Generator**: Generate random subnetting exercises for practice and learning

        Choose a tab below to get started with your networking calculations and visualizations.
        """)
        
        # Tabbed interface
        with gr.Tabs():
            with gr.Tab("IP Info"):
                ip_interface.render()
            with gr.Tab("Subnet Calculator"):
                subnet_interface.render()
            with gr.Tab("Network Diagram"):
                diagram_interface.render()
            with gr.Tab("Exercise Generator"):
                exercise_interface.render()
    
    return combined_app