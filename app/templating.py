from fastapi.templating import Jinja2Templates

from app.config import BASE_DIR
from app.constants import OPERATION_STATUSES, OPERATION_TYPES, PERSON_TYPES, ROLES

templates = Jinja2Templates(directory=str(BASE_DIR / "app" / "templates"))
templates.env.globals.update(
    ROLES=ROLES,
    PERSON_TYPES=PERSON_TYPES,
    OPERATION_TYPES=OPERATION_TYPES,
    OPERATION_STATUSES=OPERATION_STATUSES,
)
