![IPMentor Header](assets/header.png)

<p align="center">
  <a href="https://huggingface.co/spaces/Agents-MCP-Hackathon/ipmentor">
    <img src="https://img.shields.io/badge/🤗-Demo%20Space-blue" alt="Demo Space">
  </a>
  <a href="https://huggingface.co/spaces/Agents-MCP-Hackathon/ipmentor-demo">
    <img src="https://img.shields.io/badge/🤖-Chatbot%20Demo-green" alt="Chatbot Demo">
  </a>
  <a href="LICENSE">
    <img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="MIT License">
  </a>
</p>

# IPMentor

**IPMentor** is an IPv4 networking toolkit designed to serve as verified computational tools for AI tutoring systems. While modern LLMs handle many networking calculations reasonably well, IPMentor ensures accuracy and enables cost-effective tutoring by allowing smaller, specialized models to focus on pedagogy while delegating complex subnet mathematics to dedicated, verified tools.

Built for the [**Gradio MCP Hackathon 2025**](https://huggingface.co/Agents-MCP-Hackathon), IPMentor demonstrates how the Model Context Protocol (MCP) can bridge AI tutoring systems with specialized computational tools, creating more reliable and affordable educational experiences.

> **🔗 Try it now:**  

> **[Live Demo](https://huggingface.co/spaces/Agents-MCP-Hackathon/ipmentor)** - Interactive web interface (is a MCP Server!) 

> **[AI Chatbot Demo](https://huggingface.co/spaces/Agents-MCP-Hackathon/ipmentor-demo)** - Conversational AI using IPMentor tools with Mistral Small 3.1 24B as LLM

<p align="center">
    <a href="https://github.com/DavidLMS/ipmentor/issues/new?assignees=&labels=bug&projects=&template=bug_report.md&title=%5BBUG%5D">Report Bug</a>
    ·
    <a href="https://github.com/DavidLMS/ipmentor/issues/new?assignees=&labels=enhancement&projects=&template=feature_request.md&title=%5BREQUEST%5D">Request Feature</a>
  </p>

## Why IPMentor?

### The Problem with AI-Only Network Tutoring

Current AI tutoring approaches in networking education face a fundamental challenge: while large language models can perform many calculations, they occasionally make errors in complex subnet mathematics. More importantly, using powerful models for every calculation is expensive and unnecessary when the goal is to teach networking concepts rather than arithmetic.

### The IPMentor Solution

IPMentor addresses these challenges by providing:

- **Verified Calculations**: All subnet mathematics is performed by dedicated algorithms, eliminating computational errors.
- **Cost-Effective Tutoring**: Smaller, efficient AI models can handle educational interactions while delegating calculations to IPMentor.
- **Reliable Foundation**: Teachers and students can trust that the underlying mathematics is always correct.

This approach follows the principle of **computational separation of concerns** - let AI models excel at explanation and pedagogy, while specialized tools handle precise calculations.

## Key Features

- **🔍 IP Analysis**: Complete IPv4 address analysis with subnet mask support (decimal, binary, and CIDR formats).
- **🧮 Subnet Calculator**: Advanced subnet division using multiple methods:
  - Maximum subnets division.
  - Maximum hosts per subnet division.
  - Variable Length Subnet Masking (VLSM).
- **📊 Network Diagrams**: Automatic generation of basic network subnets topology diagrams with D2.
- **🤖 MCP Integration**: Native Model Context Protocol support for AI agent connectivity.
- **🎓 Educational Focus**: Designed specifically for networking education and tutoring scenarios.

## How It Works

IPMentor operates as both a standalone web application and an MCP server, making it accessible to both human learners and AI tutoring systems:

1. **Web Interface**: Students and teachers can use the interactive Gradio interface for direct calculations.
2. **MCP Tools**: AI agents connect via MCP to access three core functions:
   - `ip_info` - Analyze IPv4 addresses and subnet masks.
   - `subnet_calculator` - Perform subnet calculations with multiple division methods.
   - `generate_diagram` - Create visual network diagrams.
3. **REST API**: Direct API access to all tools for integration into custom applications and educational platforms.
4. **Verified Results**: All calculations use proven algorithms to ensure mathematical accuracy.

## Quick Start

### For Direct Use

Visit the **[live demo](https://huggingface.co/spaces/Agents-MCP-Hackathon/ipmentor)** to try IPMentor's tools immediately through the web interface.

### For Local Development

```bash
# Clone the repository
git clone https://github.com/yourusername/ipmentor.git
cd ipmentor

# Install dependencies
pip install -r requirements.txt

# Run the application
python app.py
```

The application will be available at `http://localhost:7860` with MCP server enabled at `/gradio_api/mcp/sse`.

### For AI Integration

See the **[chatbot demo](https://huggingface.co/spaces/Agents-MCP-Hackathon/ipmentor-demo)** for an example of how AI agents can use IPMentor tools through MCP for conversational network assistance.

## Example Use Cases

### Subnet Calculation Verification

```python
# AI agent uses IPMentor to verify calculations
result = await subnet_calculator(
    network="192.168.1.0/24",
    number="4", 
    division_type="max_subnets"
)
# Returns verified subnet information for 4 equal subnets
```

### Network Diagram Generation

```python
# Create visual diagrams for complex network designs
diagram = await generate_diagram(
    ip_network="10.0.0.0/16",
    hosts_list="1000,500,250,100"
)
# Generates network topology diagram with VLSM subnets
```

## Integration with LearnMCP-xAPI

IPMentor complements **[LearnMCP-xAPI](https://github.com/DavidLMS/learnmcp-xapi)** to create comprehensive AI tutoring systems:

- **IPMentor**: Provides verified computational tools for networking calculations.
- **LearnMCP-xAPI**: Maintains persistent learning records to track student progress.

Together, they enable AI tutors that can both perform accurate calculations and adapt to individual student learning patterns over time.

## Technical Architecture

IPMentor is built with:

- **Python & Gradio**: Web interface and MCP server foundation.
- **IPv4 Calculations**: Native Python algorithms for subnet mathematics.
- **D2 Integration**: Network diagram generation using the D2 language.
- **MCP Protocol**: Standard interface for AI agent integration.
- **Pydantic Validation**: Robust input validation and error handling.

## Contributing

Contributions are welcome! Whether you're improving calculations, enhancing visualizations, or adding new educational features, your input helps make networking education more effective.

Please see our [contribution guidelines](CONTRIBUTING.md) and feel free to open issues or pull requests.

## License

IPMentor is released under the [MIT License](LICENSE). You are free to use, modify, and distribute the code for both educational and commercial purposes.

---

*Built with ❤️ for the Gradio MCP Hackathon - Making AI tutoring more reliable, one subnet at a time.*