"""
Tools for IPMentor.
"""

import json
import re
import subprocess
import tempfile
import shutil
import os
import ipaddress
import math
from pathlib import Path
from typing import List, Dict, Tuple


def ip_to_binary(ip_str: str) -> str:
    """Convert IP address to binary format with dots."""
    try:
        ip = ipaddress.IPv4Address(ip_str)
        binary = format(int(ip), '032b')
        return f"{binary[:8]}.{binary[8:16]}.{binary[16:24]}.{binary[24:]}"
    except:
        return "Invalid IP"


def binary_to_ip(binary_str: str) -> str:
    """Convert binary IP to decimal format."""
    try:
        binary_clean = binary_str.replace('.', '').replace(' ', '')
        if len(binary_clean) != 32 or not all(c in '01' for c in binary_clean):
            return "Invalid Binary"
        ip_int = int(binary_clean, 2)
        return str(ipaddress.IPv4Address(ip_int))
    except:
        return "Invalid Binary"


def parse_subnet_mask(mask_str: str) -> Tuple[str, int]:
    """Parse subnet mask from various formats."""
    mask_str = mask_str.strip()
    
    if mask_str.startswith('/'):
        cidr = int(mask_str[1:])
    elif '.' in mask_str:
        mask_ip = ipaddress.IPv4Address(mask_str)
        cidr = bin(int(mask_ip)).count('1')
    else:
        cidr = int(mask_str)
    
    if not 0 <= cidr <= 32:
        raise ValueError("Invalid CIDR")
    
    mask_ip = ipaddress.IPv4Network(f"0.0.0.0/{cidr}").netmask
    return str(mask_ip), cidr


def analyze_ip(ip: str, subnet_mask: str) -> Dict:
    """Analyze IP address with subnet mask."""
    try:
        # Handle binary IP
        if '.' in ip and all(c in '01.' for c in ip.replace('.', '')):
            ip = binary_to_ip(ip)
            if ip == "Invalid Binary":
                raise ValueError("Invalid binary IP")
        
        # Parse mask
        mask_decimal, cidr = parse_subnet_mask(subnet_mask)
        
        # Create network
        network = ipaddress.IPv4Network(f"{ip}/{cidr}", strict=False)
        
        # Calculate hosts
        if cidr < 31:
            total_hosts = 2 ** (32 - cidr) - 2
            first_host = str(network.network_address + 1)
            last_host = str(network.broadcast_address - 1)
        elif cidr == 31:
            total_hosts = 2
            first_host = str(network.network_address)
            last_host = str(network.broadcast_address)
        else:
            total_hosts = 1
            first_host = str(network.network_address)
            last_host = str(network.network_address)
        
        return {
            "ip_decimal": ip,
            "ip_binary": ip_to_binary(ip),
            "subnet_mask_decimal": mask_decimal,
            "subnet_mask_binary": ip_to_binary(mask_decimal),
            "subnet_mask_cidr": f"/{cidr}",
            "network_address": str(network.network_address),
            "broadcast_address": str(network.broadcast_address),
            "first_host": first_host,
            "last_host": last_host,
            "total_hosts": total_hosts
        }
    
    except Exception as e:
        return {"error": str(e)}


def calculate_subnets(network: str, number: int, method: str, hosts_list: str = "") -> Dict:
    """Calculate subnets using different methods."""
    try:
        base_network = ipaddress.IPv4Network(network, strict=False)
        base_cidr = base_network.prefixlen
        
        if method == "max_subnets":
            # Calculate subnets needed
            bits_needed = math.ceil(math.log2(number))
            new_cidr = base_cidr + bits_needed
            
            if new_cidr > 32:
                raise ValueError("Too many subnets requested")
            
            subnets = list(base_network.subnets(new_prefix=new_cidr))
            hosts_per_subnet = 2 ** (32 - new_cidr) - 2 if new_cidr < 31 else (2 if new_cidr == 31 else 1)
            
            subnet_list = []
            for i, subnet in enumerate(subnets[:number]):
                subnet_list.append({
                    "subnet": str(subnet),
                    "network": str(subnet.network_address),
                    "broadcast": str(subnet.broadcast_address),
                    "first_host": str(subnet.network_address + 1) if hosts_per_subnet > 1 else str(subnet.network_address),
                    "last_host": str(subnet.broadcast_address - 1) if hosts_per_subnet > 1 else str(subnet.broadcast_address),
                    "hosts": hosts_per_subnet
                })
            
            return {
                "method": "Max Subnets",
                "subnets": subnet_list,
                "bits_borrowed": bits_needed,
                "hosts_per_subnet": hosts_per_subnet,
                "total_subnets": len(subnets)
            }
        
        elif method == "max_hosts_per_subnet":
            # Calculate CIDR for hosts
            if number <= 2:
                bits_for_hosts = 1 if number == 2 else 0
            else:
                bits_for_hosts = math.ceil(math.log2(number + 2))
            
            new_cidr = 32 - bits_for_hosts
            
            if new_cidr < base_cidr:
                raise ValueError("Too many hosts requested")
            
            subnets = list(base_network.subnets(new_prefix=new_cidr))
            actual_hosts = 2 ** bits_for_hosts - 2 if new_cidr < 31 else (2 if new_cidr == 31 else 1)
            
            subnet_list = []
            for subnet in subnets:
                subnet_list.append({
                    "subnet": str(subnet),
                    "network": str(subnet.network_address),
                    "broadcast": str(subnet.broadcast_address),
                    "first_host": str(subnet.network_address + 1) if actual_hosts > 1 else str(subnet.network_address),
                    "last_host": str(subnet.broadcast_address - 1) if actual_hosts > 1 else str(subnet.broadcast_address),
                    "hosts": actual_hosts
                })
            
            return {
                "method": "Max Hosts per Subnet",
                "subnets": subnet_list,
                "hosts_per_subnet": actual_hosts,
                "total_subnets": len(subnets)
            }
        
        elif method == "vlsm":
            # Parse hosts requirements
            hosts_requirements = [int(x.strip()) for x in hosts_list.split(',')]
            
            # For VLSM, always use the number calculated from hosts_list
            calculated_number = len(hosts_requirements)
            if number == 0 or number != calculated_number:
                if number != 0:
                    print(f"VLSM: Using calculated number {calculated_number} from hosts_list instead of provided number {number}")
                number = calculated_number
            
            # Sort largest first for optimal allocation
            sorted_reqs = sorted(enumerate(hosts_requirements), key=lambda x: x[1], reverse=True)
            
            subnets = []
            available_networks = [base_network]
            
            for original_idx, hosts_needed in sorted_reqs:
                # Find required CIDR
                if hosts_needed == 1:
                    required_cidr = 32
                elif hosts_needed == 2:
                    required_cidr = 31
                else:
                    # Calculate bits needed for hosts + network + broadcast
                    bits_for_hosts = math.ceil(math.log2(hosts_needed + 2))
                    required_cidr = 32 - bits_for_hosts
                
                # Find a suitable available network
                allocated = False
                for i, avail_net in enumerate(available_networks):
                    # Check if we can fit the required subnet in this available network
                    if required_cidr >= avail_net.prefixlen:
                        # Allocate the first subnet of the required size
                        try:
                            allocated_subnet = list(avail_net.subnets(new_prefix=required_cidr))[0]
                        except ValueError:
                            # Cannot create subnet of this size
                            continue
                        
                        # Calculate actual host capacity
                        if required_cidr == 32:
                            actual_hosts = 1
                            first_host = str(allocated_subnet.network_address)
                            last_host = str(allocated_subnet.network_address)
                        elif required_cidr == 31:
                            actual_hosts = 2
                            first_host = str(allocated_subnet.network_address)
                            last_host = str(allocated_subnet.broadcast_address)
                        else:
                            actual_hosts = 2 ** (32 - required_cidr) - 2
                            first_host = str(allocated_subnet.network_address + 1)
                            last_host = str(allocated_subnet.broadcast_address - 1)
                        
                        subnets.append({
                            "subnet": str(allocated_subnet),
                            "network": str(allocated_subnet.network_address),
                            "broadcast": str(allocated_subnet.broadcast_address),
                            "first_host": first_host,
                            "last_host": last_host,
                            "hosts": actual_hosts,
                            "hosts_requested": hosts_needed,
                            "original_order": original_idx + 1
                        })
                        
                        # Remove the used network
                        available_networks.pop(i)
                        
                        # Add remaining available spaces by splitting the original network
                        remaining_subnets = []
                        for subnet in avail_net.subnets(new_prefix=required_cidr):
                            if subnet != allocated_subnet:
                                remaining_subnets.append(subnet)
                        
                        # Add the remaining subnets back to available networks
                        available_networks.extend(remaining_subnets)
                        
                        allocated = True
                        break
                
                if not allocated:
                    raise ValueError(f"Cannot allocate subnet for {hosts_needed} hosts")
            
            # Sort back to original order
            subnets.sort(key=lambda x: x["original_order"])
            
            return {
                "method": "VLSM",
                "subnets": subnets,
                "total_hosts_requested": sum(hosts_requirements),
                "total_hosts_allocated": sum(s["hosts"] for s in subnets)
            }
        
        else:
            raise ValueError("Invalid method")
    
    except Exception as e:
        return {"error": str(e)}


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


def subnet_calculator(network: str, number: str = "0", division_type: str = "max_subnets", hosts_per_subnet: str = "") -> str:
    """
    Calculate subnets using different division methods.

    Args:
        network (str): Main network in CIDR format (e.g., "192.168.1.0/24")
        number (str): Number for division calculation (optional for VLSM, auto-calculated from hosts_per_subnet)
        division_type (str): Division method - "max_subnets", "max_hosts_per_subnet", or "vlsm"
        hosts_per_subnet (str): Comma-separated host counts per subnet (required for VLSM)

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


def _generate_basic_d2_diagram(network_ip: str, hosts_per_subnet: List[int]) -> str:
    """Generate basic D2 diagram without styling."""
    lines = [
        "Internet: Cloud",
        "Router: Router",
        "Switch_0: Switch",
        "",
        "Internet -> Router",
        f'Router -> Switch_0: "{network_ip}"',
        ""
    ]
    for idx, hosts in enumerate(hosts_per_subnet, start=1):
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


def _style_d2_diagram(diagram: str) -> str:
    """Add styling and icons to D2 diagram."""
    styled = []
    for line in diagram.splitlines():

        if not line.strip():
            styled.append("")
            continue

        # Nodes
        node_match = re.match(r'^(\w+(?:_\d+)?):\s*(Cloud|Router|Switch|Hosts)\s*$', line.strip())
        if node_match:
            name, kind = node_match.groups()
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
        edge_with_label_match = re.match(r'^(\w+(?:_\d+)?) -> (\w+(?:_\d+)?):\s*"([^"]+)"$', line.strip())
        if edge_with_label_match:
            src, dst, label = edge_with_label_match.groups()
            styled.append(
                f'{src} -> {dst}: "{label}" {{\n'
                f"{EDGE_STYLE_BASE}"
                "    font-size: 30\n"
                "  }\n"
                "}"
            )
            continue

        # Edges without labels
        edge_match = re.match(r'^(\w+(?:_\d+)?) -> (\w+(?:_\d+)?)$', line.strip())
        if edge_match:
            src, dst = edge_match.groups()
            styled.append(
                f"{src} -> {dst}: {{\n"
                f"{EDGE_STYLE_BASE}"
                "  }\n"
                "}"
            )
            continue

        styled.append(line)

    return "\n".join(styled)


def _export_to_image(d2_diagram: str, output_path: str | Path = "diagram.png", format: str = "png") -> Path:
    """Export D2 diagram to PNG or SVG using d2 CLI."""
    if shutil.which("d2") is None:
        raise RuntimeError(
            "D2 executable not found.\n"
            "Install it from https://d2lang.com/tour/installation "
            "or with Homebrew / chocolatey / scoop."
        )

    # Ensure output path has correct extension
    output_path = Path(output_path).expanduser().resolve()
    if format == "svg" and not output_path.suffix == ".svg":
        output_path = output_path.with_suffix(".svg")
    elif format == "png" and not output_path.suffix == ".png":
        output_path = output_path.with_suffix(".png")

    with tempfile.NamedTemporaryFile("w+", suffix=".d2", delete=False) as tmp:
        tmp.write(d2_diagram)
        tmp.flush()
        tmp_path = Path(tmp.name)

    try:
        cmd = ["d2", str(tmp_path), str(output_path)]
        subprocess.run(cmd, check=True)
    finally:
        if tmp_path.exists():
            os.remove(tmp_path)

    return output_path


def generate_diagram(ip_network: str, hosts_list: str, use_svg: bool = False) -> str:
    """
    Generate a network diagram in PNG or SVG format.

    Args:
        ip_network (str): Network IP with mask in CIDR format (e.g., "192.168.1.0/24")
        hosts_list (str): Comma-separated list of host counts per subnet (e.g., "50,20,10,5")
        use_svg (bool): Whether to generate SVG format (default: PNG)

    Returns:
        str: Result information in JSON format including image path or error
    """
    try:
        # Handle string boolean values from JSON (MCP tools often pass strings)
        if isinstance(use_svg, str):
            use_svg = use_svg.lower() in ('true', '1', 'yes', 'on')
        
        # Parse hosts list
        hosts_per_subnet = [int(h.strip()) for h in hosts_list.split(",") if h.strip()]
        
        if not hosts_per_subnet:
            return json.dumps({"error": "No valid host counts provided"}, indent=2)

        # Validate that the subnet distribution is possible using VLSM
        validation_result = calculate_subnets(
            ip_network.strip(), 
            len(hosts_per_subnet), 
            "vlsm", 
            hosts_list.strip()
        )
        
        if "error" in validation_result:
            return json.dumps({
                "error": f"Invalid subnet distribution: {validation_result['error']}"
            }, indent=2)

        # Generate basic diagram
        base_diagram = _generate_basic_d2_diagram(ip_network.strip(), hosts_per_subnet)
        
        # Add styling
        styled_diagram = _style_d2_diagram(base_diagram)
        
        # Export to image
        format = "svg" if use_svg else "png"
        filename = f"network_diagram.{format}"
        output_path = _export_to_image(styled_diagram, filename, format)
        
        result = {
            "success": True,
            "image_path": str(output_path),
            "format": format,
            "network": ip_network.strip(),
            "hosts_per_subnet": hosts_per_subnet,
            "d2_diagram": styled_diagram
        }
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        return json.dumps({"error": str(e)}, indent=2)