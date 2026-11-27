"""One-line material labels: never repeat a name, and show well-known equivalent designations."""
import re

# Equivalent designations shown only when the record itself does not already carry one.
ALIASES = {'AISI316L': '1.4404', 'AISI304L': '1.4307', 'CUNI10FE1MN': 'CW352H'}


def _code(text):
    return re.sub(r'[^A-Z0-9]', '', str(text or '').upper())


def material_label(name, designation):
    name = str(name or '').strip()
    designation = str(designation or '').strip()
    if not designation or _code(designation) == _code(name):
        designation = ALIASES.get(_code(name), '')
    return f'{name} ({designation})' if designation else name
