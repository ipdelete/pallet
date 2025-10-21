#!/usr/bin/env python3
"""
Demo script showing the difference between subprocess with and without PIPE.
"""
import asyncio
import subprocess


async def demo_with_pipe():
    """Demo with PIPE - captures output for programmatic access"""
    print("=== WITH PIPE ===")
    print("Running: echo 'Hello from stdout' && echo 'Error from stderr' >&2")
    
    process = await asyncio.create_subprocess_exec(
        "sh", "-c", "echo 'Hello from stdout' && echo 'Error from stderr' >&2",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    
    stdout, stderr = await process.communicate()
    stdout = stdout.decode()
    stdout = stdout.strip()
    
    print(f"Captured stdout: {stdout.decode().strip()}")
    print(f"Captured stderr: {stderr.decode().strip()}")
    print(f"Return code: {process.returncode}")
    print()


async def demo_without_pipe():
    """Demo without PIPE - output goes directly to terminal"""
    print("=== WITHOUT PIPE ===")
    print("Running: echo 'Hello from stdout' && echo 'Error from stderr' >&2")
    print("(Output will appear directly in terminal)")
    
    process = await asyncio.create_subprocess_exec(
        "sh", "-c", "echo 'Hello from stdout' && echo 'Error from stderr' >&2"
        # No stdout/stderr parameters - inherits parent's streams
    )
    
    await process.wait()
    print(f"Return code: {process.returncode}")
    print("Note: No captured output available - it went directly to terminal")
    print()


async def main():
    await demo_with_pipe()
    await demo_without_pipe()


if __name__ == "__main__":
    asyncio.run(main())