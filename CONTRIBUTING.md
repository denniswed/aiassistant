# Contributing to AI Assistant

Thank you for your interest in contributing to the AI Assistant project! This document provides guidelines and instructions for contributing.

## Code of Conduct

- Be respectful and inclusive
- Welcome newcomers and help them get started
- Focus on constructive feedback
- Keep discussions on topic

## Getting Started

### Prerequisites

1. Python 3.8 or higher
2. Git
3. A code editor (VS Code recommended)
4. LM Studio for testing

### Setting Up Development Environment

```bash
# Clone the repository
git clone https://github.com/denniswed/aiassistant.git
cd aiassistant

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install development dependencies
pip install pytest pytest-cov black flake8 mypy

# Copy example config
cp config.json.example config.json
# Edit config.json with your settings
```

## Development Workflow

### 1. Create a Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/your-bug-fix
```

### 2. Make Your Changes

Follow these guidelines:

#### Code Style

- Follow PEP 8 conventions
- Use type hints for all function parameters and return values
- Maximum line length: 100 characters
- Use descriptive variable names

#### Formatting

Run Black formatter before committing:

```bash
black assistant.py
```

#### Type Checking

Run mypy to check type hints:

```bash
mypy assistant.py
```

#### Linting

Run flake8 to check code quality:

```bash
flake8 assistant.py --max-line-length=100
```

### 3. Documentation

- Add docstrings to all new functions and classes
- Use Google-style docstrings
- Update README.md if adding new features
- Update CHANGELOG.md with your changes

#### Docstring Example

```python
def example_function(param1: str, param2: int) -> bool:
    """Brief description of the function.
    
    More detailed description if needed. Explain what the function does,
    any important behavior, or side effects.
    
    Args:
        param1: Description of param1
        param2: Description of param2
        
    Returns:
        Description of return value
        
    Raises:
        ValueError: When param2 is negative
        IOError: When file cannot be read
    """
    pass
```

### 4. Testing

Write tests for new features:

```python
# test_assistant.py
import pytest
from assistant import AssistantConfig

def test_config_validation():
    """Test configuration validation."""
    with pytest.raises(ValueError):
        config = AssistantConfig(sample_rate=-1)
```

Run tests:

```bash
pytest
pytest --cov=assistant  # With coverage
```

### 5. Commit Your Changes

Write clear, descriptive commit messages:

```bash
git add .
git commit -m "feat: Add configuration validation

- Add validation for sample_rate parameter
- Raise ValueError for invalid values
- Add unit tests for validation
"
```

#### Commit Message Format

```
<type>: <subject>

<body>

<footer>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

### 6. Push and Create Pull Request

```bash
git push origin feature/your-feature-name
```

Then create a pull request on GitHub with:
- Clear title describing the change
- Description of what was changed and why
- Reference to any related issues
- Screenshots for UI changes (if applicable)

## Pull Request Guidelines

### Checklist

Before submitting a PR, ensure:

- [ ] Code follows PEP 8 style guidelines
- [ ] All functions have type hints
- [ ] All functions have docstrings
- [ ] Tests pass (`pytest`)
- [ ] Code is formatted with Black
- [ ] No linting errors (`flake8`)
- [ ] Type checking passes (`mypy`)
- [ ] Documentation is updated
- [ ] CHANGELOG.md is updated
- [ ] Commit messages are clear

### Review Process

1. Maintainers will review your PR
2. Address any feedback or requested changes
3. Once approved, your PR will be merged

## Areas for Contribution

### High Priority

- [ ] Add unit tests for existing functionality
- [ ] Implement configuration GUI
- [ ] Add voice activity detection (VAD)
- [ ] Support for multiple languages
- [ ] Conversation history persistence

### Medium Priority

- [ ] Add streaming response support
- [ ] Implement plugin system
- [ ] Add more TTS engine options
- [ ] Improve error recovery
- [ ] Add performance profiling

### Low Priority

- [ ] Add themes/customization
- [ ] Create desktop notifications
- [ ] Add system tray integration
- [ ] Support for custom hotkeys
- [ ] Add speech synthesis caching

## Reporting Issues

### Bug Reports

Include:
- Python version
- Operating system
- Steps to reproduce
- Expected behavior
- Actual behavior
- Relevant logs from `assistant.log`

### Feature Requests

Include:
- Clear description of the feature
- Use cases
- Why it would be valuable
- Any implementation ideas

## Questions?

- Open an issue with the `question` label
- Check existing issues and documentation first

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

## Thank You!

Your contributions make this project better for everyone!
