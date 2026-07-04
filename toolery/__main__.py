"""Entry point for ``python -m toolery`` and the ``toolery`` console script."""

from .cli import _dispatch_funcs


def main():
    """Dispatch the toolery CLI subcommands."""
    import argh

    argh.dispatch_commands(_dispatch_funcs)


if __name__ == "__main__":
    main()
