"""
IPMentor - IPv4 Network Analysis and Subnetting Tutor
"""

import logging
from .ui import create_interface
from .config import HOST, PORT, DEBUG, MCP_ENABLED, APP_NAME, VERSION

# Simple logging setup
logging.basicConfig(
    level=logging.INFO if not DEBUG else logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def main():
    """Main application entry point."""
    logger.info(f"Starting {APP_NAME} v{VERSION}")
    
    # Create Gradio app
    app = create_interface()
    
    # Launch configuration
    launch_config = {
        "server_name": HOST,
        "server_port": PORT,
        "share": False,
        "show_error": DEBUG,
        "mcp_server": MCP_ENABLED,
        "quiet": not DEBUG
    }
    
    logger.info(f"🌐 Web Interface: http://{HOST}:{PORT}")
    if MCP_ENABLED:
        logger.info(f"🤖 MCP Server: http://{HOST}:{PORT}/gradio_api/mcp/sse")
    
    try:
        app.launch(**launch_config)
    except KeyboardInterrupt:
        logger.info("👋 Shutting down...")
    except Exception as e:
        logger.error(f"❌ Error: {e}")


if __name__ == "__main__":
    main()