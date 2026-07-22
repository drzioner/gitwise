"""gitwise -- CLI for optimizing git workflows and coding-agent integration."""

__version__ = "0.36.1"


def get_version() -> str:
    """Return the installed package version, falling back to the source version."""
    from importlib.metadata import PackageNotFoundError
    from importlib.metadata import version as _version

    try:
        return _version("gitwise")
    except PackageNotFoundError:
        return __version__
