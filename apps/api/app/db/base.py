import importlib
import pkgutil

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


def import_all_models() -> None:
    """
    Import all SQLAlchemy model modules so Base.metadata knows all tables.

    Celery worker does not boot FastAPI, so we must explicitly import models.
    This version only imports model files that actually exist.
    """

    import app.modules

    for module_info in pkgutil.walk_packages(
        app.modules.__path__,
        prefix="app.modules.",
    ):
        module_name = module_info.name

        if module_name.endswith(".models"):
            importlib.import_module(module_name)