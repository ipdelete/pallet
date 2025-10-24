#!/usr/bin/env python3
# /// script
# dependencies = []
# ///

import json
import sys
from datetime import datetime
from pathlib import Path

# Read hook input from stdin
hook_data = json.load(sys.stdin)

# Extract prompt text
prompt = hook_data.get("prompt", "")

# Create logs directory if needed
log_dir = Path("logs/prompts")
log_dir.mkdir(parents=True, exist_ok=True)

# Write to timestamped file
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_file = log_dir / f"prompt_{timestamp}.txt"

with open(log_file, "w") as f:
    f.write(f"Timestamp: {datetime.now().isoformat()}\n")
    f.write(f"Session: {hook_data.get('session_id', 'unknown')}\n")
    f.write(f"\nPrompt:\n{prompt}\n")

# Exit 0 for success (stdout ignored unless in transcript mode)
sys.exit(0)
