"""
Simple configuration for IPMentor.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# Basic settings
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", 7861))
DEBUG = os.getenv("DEBUG", "false").lower() == "true"
MCP_ENABLED = os.getenv("MCP_ENABLED", "true").lower() == "true"

# App info
APP_NAME = "IPMentor"
VERSION = "1.0.0"
DESCRIPTION = "IPv4 network analysis and subnetting tutor"