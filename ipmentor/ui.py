"""
Gradio UI for IPMentor.
"""

import gradio as gr
import json
from .tools import generate_diagram as generate_diagram_core, ip_info, subnet_calculator
from .config import APP_NAME

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
            gr.Textbox(label="Number", placeholder="4"),
            gr.Dropdown(label="Division Type", choices=["max_subnets","max_hosts_per_subnet","vlsm"], value="max_subnets"),
            gr.Textbox(label="Hosts per Subnet", placeholder="100,50,25,10")
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
    
    # Combine all the MCP tool interfaces
    combined_app = gr.TabbedInterface(
        [ip_interface, subnet_interface, diagram_interface],
        ["IP Info", "Subnet Calculator", "Network Diagram"],
        title=f"{APP_NAME}"
    )
    
    return combined_app