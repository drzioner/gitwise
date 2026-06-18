__version__ = "0.26.1"


def get_version() -> str:
    from importlib.metadata import PackageNotFoundError
    from importlib.metadata import version as _version

    try:
        return _version("gitwise")
    except PackageNotFoundError:
        return __version__
