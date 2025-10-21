// ...existing code...

# TailorBuy

<img src="readmeai/assets/logos/purple.svg" width="30%" alt="Project Logo"/>

Built with: Streamlit, FastAPI, scikit-learn, NumPy, pandas, Plotly, Pytest, Pydantic, OpenAI

Badges:
- Streamlit • FastAPI • Python • Pytest

---

## Table of Contents

- Overview
- Features
- Project structure
- Getting started
  - Prerequisites
  - Installation
  - Running (backend & frontend)
  - Testing
- Contributing
- License
- Acknowledgments

---

## Overview

TailorBuy is a product-recommender prototype with a Streamlit frontend and a FastAPI backend. The backend exposes conversation and chat endpoints and integrates an LLM-based product recommender. The frontend provides an interactive UI to start conversations, ask queries, and view product suggestions.

---

## Features

- Streamlit-based interactive frontend
- FastAPI backend with endpoints to create/list/delete conversations and chat with the recommender
- LLM-based product recommendation pipeline
- MongoDB persistence for conversation history
- Data ingestion pipeline with image description support
- Caching and TTL for short-term conversation state

---

## Project structure

Top-level layout (relevant files)

```
TailorBuy/
├── backend/
│   ├── app/
│   │   ├── main.py                     # FastAPI application and endpoints
│   │   ├── product_recommender_agent.py
│   │   ├── graph.py
│   │   └── ...
│   ├── database/
│   │   └── setup_db.py
│   └── mongodb/
│       ├── setup.py
│       └── create_collection.py
├── frontend/
│   └── app/
│       └── home.py                     # Streamlit frontend
├── Config/
│   └── config.py
├── requirements.txt
├── setup.py
├── Dockerfile.backend
├── Dockerfile.frontend
└── README.md
```

Key files:
- backend/app/main.py — FastAPI app (endpoints: POST /conversations/new, GET /conversations/{user_identity}, DELETE /conversations/{conversation_id}, POST /chat, GET /health)
- frontend/app/home.py — Streamlit UI; calls backend and deserializes /chat response
- backend/app/product_recommender_agent.py — recommendation logic and LLM integration
- backend/data/process_data.py — ingestion and image description pipeline
- backend/mongodb/* — MongoDB setup and collection creation
- Config/config.py — loads environment variables and API keys

---

## Getting Started

This workspace runs in a dev container (Ubuntu 24.04.2 LTS). Commands assume you are inside the container at /workspaces/TailorBuy.

### Prerequisites

- Python 3.10+ (use the venv in the dev container)
- pip
- MongoDB (or a MongoDB connection string)
- Environment API keys (see Config/config.py)

Environment variables commonly required:
- PINECONE_API_KEY (if using Pinecone)
- GEMINI_API_KEY or GOOGLE_API_KEY (LLM / vision APIs)
- MONGO_DB_URI or MONGO_DB_PASSWORD / related vars (see backend/mongodb/setup.py)

### Installation

From the workspace root:

```sh
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

If you prefer system Python (dev container already prepared): just run pip install -r requirements.txt.

### Configuration

Create a .env file or export environment variables required by Config/config.py. Example (.env):

```
PINECONE_API_KEY=your_pinecone_key
GEMINI_API_KEY=your_gemini_key
MONGO_DB_URI=mongodb://user:pass@host:port/dbname
```

Ensure Config/config.py reads env vars (it usually uses python-dotenv if present).

### Running

1) Start the backend (development)

```sh
uvicorn backend.app.main:app --reload --port 8000
```

The FastAPI interactive docs: http://127.0.0.1:8000/docs

2) Start the frontend (Streamlit)

```sh
streamlit run frontend/app/home.py
```

Open the URL shown by Streamlit (usually http://localhost:8501 or printed to console).

Notes:
- The frontend expects the backend at http://127.0.0.1:8000 by default. If you run the backend on another host/port, update the API base URL in frontend/app/home.py.
- The /chat endpoint returns a pickled binary object — frontend deserializes it. If calling /chat directly, save output and unpickle in Python.

Example curl usage:

Create a new conversation:
```sh
curl -X POST "http://127.0.0.1:8000/conversations/new" \
  -H "Content-Type: application/json" \
  -d '{"uuid":"<uuid>","user_identity":"alice"}'
```

Chat with the agent (binary response — save to file):
```sh
curl -X POST "http://127.0.0.1:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{"uuid":"<uuid>","user_query":"looking for blue shirts","is_selected_products":false}' \
  --output chat_response.pickle
```

Unpickle in Python:
```py
import pickle
with open("chat_response.pickle","rb") as f:
    resp = pickle.load(f)
print(resp)
```

## Troubleshooting

- Connection refused between frontend and backend: ensure backend is running and the base URL in frontend/app/home.py matches backend host/port.
- MongoDB errors: verify MONGO_DB_URI and check network connectivity to MongoDB instance.
- Long-running LLM or image description calls: these depend on external API keys and network — watch backend logs while requests are processed.
- Missing environment variables: Config/config.py will raise errors or default to None; set variables in .env or environment.

---

## Contributing

- Fork the repo, create a feature branch, implement changes, run tests, and open a PR.
- Keep changes scoped and include tests for new behavior.

Contributing checklist:
- Run linting and tests
- Include documentation for new endpoints
- Keep secrets out of the repository

---

## License

Add a LICENSE file appropriate to your project (e.g., MIT). This repo currently has no license file; choose one before publishing.

---

## Acknowledgments

- Project scaffolding and README generation assisted by repository tooling.
- Thanks to contributors and open-source projects used in this stack.

// ...existing code...
