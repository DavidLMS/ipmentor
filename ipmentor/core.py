"""
Core IPv4 networking functions for IPMentor.
"""

import ipaddress
import math
from typing import Dict, List, Tuple


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
            
            if len(hosts_requirements) != number:
                raise ValueError(f"Need exactly {number} host values")
            
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