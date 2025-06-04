#!/usr/bin/env python3
"""
IPMentor - IPv4 Network Analysis and Subnetting Tutor
Hugging Face Space Entry Point
"""

import logging
import os
from ipmentor.ui import create_interface

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def main():
    """Main application entry point for Hugging Face Space."""
    logger.info("Starting IPMentor v1.0.0 for Hugging Face Space")
    
    # Create Gradio app
    app = create_interface()
    
    # Launch configuration for Hugging Face Space
    port = int(os.getenv("GRADIO_SERVER_PORT", 7860))
    launch_config = {
        "server_name": "0.0.0.0",
        "server_port": port,  # Use environment port or default
        "share": False,
        "show_error": True,
        "mcp_server": True,  # Enable MCP for Space
        "quiet": False
    }
    
    logger.info(f"🌐 Web Interface: Starting on port {port}")
    logger.info("🤖 MCP Server: Enabled for Hugging Face Space")
    
    try:
        app.launch(**launch_config)
    except Exception as e:
        logger.error(f"❌ Error launching app: {e}")
        raise

if __name__ == "__main__":
    main()