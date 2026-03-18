import pyrogram.raw.core.primitives.string as string_module

_original_string_new = string_module.String.__new__

def _patched_string_new(cls, value: str):
    try:
        return _original_string_new(cls, value)
    except UnicodeEncodeError:
        clean_value = value.encode('utf-8', 'replace').decode('utf-8')
        return _original_string_new(cls, clean_value)

string_module.String.__new__ = _patched_string_new

from ub_core import BOT, LOGGER, Config, Convo, CustomDB, Message, bot
