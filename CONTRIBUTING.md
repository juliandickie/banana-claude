# Contributing to Banana Claude

Contributions are welcome! Here's how to help.

## How to Contribute

1. **Fork** the repository
2. **Create a branch** for your feature or fix
3. **Make your changes** and test them
4. **Submit a pull request** with a clear description

## What to Contribute

- Bug fixes
- New domain modes
- Improved prompt templates
- Documentation improvements
- Post-processing recipes

## Guidelines

- Keep SKILL.md under 500 lines / 5,000 tokens
- Ensure consistency across all reference files (rate limits, model names, aspect ratios)
- Test as plugin: `claude --plugin-dir .`
- Validate before submitting: `claude plugin validate .`
- Follow existing markdown formatting conventions
- Bump version in all 4 files when releasing (see CLAUDE.md Versioning section)

## Reporting Issues

Open an issue with:
- What you expected to happen
- What actually happened
- Steps to reproduce
