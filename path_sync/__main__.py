import logging

from path_sync._internal import (  # noqa: F401
    cmd_boot,
    cmd_copy,
    cmd_dep_update,
    cmd_merge,
    cmd_prune,
    cmd_pull,
    cmd_validate,
)
from path_sync._internal.models import LOG_FORMAT
from path_sync._internal.typer_app import app


def main() -> None:
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
    app()


if __name__ == "__main__":
    main()
