#!/usr/bin/env python3
"""
Entry point for running the package as a module.
"""
import sys
import traceback

def run_main():
    try:
        print("Starting LinkedIn Job Scraper...")
        from .main import main
        main()
    except ImportError as e:
        print(f"Import error: {e}")
        print("This might be due to incorrect file names or missing dependencies.")
        print("Traceback:")
        traceback.print_exc()
    except Exception as e:
        print(f"Error running LinkedIn Job Scraper: {e}")
        print("Traceback:")
        traceback.print_exc()

if __name__ == "__main__":
    run_main()