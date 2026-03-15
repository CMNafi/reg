import sys
import os
import asyncio

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from db.models import create_tables, SessionLocal
from data.seed import seed_all_firms


def main():
    print("=" * 60)
    print("  RegIntel — Regulatory Intelligence Platform")
    print("  SEC Investment Adviser Analysis Engine")
    print("=" * 60)
    print()

    print("[1/3] Creating database tables...")
    create_tables()
    print("  Tables created.")
    print()

    print("[2/3] Seeding initial firms...")
    try:
        asyncio.run(seed_all_firms())
    except RuntimeError as e:
        print(f"\n  SEED FAILED: {e}")
        print("  Exiting.")
        sys.exit(1)
    print()

    print("[3/3] Starting API server...")
    port = int(os.getenv("PORT", 8000))
    print(f"  API:  http://localhost:{port}")
    print(f"  Docs: http://localhost:{port}/docs")
    print()

    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)


if __name__ == "__main__":
    main()
