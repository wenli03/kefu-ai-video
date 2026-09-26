"""
Startup script for e-commerce video CS agent.

Usage:
    python scripts/start.py

Requires environment variables (see .env.example):
    LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET
    OPENAI_API_KEY (optional, falls back to rule-based)
    DEEPGRAM_API_KEY (for STT)
    CARTESIA_API_KEY (for TTS)
"""

import os
import sys
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from dotenv import load_dotenv


def check_environment() -> list[str]:
    """Check required environment variables and return list of warnings."""
    warnings = []

    required = ["LIVEKIT_URL", "LIVEKIT_API_KEY", "LIVEKIT_API_SECRET"]
    for var in required:
        if not os.getenv(var):
            warnings.append(f"Missing required: {var}")

    optional = {
        "OPENAI_API_KEY": "LLM will use rule-based fallback",
        "DEEPGRAM_API_KEY": "STT will not work",
        "CARTESIA_API_KEY": "TTS will not work",
    }
    for var, impact in optional.items():
        if not os.getenv(var):
            warnings.append(f"Missing optional: {var} ({impact})")

    return warnings


def main():
    load_dotenv()

    print("=" * 60)
    print("E-commerce AI Video Customer Service Agent")
    print("=" * 60)

    warnings = check_environment()
    if warnings:
        print("\nEnvironment warnings:")
        for w in warnings:
            print(f"  - {w}")
        print()

    if any("Missing required" in w for w in warnings):
        print("ERROR: Required environment variables missing.")
        print("Copy .env.example to .env and fill in your LiveKit credentials.")
        sys.exit(1)

    print("Starting agent server...")
    print("Press Ctrl+C to stop\n")

    from livekit.agents import cli
    from agent import server

    cli.run_app(server)


if __name__ == "__main__":
    main()
