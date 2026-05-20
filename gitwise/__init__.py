__version__ = "0.12.1"


def get_version() -> str:
    try:
        from importlib.metadata import version

        return version("gitwise")
    except ImportError:
        return __version__
