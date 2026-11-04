# AgroDron - Sprint 1 / Epica 1 (v3)
# Punto de entrada principal (trazabilidad H5). La implementacion vive en src/
import sys
from src import core as _core
from src.core import *  # noqa: F401,F403

if __name__ == "__main__":
    sys.exit(_core.main())
