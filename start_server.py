#!/usr/bin/env python3
"""
Startup script for ShopMind AI E-commerce Customer Service

Starts the FastAPI backend server with Ollama LLM integration.
"""

import os
import sys
import subprocess
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))


def check_ollama():
    """Check if Ollama is running."""
    import httpx
    try:
        response = httpx.get("http://localhost:11434/api/tags", timeout=5.0)
        if response.status_code == 200:
            models = response.json().get("models", [])
            print(f"[OK] Ollama is running with {len(models)} model(s)")
            for m in models:
                print(f"  - {m['name']}")
            return True
    except Exception:
        pass
    return False


def check_dependencies():
    """Check if required dependencies are installed."""
    required = ["fastapi", "uvicorn", "httpx", "chromadb", "langchain"]
    missing = []

    for pkg in required:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)

    if missing:
        print(f" Missing dependencies: {', '.join(missing)}")
        print("Run: pip install -e .")
        return False

    print("[OK] All dependencies installed")
    return True


def main():
    print("=" * 60)
    print("ShopMind AI — E-commerce Customer Service")
    print("=" * 60)
    print()

    # Check dependencies
    if not check_dependencies():
        sys.exit(1)

    # Check Ollama
    ollama_running = check_ollama()
    if not ollama_running:
        print()
        print("[WARN] Ollama is not running or not installed")
        print("  Install: https://ollama.com/download")
        print("  Start: ollama serve")
        print("  Pull model: ollama pull qwen2.5:3b")
        print()
        print("The system will use mock responses if Ollama is unavailable.")
        print()

    # Set environment variables
    os.environ.setdefault("OLLAMA_BASE_URL", "http://localhost:11434")
    os.environ.setdefault("OLLAMA_MODEL", "qwen2.5:3b")

    # Start server
    print("Starting FastAPI server...")
    print("API docs: http://localhost:8000/docs")
    print()

    try:
        import uvicorn
        uvicorn.run(
            "src.api.server:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
        )
    except ImportError:
        print("[ERROR] uvicorn not installed. Run: pip install uvicorn")
        sys.exit(1)


if __name__ == "__main__":
    main()
