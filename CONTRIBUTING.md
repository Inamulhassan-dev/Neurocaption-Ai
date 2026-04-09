# Contributing to AI Caption Lab

Thank you for your interest in contributing! 🎉

## How to Contribute

### Reporting Bugs

1. Check if the bug has already been reported in Issues
2. Create a new issue with:
   - Clear title and description
   - Steps to reproduce
   - Expected vs actual behavior
   - Screenshots if applicable
   - Your environment (OS, Python version, Node version)

### Suggesting Features

1. Check if the feature has been suggested
2. Create a new issue with:
   - Clear description of the feature
   - Use cases and benefits
   - Possible implementation approach

### Pull Requests

1. **Fork the repository**
2. **Create a feature branch**
   ```bash
   git checkout -b feature/amazing-feature
   ```

3. **Make your changes**
   - Follow the existing code style
   - Add comments for complex logic
   - Update documentation if needed

4. **Test your changes**
   ```bash
   # Backend tests
   cd Backend
   python -m pytest

   # Frontend tests
   cd Frontend
   npm test
   ```

5. **Commit your changes**
   ```bash
   git commit -m "Add amazing feature"
   ```

6. **Push to your fork**
   ```bash
   git push origin feature/amazing-feature
   ```

7. **Open a Pull Request**
   - Describe your changes
   - Reference any related issues
   - Wait for review

## Code Style

### Python (Backend)
- Follow PEP 8
- Use type hints where possible
- Add docstrings for functions
- Keep functions focused and small

### JavaScript/React (Frontend)
- Use functional components
- Follow React best practices
- Use meaningful variable names
- Keep components modular

## Development Setup

1. **Install dependencies**
   ```bash
   # Backend
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r Backend/requirements.txt

   # Frontend
   cd Frontend
   npm install
   ```

2. **Run in development mode**
   ```bash
   # Backend
   cd Backend
   python app.py

   # Frontend
   cd Frontend
   npm start
   ```

## Questions?

Feel free to open an issue for any questions!

---

**Thank you for contributing! 🙏**
