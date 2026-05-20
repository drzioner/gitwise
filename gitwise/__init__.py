__version__ = "0.12.1"


def get_version() -> str:
    try:
        from importlib.metadata import version as _version

        return _version("gitwise")
    except (ImportError, Exception):
        return __version__
