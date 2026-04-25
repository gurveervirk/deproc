from __future__ import annotations

import argparse

from .runtime import get_runtime_registry


def main() -> None:
    parser = argparse.ArgumentParser(prog="deproc-core")
    parser.add_argument(
        "--list",
        action="store_true",
        help="List discovered language plugins.",
    )
    args = parser.parse_args()

    if args.list:
        registry = get_runtime_registry()
        for language in registry.supported_languages():
            print(language)
        return

    parser.print_help()


if __name__ == "__main__":
    main()
