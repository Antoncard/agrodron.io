# Punto de entrada minimo de AgroDron (llama a src.cli.main)
import sys

from src import cli
from src.almacen import *  # noqa: F401,F403
from src.cli import main  # noqa: F401
from src.dominio import *  # noqa: F401,F403

if __name__ == "__main__":
    sys.exit(cli.main())
