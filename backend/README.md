# RuParked Backend

FastAPI backend for the RuParked parking application.

## Quick Start

### 1. Install Python
Download from https://www.python.org/downloads/ (check "Add to PATH")

### 2. Install Dependencies
```bash
cd backend
pip install -r requirements.txt
```

### 3. Set Up Environment
Copy `.env.example` to `.env` and fill in your Azure keys:
```bash
cp .env.example .env
```

### 4. Run the Server
```bash
python -m uvicorn main:app --reload
```

Server runs at: http://localhost:8000

API Docs: http://localhost:8000/docs

## Features
- **Smart Commute Optimization** - Find the best parking lot for your commute
- **Social Features** - Friends, groups, parking sharing
- **Safety** - Location sharing, emergency contacts
- **Sustainability** - Carpool matching, eco badges

## API Endpoints
| Endpoint | Description |
|----------|-------------|
| `/navigation/commute/optimize` | Calculate optimal parking lot |
| `/navigation/commute/health` | Health check |
| `/navigation/commute/config` | View config status |

## Environment Variables
See `.env.example` for all required variables.
