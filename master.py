"""Repository entry point for consolidation and explicit read-only Vision backup."""

if __name__ == "__main__":
    from src.cc_vision_import.master_cli import main

    raise SystemExit(main())
