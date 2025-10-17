"""Pallet Orchestrator - Phase 5: Simple Linear Pipeline.

Main entry point. Delegates to src.orchestrator module for core logic.

Usage:
  uv run python main.py [requirements]
  python main.py "Create a function that validates email addresses"
"""

import asyncio
import sys

from src.orchestrator import main as orchestrator_main


async def main():
    """Parse CLI args and run orchestrator."""
    if len(sys.argv) < 2:
        # Use default requirements
        await orchestrator_main()
    else:
        # Use provided requirements
        requirements = " ".join(sys.argv[1:])
        await orchestrator_main(requirements)


if __name__ == "__main__":
    asyncio.run(main())
