"""Entry point for ``python -m toolery`` and the ``toolery`` console script.

The dispatch itself lives in :mod:`toolery.cli`, next to ``_dispatch_funcs`` (the
SSOT for what the CLI exposes); this module only re-exports it so the console
script's ``toolery.__main__:main`` target keeps resolving.
"""

from .cli import main


__all__ = ["main"]


if __name__ == "__main__":
    main()
