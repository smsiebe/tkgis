"""Entry point for ``python -m tkgis``."""
from __future__ import annotations

import argparse
import sys


def main() -> None:
    """Launch the tkgis application."""
    parser = argparse.ArgumentParser(
        prog="tkgis",
        description="tkgis — Python Tkinter GIS Workbench",
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="Print version and exit",
    )
    args = parser.parse_args()

    if args.version:
        from tkgis import __version__

        print(f"tkgis {__version__}")
        sys.exit(0)

    from tkgis.app import TkGISApp

    app = TkGISApp()
    app.mainloop()


if __name__ == "__main__":
    main()
