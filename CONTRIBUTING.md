# Contributing to IPMentor

Thanks for taking the time to contribute! Your help is greatly appreciated.

All types of contributions are encouraged and valued, whether it's code, documentation, suggestions for new features, or bug reports.

> If you like the project but don't have time to contribute, you can also star the project, tweet about it, or mention it in your project's README.

## I Have a Question

Before asking a question, please read the [README](README.md) and search for existing [Issues](../../issues) that might help you. If you still need clarification, open a new issue with as much context as possible about what you're running into.

## Reporting Bugs

Before submitting a bug report, ensure you're using the latest version and verify the issue isn't due to misconfiguration. Search the [bug tracker](../../issues?q=label%3Abug) to check if it's already been reported.

When reporting a bug, include your OS, Python version, Gradio version, and D2 installation status. Provide the specific IP addresses or calculation parameters that caused the issue, along with expected vs actual results. Include clear steps to reproduce the problem.

> Don't report security issues publicly - email them privately instead.

## Suggesting Enhancements

Check the documentation and existing issues before suggesting new features. Make sure your suggestion aligns with IPMentor's educational focus and IPv4 networking scope.

When suggesting enhancements, use a clear title and provide detailed context about why the enhancement would benefit networking education. Include screenshots or network diagrams if they help illustrate your suggestion.

## Your First Code Contribution

### Setup

Fork the repository, then:

```bash
git clone https://github.com/<YOUR_GITHUB_USER>/ipmentor.git
cd ipmentor
git checkout -B <feature-description>

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install D2 for diagram generation
# macOS: brew install d2
# Windows: scoop install d2 or choco install d2
# Linux: curl -fsSL https://d2lang.com/install.sh | sh
# Alternative: Download binary from https://github.com/terrastruct/d2/releases
#             and place it in bin/d2 (create bin/ directory if needed)

# Run tests
python -m pytest

# Start development server
python app.py
```

### Guidelines

**Code Quality**: Follow PEP 8, use type hints, and write clear docstrings. Ensure your code passes linting and all tests.

**Calculation Accuracy**: All networking calculations must be mathematically correct and follow RFC standards. Validate against established networking tools and references.

**Educational Value**: Consider how your changes help students learn networking concepts better. Prefer clarity over complexity.

**MCP Integration**: If adding new calculations, consider whether they should be available as MCP tools for AI agents.

**Testing**: Write comprehensive tests covering edge cases, invalid inputs, and RFC compliance. Test calculations against multiple reference implementations.

### Contributing New Features

For new calculation features, add functions to `ipmentor/tools.py` with proper input validation and error handling. Update MCP tools in the main interface if the calculation should be available to AI agents. Add UI components to `ipmentor/ui.py` for web access.

For diagram improvements, understand the current D2 approach and maintain educational clarity. Test with various network sizes and consider accessibility in design choices.

## Documentation

We especially welcome help with setup guides, educational examples, integration tutorials, and troubleshooting guides. Since IPMentor is educational, clear documentation is crucial.

## Style Guidelines

Use conventional commit messages (`feat:`, `fix:`, `docs:`, `test:`, `refactor:`). Write clear, descriptive commit summaries under 50 characters.

Follow standard Python style with meaningful error messages that help users understand networking concepts. Include comments explaining the networking principles being implemented.

## Educational Focus

Remember that IPMentor is primarily educational. Accuracy is paramount since students depend on correct calculations. New features should enhance learning and support both basic and advanced scenarios.

## License

By contributing to IPMentor, you agree that your contributions will be licensed under the MIT License.