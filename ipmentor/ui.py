"""
Gradio UI for IPMentor.
"""

import gradio as gr
import json
from .core import analyze_ip, calculate_subnets
from .tools import generate_diagram, generate_diagram_mcp
from .config import APP_NAME




# MCP Tool Functions
def ip_info(ip: str, subnet_mask: str) -> str:
    """
    Analyze a complete IPv4 address with its subnet mask.
    
    Args:
        ip (str): IP address in decimal (192.168.1.10) or binary format
        subnet_mask (str): Subnet mask in decimal (255.255.255.0), CIDR (/24), or number (24) format
    
    Returns:
        str: Complete IP and network information in JSON format
    """
    try:
        result = analyze_ip(ip.strip(), subnet_mask.strip())
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)}, indent=2)


def subnet_calculator(network: str, number: str, division_type: str, hosts_per_subnet: str = "") -> str:
    """
    Calculate subnets using different division methods.
    
    Args:
        network (str): Main network in CIDR format (e.g., "192.168.1.0/24")
        number (str): Number for division calculation
        division_type (str): Division method - "max_subnets", "max_hosts_per_subnet", or "vlsm"
        hosts_per_subnet (str): Comma-separated host counts per subnet (VLSM only)
    
    Returns:
        str: Calculated subnet information in JSON format
    """
    try:
        number_int = int(number.strip())
        result = calculate_subnets(
            network.strip(), 
            number_int, 
            division_type.strip(), 
            hosts_per_subnet.strip()
        )
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)}, indent=2)


# MCP API function for diagram generation  
def generate_diagram_api(ip_network: str, hosts_list: str) -> str:
    """MCP API wrapper for diagram generation that returns JSON."""
    return generate_diagram_mcp(ip_network, hosts_list)


# Gradio UI wrapper for diagram generation
def generate_diagram_ui(ip_network: str, hosts_list: str):
    """Gradio UI wrapper for diagram generation that handles errors gracefully."""
    try:
        if not ip_network.strip() or not hosts_list.strip():
            return None
        result = generate_diagram(ip_network, hosts_list)
        return result
    except Exception as e:
        # Return None if there's any error - Gradio will handle this gracefully
        return None


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
        fn=generate_diagram_ui,
        api_name="generate_diagram",
        inputs=[
            gr.Textbox(label="Network", placeholder="192.168.1.0/24"),
            gr.Textbox(label="Hosts per Subnet", placeholder="50,20,10,5")
        ],
        outputs=gr.Image(label="Network Diagram", type="filepath"),
        title="Network Diagram Generator",
        description="Generate network diagrams with SVG output"
    )
    
    # Combine all the MCP tool interfaces
    combined_app = gr.TabbedInterface(
        [ip_interface, subnet_interface, diagram_interface],
        ["IP Info", "Subnet Calculator", "Network Diagram"],
        title=f"{APP_NAME} - MCP Tools"
    )
    
    return combined_app