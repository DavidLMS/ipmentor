"""
MCP tools for IPMentor.
"""

import json
import re
import subprocess
import tempfile
import shutil
import os
from pathlib import Path
from typing import List
from .core import analyze_ip, calculate_subnets


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


# Diagram generation constants and functions
ICON_MAP = {
    "Cloud":  "https://davidlms.github.io/ipmentor/assets/cloud.svg",
    "Router": "https://davidlms.github.io/ipmentor/assets/router.svg",
    "Switch": "https://davidlms.github.io/ipmentor/assets/switch.svg",
    "Hosts":  "https://davidlms.github.io/ipmentor/assets/host.svg",
}

EDGE_STYLE_BASE = (
    '  style: {\n'
    '    stroke: "#FFA201"\n'
    '    stroke-width: 3\n'
)


def _generar_diagrama_d2(ip_red: str, hosts_subredes: List[int]) -> str:
    """Generate basic D2 diagram without styling."""
    lines = [
        "Internet: Cloud",
        "Router: Router",
        "Switch_0: Switch",
        "",
        "Internet -> Router",
        f'Router -> Switch_0: "{ip_red}"',
        ""
    ]
    for idx, hosts in enumerate(hosts_subredes, start=1):
        lines += [
            f"Switch_{idx}: Switch",
            f"Host_{idx}: Hosts",
            f"Switch_0 -> Switch_{idx}",
            f'Switch_{idx} -> Host_{idx}: "{hosts} hosts"',
            ""
        ]
    if lines[-1] == "":
        lines.pop()
    return "\n".join(lines)


def _estilizar_diagrama_d2(diagrama: str) -> str:
    """Add styling and icons to D2 diagram."""
    styled = []
    for line in diagrama.splitlines():

        if not line.strip():
            styled.append("")
            continue

        # Nodes
        m_node = re.match(r'^(\w+(?:_\d+)?):\s*(Cloud|Router|Switch|Hosts)\s*$', line.strip())
        if m_node:
            name, kind = m_node.groups()
            styled.append(
                f"{name}: {kind} {{\n"
                "  style: {\n"
                "    font-color: transparent\n"
                "  }\n"
                "  shape: image\n"
                f"  icon: {ICON_MAP[kind]}\n"
                "}"
            )
            continue

        # Edges with labels
        m_edge_lbl = re.match(r'^(\w+(?:_\d+)?) -> (\w+(?:_\d+)?):\s*"([^"]+)"$', line.strip())
        if m_edge_lbl:
            src, dst, label = m_edge_lbl.groups()
            styled.append(
                f'{src} -> {dst}: "{label}" {{\n'
                f"{EDGE_STYLE_BASE}"
                "    font-size: 30\n"
                "  }\n"
                "}"
            )
            continue

        # Edges without labels
        m_edge = re.match(r'^(\w+(?:_\d+)?) -> (\w+(?:_\d+)?)$', line.strip())
        if m_edge:
            src, dst = m_edge.groups()
            styled.append(
                f"{src} -> {dst}: {{\n"
                f"{EDGE_STYLE_BASE}"
                "  }\n"
                "}"
            )
            continue

        styled.append(line)

    return "\n".join(styled)


def _exportar_svg(diagrama_d2: str, salida: str | Path = "diagrama.svg") -> Path:
    """Export D2 diagram to SVG using d2 CLI."""
    if shutil.which("d2") is None:
        raise RuntimeError(
            "No se encontró el ejecutable 'd2'.\n"
            "Instálalo desde https://d2lang.com/tour/installation "
            "o con Homebrew / chocolatey / scoop."
        )

    salida = Path(salida).expanduser().resolve()

    with tempfile.NamedTemporaryFile("w+", suffix=".d2", delete=False) as tmp:
        tmp.write(diagrama_d2)
        tmp.flush()
        tmp_path = Path(tmp.name)

    try:
        cmd = ["d2", str(tmp_path), str(salida)]
        subprocess.run(cmd, check=True)
    finally:
        if tmp_path.exists():
            os.remove(tmp_path)

    return salida


def generate_diagram(ip_network: str, hosts_list: str) -> str:
    """
    Generate a network diagram in SVG format for Gradio UI.

    Args:
        ip_network (str): Network IP with mask in CIDR format (e.g., "192.168.1.0/24")
        hosts_list (str): Comma-separated list of host counts per subnet (e.g., "50,20,10,5")

    Returns:
        str: Path to the generated SVG file for Gradio Image component
    """
    try:
        # Parse hosts list
        hosts_per_subnet = [int(h.strip()) for h in hosts_list.split(",") if h.strip()]
        
        if not hosts_per_subnet:
            raise ValueError("No valid host counts provided")

        # Generate basic diagram
        base_diagram = _generar_diagrama_d2(ip_network.strip(), hosts_per_subnet)
        
        # Add styling
        styled_diagram = _estilizar_diagrama_d2(base_diagram)
        
        # Export to SVG
        output_path = _exportar_svg(styled_diagram, "network_diagram.svg")
        
        return str(output_path)
        
    except Exception as e:
        # Create a simple error diagram for Gradio to display
        error_diagram = f"""
Internet: Cloud {{
  style: {{
    font-color: red
  }}
}}
Error: Error occurred: {str(e)[:50]}... {{
  style: {{
    font-color: red
    font-size: 20
  }}
}}
Internet -> Error
"""
        try:
            error_path = _exportar_svg(error_diagram, "error_diagram.svg")
            return str(error_path)
        except:
            # If even error diagram fails, return None
            return None


def generate_diagram_mcp(ip_network: str, hosts_list: str) -> str:
    """
    Generate a network diagram in SVG format for MCP API.

    Args:
        ip_network (str): Network IP with mask in CIDR format (e.g., "192.168.1.0/24")
        hosts_list (str): Comma-separated list of host counts per subnet (e.g., "50,20,10,5")

    Returns:
        str: Result information in JSON format including SVG path or error
    """
    try:
        # Parse hosts list
        hosts_per_subnet = [int(h.strip()) for h in hosts_list.split(",") if h.strip()]
        
        if not hosts_per_subnet:
            return json.dumps({"error": "No valid host counts provided"}, indent=2)

        # Generate basic diagram
        base_diagram = _generar_diagrama_d2(ip_network.strip(), hosts_per_subnet)
        
        # Add styling
        styled_diagram = _estilizar_diagrama_d2(base_diagram)
        
        # Export to SVG
        output_path = _exportar_svg(styled_diagram, "network_diagram.svg")
        
        result = {
            "success": True,
            "svg_path": str(output_path),
            "network": ip_network.strip(),
            "hosts_per_subnet": hosts_per_subnet,
            "d2_diagram": styled_diagram
        }
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        return json.dumps({"error": str(e)}, indent=2)