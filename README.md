# 🌐 IPMentor

**IPv4 network analysis and subnetting tutor with MCP server integration**

A simple but powerful tool for learning IPv4 networking concepts. Features a clean web interface for humans and automatic MCP server for AI assistants.

## ✨ Features

- **📋 IP Analysis**: Complete IPv4 address breakdown with binary conversion
- **🧮 Subnetting Calculator**: Fixed-length and VLSM subnetting
- **🤖 MCP Server**: Automatic tool exposure for AI assistants
- **🎓 Educational**: Perfect for networking students and professionals

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone <your-repo-url>
cd ipmentor

# Install dependencies
pip install -r requirements.txt

# Run the application
python -m ipmentor.main
```

### Access

- **Web Interface**: http://localhost:7861
- **MCP Server**: http://localhost:7861/gradio_api/mcp/sse

## 🔧 Configuration

Create `.env` file for custom settings:

```env
HOST=0.0.0.0
PORT=7861
DEBUG=false
MCP_ENABLED=true
```

## 🤖 MCP Integration

### Claude Desktop Setup

Add to your Claude Desktop configuration:

```json
{
  "mcpServers": {
    "ipmentor": {
      "url": "http://localhost:7861/gradio_api/mcp/sse"
    }
  }
}
```

### Available Tools

- **`ip_info`**: Analyze IP addresses with subnet masks
- **`subnet_calculator`**: Calculate subnets using different methods
- **`generate_diagram`**: Create visual network diagrams in SVG format

### Example AI Prompts

- "Analyze the IP 192.168.1.100/24"
- "Create 8 subnets from 10.0.0.0/16"
- "Design VLSM for networks needing 100, 50, and 25 hosts"

## 🐳 Docker

```bash
# Build image
docker build -t ipmentor .

# Run container
docker run -p 7861:7861 ipmentor
```

## 📖 Usage Examples

### IP Analysis
```python
# Via Python
from ipmentor.core import analyze_ip
result = analyze_ip("192.168.1.10", "/24")
```

### Subnetting
```python
# Via Python  
from ipmentor.core import calculate_subnets
result = calculate_subnets("10.0.0.0/16", 8, "max_subnets")
```

## 🧪 Testing

```bash
python -m pytest tests/
```

## 📁 Project Structure

```
ipmentor/
├── ipmentor/
│   ├── main.py      # Entry point
│   ├── core.py      # IPv4 functions
│   ├── tools.py     # MCP tools
│   ├── ui.py        # Gradio interface
│   └── config.py    # Configuration
├── tests/           # Test suite
├── requirements.txt # Dependencies
└── README.md       # This file
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📝 License

MIT License - see LICENSE file for details.

---

**Built for the networking community** 🎓