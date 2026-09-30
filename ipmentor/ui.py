"""
Gradio UI for IPMentor.
"""

import gradio as gr
import ipaddress
import json
import random
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


def generate_exercise(use_vlsm: bool = False):
    """
    Generate a complete subnetting exercise with solution and diagram.

    Args:
        use_vlsm (bool): Whether to use VLSM (different host counts per subnet)

    Returns:
        tuple: (diagram_path, exercise_and_solution_json) for Gradio outputs
    """
    try:
        result_json = generate_exercise_core(use_vlsm)
        result = json.loads(result_json)

        if "error" in result:
            return None, json.dumps(result, indent=2)

        # Extract diagram path
        diagram_path = result.get("diagram_path")

        # Return diagram and formatted JSON
        return diagram_path, json.dumps(result, indent=2)

    except Exception as e:
        return None, json.dumps({"error": str(e)}, indent=2)


def random_ip_and_mask():
    """
    Generate a random, meaningful IPv4 address and subnet mask for practice.

    The address is always a usable host (never the network or broadcast
    address) inside a private range or a public unicast range, and the mask
    is consistent with that range. The mask is returned either in CIDR
    notation or in dotted decimal, chosen at random.

    Returns:
        tuple: (ip_address, subnet_mask) as strings
    """
    # (base network, allowed prefix range) — mask never shorter than the block
    ranges = [
        ("10.0.0.0/8", (8, 30)),
        ("172.16.0.0/12", (12, 30)),
        ("192.168.0.0/16", (16, 30)),
        ("192.168.0.0/16", (24, 30)),  # extra weight for classic /24+ LANs
    ]
    # Public unicast first octets (avoid 0, 10, 100.64/10, 127, 169.254, 172.16/12, 192.168, 224+)
    public_first_octets = [o for o in range(1, 224)
                           if o not in (10, 100, 127, 169, 172, 192)]

    if random.random() < 0.75:
        base, (pmin, pmax) = random.choice(ranges)
        block = ipaddress.IPv4Network(base)
    else:
        first = random.choice(public_first_octets)
        block = ipaddress.IPv4Network(f"{first}.0.0.0/8")
        pmin, pmax = 8, 30

    prefix = random.randint(pmin, pmax)
    # Random subnet of the chosen size inside the block
    subnets_in_block = 2 ** (prefix - block.prefixlen)
    subnet_index = random.randrange(subnets_in_block)
    subnet_int = int(block.network_address) + subnet_index * 2 ** (32 - prefix)
    subnet = ipaddress.IPv4Network(f"{ipaddress.IPv4Address(subnet_int)}/{prefix}")

    # Usable host: skip network and broadcast addresses
    host_offset = random.randint(1, subnet.num_addresses - 2)
    host = ipaddress.IPv4Address(int(subnet.network_address) + host_offset)

    mask = f"/{prefix}" if random.random() < 0.5 else str(subnet.netmask)
    return str(host), mask


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
            gr.Checkbox(label="Use VLSM (Variable Length Subnet Mask)", value=False)
        ],
        outputs=[
            gr.Image(label="Network Diagram", type="filepath"),
            gr.Textbox(label="Complete Exercise (Problem + Solution)", lines=30, interactive=False)
        ],
        title="Subnetting Exercise Generator",
        description="Generate complete random subnetting exercises with solution and diagram. Number of subnets (2-32) is randomly chosen. Enable VLSM for variable host requirements per subnet, or disable for equal division."
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
                random_btn = gr.Button("🎲 Random", variant="secondary")
                # UI-only helper: fills the inputs, hidden from the API/MCP tools
                random_btn.click(
                    fn=random_ip_and_mask,
                    inputs=None,
                    outputs=ip_interface.input_components,
                    show_api=False,
                )
            with gr.Tab("Subnet Calculator"):
                subnet_interface.render()
            with gr.Tab("Network Diagram"):
                diagram_interface.render()
            with gr.Tab("Exercise Generator"):
                exercise_interface.render()
    
    return combined_app
