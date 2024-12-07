# AutoScribe 📝

> Intelligent changelog automation powered by AI

[![PyPI version](https://badge.fury.io/py/autoscribe.svg)](https://badge.fury.io/py/autoscribe)
[![Python Version](https://img.shields.io/pypi/pyversions/autoscribe)](https://pypi.org/project/autoscribe)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Checked with mypy](https://www.mypy-lang.org/static/mypy_badge.svg)](https://mypy-lang.org/)

AutoScribe is a modern, AI-powered changelog generation tool designed to transform your git history into beautiful, meaningful documentation. It leverages the power of Large Language Models to understand your commits and create structured, readable changelogs following the [Keep a Changelog](https://keepachangelog.com/) format.

## 🎯 Why AutoScribe?

Managing changelogs is a critical but often overlooked aspect of software development:
- Manual changelog maintenance is time-consuming
- Conventional commit messages don't always translate well to user-friendly changes
- Maintaining consistency across versions is challenging
- Legacy changelog tools lack modern features and intelligence

AutoScribe solves these challenges by:
- Automatically generating structured changelogs from git history
- Using AI to translate technical commits into user-friendly descriptions
- Following Keep a Changelog format consistently
- Integrating seamlessly with existing workflows

## 🚀 Quick Start

1. Install AutoScribe via pip:

```bash
pip install autoscribe
```

2. Set up your OpenAI API key:

```bash
export OPENAI_API_KEY=your-api-key
# or create a .env file with OPENAI_API_KEY=your-api-key
```

3. Generate your changelog:

```bash
# Basic usage
scribe

# With AI enhancement
scribe --ai

# Specific version
scribe --version 1.2.3
```

## ✨ Features

- 🤖 **AI Enhancement**: Uses LLMs to improve changelog readability and clarity
- 🎯 **Smart Categorization**: Automatically groups changes by type and impact
- 📝 **Keep a Changelog**: Follows the Keep a Changelog format
- 🔄 **Version Management**: Automatic version bumping and tag creation
- 🔍 **Conventional Commits**: Full support for conventional commit messages
- 🌐 **GitHub Integration**: Automatic release notes and tag creation
- 💡 **Intelligent Parsing**: Understands various commit message formats
- 📈 **Breaking Changes**: Automatic detection and highlighting of breaking changes

## ⚙️ Configuration

AutoScribe can be configured through multiple methods:

### Configuration File

Create `pyproject.toml` or `.autoscribe.toml`:

```toml
[tool.autoscribe]
# Output configuration
output = "CHANGELOG.md"

# Version management
version_file = "pyproject.toml"
version_pattern = "version = '{version}'"

# Content configuration
categories = [
    "Added",
    "Changed",
    "Deprecated",
    "Removed",
    "Fixed",
    "Security"
]

# GitHub integration
github_release = true
github_token = "env:GITHUB_TOKEN"

# AI configuration
ai_enabled = true
ai_model = "gpt-4o-mini"
openai_api_key = "env:OPENAI_API_KEY"
```

### Environment Variables

Configure via environment variables:

```bash
AUTOSCRIBE_OUTPUT=CHANGELOG.md
AUTOSCRIBE_AI_ENABLED=true
AUTOSCRIBE_GITHUB_TOKEN=your-token
```

### Command Line Options

Override settings via CLI:

```bash
scribe --output CHANGELOG.md \
       --ai \
       --github-release
```

## 🤖 AI Features

When AI enhancement is enabled, AutoScribe:

1. **Improves Readability**: Transforms technical commit messages into user-friendly descriptions
2. **Detects Impact**: Analyzes changes to determine their impact level
3. **Groups Related Changes**: Intelligently groups related commits
4. **Suggests Version Bumps**: Recommends version changes based on commit content
5. **Generates Summaries**: Creates concise version summaries

### Supported Models

| Model | Cost | Best for |
|-------|------|----------|
| gpt-4o-mini | Low | Most cases |
| gpt-4o | Medium | Complex analysis |
| gpt-3.5-turbo | Lowest | Basic enhancement |

## 📖 Advanced Usage

### GitHub Integration

Enable automatic GitHub releases:

```bash
# Configure GitHub token
export GITHUB_TOKEN=your-token

# Create release on version bump
scribe --version minor --github-release

# Create draft release
scribe --version patch --github-release --draft
```

### Conventional Commits Support

AutoScribe fully supports the Conventional Commits specification:

```bash
feat(api): add new endpoint
fix(core): resolve memory leak
docs(readme): update installation steps
BREAKING CHANGE: remove legacy support
```

## 🛠️ Development Status

- ✅ **Core Features**: Changelog generation, version management
- ✅ **AI Integration**: OpenAI support, customizable prompts
- ✅ **Quality**:
  - Comprehensive test suite
  - Static type checking with mypy
  - Code formatting with ruff
  - Documentation with autodoc
- 🚧 **In Progress**:
  - Additional AI models support
  - Enhanced GitHub integration
  - Plugin architecture

## 🤝 Contributing

Contributions are welcome! Please read our [Contributing Guidelines](CONTRIBUTING.md) before submitting pull requests.

Areas we'd love help with:
- AI model integrations
- GitHub integration improvements
- Documentation enhancement
- Bug fixes and testing

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

<p align="center">Crafted with ❤️ by <a href="https://github.com/Arakiss">@Arakiss</a></p>
