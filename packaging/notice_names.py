"""Notice filename discovery only; a match does not establish licence coverage."""
import re


def is_notice_name(name, *, strict=False):
    """Accept both licence spellings; Cargo retains its bounded basename rule.

    Other collectors also retain aggregate/prefixed notice filenames. Callers
    still own path safety, size limits, original-byte retention and scope.
    """
    if not isinstance(name, str) or not name or '/' in name or '\\' in name:
        return False
    if strict:
        return re.fullmatch(r'(?:(?:UN)?LICEN[CS]E|COPYING|NOTICE|COPYRIGHT)(?:[._-].*)?', name, re.I) is not None
    return re.search(r'licen[cs]e|copying|notice|copyright', name, re.I) is not None
