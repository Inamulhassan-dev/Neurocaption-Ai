# 🎨 AI Caption Lab

**AI-Powered Social Media Caption Generator**

Generate engaging, platform-optimized captions for your images using local AI models (Ollama). No API keys required!

---

## ✨ Features

- 🤖 **AI-Powered Analysis** - Automatic image detection and tagging
- 🎯 **Smart Prompt Suggestions** - Context-aware prompt recommendations
- 🌐 **Multi-Platform Support** - Instagram, TikTok, LinkedIn, Twitter, YouTube
- 🎨 **Multiple Modes** - Social, Funny, Story, Business, Education
- 🌍 **Multi-Language** - English, Hindi, Spanish, French, German
- 📊 **Quality Meter** - Real-time engagement prediction
- 🎭 **Custom Presets** - Save and reuse your favorite settings
- 🖼️ **Multi-Image Support** - Generate captions for multiple images
- 🔍 **AI Detection** - Detect if images are AI-generated
- 🎤 **Voice Input** - Speak your prompts
- 🌓 **Dark/Light Theme** - Toggle between themes

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- Node.js 16+
- Ollama installed ([Download](https://ollama.ai))

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/Inamulhassan-dev/Neurocaption-Ai.git
   cd Neurocaption-Ai
   ```

2. **Set up environment variables**
   ```bash
   cp Backend/.env.example Backend/.env
   # Edit Backend/.env if you need to change model names or Ollama host
   ```

3. **Pull required Ollama models**
   ```bash
   ollama pull moondream
   ollama pull llama3.2:3b
   ```

4. **Install dependencies**

   *Windows (automated):*
   ```bash
   setup-windows.bat
   ```

   *Linux / macOS (manual):*
   ```bash
   # Backend
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r Backend/requirements.txt

   # Frontend
   cd Frontend
   npm install
   npm run build
   cd ..
   ```

5. **Start all services**

   *Windows:*
   ```bash
   start-all.bat
   ```

   *Linux / macOS:*
   ```bash
   # Terminal 1 – backend
   source .venv/bin/activate
   cd Backend && python app.py

   # Terminal 2 – frontend
   cd Frontend && node serve-build.js
   ```

6. **Open your browser**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8001

---

## 📁 Project Structure

```
Neurocaption-Ai/
├── Backend/              # FastAPI backend
│   ├── app.py           # Main API server
│   ├── model.py         # AI model logic
│   ├── ai_detector.py   # AI image detection
│   ├── requirements.txt # Python dependencies
│   ├── .env.example     # Template – copy to .env and fill in
│   └── Dockerfile       # Docker configuration
│
├── Frontend/            # React frontend
│   ├── src/
│   │   ├── App.jsx     # Main application
│   │   ├── styles.css  # Styling
│   │   └── index.js    # Entry point
│   └── package.json    # Node dependencies
│
├── .venv/              # Python virtual environment (git-ignored)
├── setup-windows.bat   # Windows: install deps + build + launch
├── start-all.bat       # Start all services
├── start-backend.bat   # Start backend only
├── start-frontend.bat  # Start frontend only
├── stop-services.bat   # Stop all services
└── README.md           # This file
```

---

## 🎮 Usage

### Basic Workflow

1. **Upload an image** - Click or drag & drop
2. **Review AI suggestions** - See detected tags and smart prompts
3. **Select platform** - Choose your target social media
4. **Customize settings** - Adjust creativity, length, emojis, etc.
5. **Generate captions** - Click "Generate Captions"
6. **Copy & use** - Copy your favorite caption

### Advanced Features

- **Quick Presets**: Use pre-configured settings (Viral, Minimal, Professional, etc.)
- **Custom Presets**: Save your own preset combinations
- **Voice Input**: Click the microphone icon to speak your prompt
- **Hashtag Generator**: Generate trending hashtags for your image
- **Caption Refinement**: Refine generated captions (shorter, longer, funnier)
- **Favorites**: Save your best captions for later

---

## 🛠️ Configuration

### Environment Variables

Create a `.env` file in the Backend folder:

```env
OLLAMA_HOST=http://localhost:11434
VISION_MODEL=moondream
TEXT_MODEL=llama3.2:3b
FAST_LOCAL=0
```

### Model Selection

- **Fast Mode** (FAST_LOCAL=1): Optimized for laptops/16GB RAM
- **Quality Mode** (FAST_LOCAL=0): Better quality, requires more resources

---

## 🐳 Docker Deployment

```bash
# Build and run with Docker Compose
docker-compose up -d
```

---

## 📝 API Endpoints

- `POST /caption` - Generate captions
- `POST /analyze` - Analyze image
- `POST /refine` - Refine caption
- `POST /hashtags` - Generate hashtags
- `GET /health` - Health check
- `GET /ollama-status` - Check Ollama status

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

---

## 📄 License

This project is licensed under the MIT License.

---

## 🙏 Acknowledgments

- [Ollama](https://ollama.ai) - Local AI models
- [FastAPI](https://fastapi.tiangolo.com/) - Backend framework
- [React](https://react.dev/) - Frontend framework
- [Moondream](https://moondream.ai/) - Vision model

---

## 👨‍💻 Developer

**Mohd Inamul Hassan**
- GitHub: [@inamulhassan-dev](https://github.com/inamulhassan-dev)
- Email: inamulhassan20006@gmail.com

---

## 📧 Support

For issues and questions, please open an issue on GitHub or contact the developer.

---

**Made with ❤️ by Mohd Inamul Hassan using Local AI**
