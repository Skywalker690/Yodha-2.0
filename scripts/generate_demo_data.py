"""Prepare the documented cohort with actual scans and visibly precomputed baseline outputs."""

from scripts.import_oasis import main

if __name__ == "__main__":
    import sys

    if "--precompute" not in sys.argv:
        sys.argv.append("--precompute")
    main()
