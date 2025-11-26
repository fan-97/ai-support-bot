from functools import wraps
from config.settings import ALLOWED_USER_IDS

def restricted(func):
    @wraps(func)
    async def wrapped(update, context, *args, **kwargs):
        if update.effective_user.id not in ALLOWED_USER_IDS: return
        return await func(update, context, *args, **kwargs)
    return wrapped
