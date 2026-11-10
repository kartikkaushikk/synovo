"""Model package initializer.

Import all model modules so SQLAlchemy can resolve relationship targets.
"""

from app.models import analytics as _analytics  # noqa: F401
from app.models import job as _job  # noqa: F401
from app.models import transcript as _transcript  # noqa: F401
