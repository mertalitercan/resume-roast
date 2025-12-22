# Resume Roast

An AI-powered tool designed to help job seekers optimize their resumes by providing instant, actionable feedback. It analyzes PDFs to enhance bullet points, metrics, and ATS compatibility.

Demo: https://resume-roast-t1w8.onrender.com/

## Features

- 📄 PDF resume upload and text extraction
- 🤖 AI-powered resume analysis using GPT-4
- 🔐 Firebase Authentication (Google Sign-In)
- ☁️ AWS S3 file storage
- 📊 MongoDB data persistence
- 🐳 Docker containerization

## Setup

### 1. Prerequisites

- Python 3.11+
- Docker & Docker Compose
- AWS Account (for S3)
- Firebase Project
- OpenAI API Key

### 2. Clone and Install

```bash
cd resumeroast
pip install -r requirements.txt
```

### 3. Configure Environment

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

Update `.env` with:
- MongoDB URI
- AWS credentials
- OpenAI API key
- Firebase credentials

### 4. Update Firebase Config

Edit `app/templates/index.html` and replace the Firebase config:

```javascript
const firebaseConfig = {
    apiKey: "YOUR_API_KEY",
    authDomain: "YOUR_PROJECT.firebaseapp.com",
    projectId: "YOUR_PROJECT_ID",
};
```

### 5. Run with Docker

```bash
docker-compose up --build
```

### 6. Run Locally (without Docker)

```bash
# Start MongoDB
docker run -d -p 27017:27017 mongo:7

# Run FastAPI
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 7. Open Browser

Visit: http://localhost:8000

## API Endpoints

- `GET /` - Homepage
- `POST /api/analyze` - Upload and analyze resume (requires auth)
- `GET /api/history` - Get user's resume history (requires auth)
- `GET /health` - Health check

## Tech Stack

- **Backend**: FastAPI, Python
- **Database**: MongoDB
- **Storage**: AWS S3
- **Authentication**: Firebase Auth
- **AI**: OpenAI GPT-4
- **PDF Processing**: PyPDF2
- **Frontend**: Jinja2, TailwindCSS
- **Deployment**: Docker

## Project Structure

```
resumeroast/
├── app/
│   ├── main.py              # FastAPI app
│   ├── config.py            # Configuration
│   ├── models.py            # Pydantic models
│   ├── services/            # Business logic
│   └── templates/           # HTML templates
├── static/                  # Static files
├── requirements.txt
├── Dockerfile
└── docker-compose.yml
```

## Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run tests (TODO)
pytest

# Format code
black app/

# Lint
flake8 app/
```

## License

MIT
