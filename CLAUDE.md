# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Octopus is a multi-agent AI system built with FastAPI that provides natural language orchestration of various AI agents. It uses a decorator-based registration system for agent discovery and method introspection.

## Key Architecture Concepts

### Agent System
- **Base Class**: All agents inherit from `BaseAgent` (octopus/agents/base_agent.py)
- **Registration**: Use `@register_agent` decorator on agent classes
- **Method Exposure**: Use `@agent_method` decorator on methods you want to expose
- **Router**: `AgentRouter` (octopus/router/agents_router.py) manages all agent registrations as a singleton
- **Master Agent**: `MasterAgent` (octopus/master_agent.py) handles natural language task delegation

### Directory Structure
- `octopus/` - Main package containing all source code
- `octopus/agents/` - Agent implementations
- `octopus/router/` - Agent routing and registration
- `octopus/api/` - FastAPI endpoints (versioned)
- `external/anp-open-sdk/` - ANP SDK submodule

## Common Development Commands

### Running the Application
```bash
# Main entry point (recommended)
uv run python -m octopus.octopus

# Or using uvicorn directly
uv run uvicorn octopus.octopus:app --reload --host 0.0.0.0 --port 9880
```

### Running Tests
```bash
# Run all tests with coverage
uv run pytest

# Run specific test categories
uv run pytest -m unit        # Unit tests only
uv run pytest -m integration # Integration tests only
uv run pytest -m "not slow"  # Skip slow tests
```

### Code Quality Tools
```bash
# Format code with black
uv run black octopus/

# Lint with flake8
uv run flake8 octopus/

# Type check with mypy
uv run mypy octopus/
```

### Dependency Management
```bash
# Install all dependencies
uv sync

# Install with optional dependencies
uv sync --all-extras  # Install all optional groups
uv sync --extra dev   # Install dev dependencies only
```

## Environment Configuration

The project uses `.env` file for configuration. Copy `.env_template` to `.env` and set:
- `OPENAI_API_KEY` - Required for AI functionality
- `OPENAI_MODEL` - Model to use (default: gpt-4-turbo-preview)
- `APP_PORT` - Application port (default: 9880)
- `LOG_LEVEL` - Logging level (INFO, DEBUG, etc.)

## Key Technical Details

- **Python Version**: 3.11+ required
- **Package Manager**: Uses `uv` (modern Python package manager)
- **Framework**: FastAPI with async support
- **Configuration**: Pydantic Settings with environment variables
- **Logging**: Enhanced logging with colorlog, logs to `~/Library/Logs/octopus/octopus.log`
- **Testing**: pytest with async support and coverage reporting
- **OpenAI Integration**: Supports both OpenAI and Azure OpenAI endpoints

## Adding New Agents

To create a new agent:
1. Create a new file in `octopus/agents/`
2. Inherit from `BaseAgent`
3. Use decorators for registration:

```python
from octopus.agents.base_agent import BaseAgent
from octopus.router.agents_router import register_agent, agent_method

@register_agent(name="my_agent", description="Description of what this agent does")
class MyAgent(BaseAgent):
    @agent_method(description="Process some data")
    async def process_data(self, data: str) -> str:
        # Implementation
        return processed_data
```

The agent will be automatically discovered and registered when the application starts.
