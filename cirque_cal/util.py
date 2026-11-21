import html
import re

_TAG = re.compile(r"<[^>]+>")
_BR = re.compile(r"<\s*(br|/p|/div|/li|/h\d)\s*/?>", re.I)


def html_to_text(s: str | None) -> str:
    """Crude HTML -> plain text (good enough for calendar descriptions)."""
    if not s:
        return ""
    s = _BR.sub("\n", s)
    s = _TAG.sub("", s)
    s = html.unescape(s).replace("\xa0", " ")
    lines = [ln.strip() for ln in s.splitlines()]
    out, blank = [], False
    for ln in lines:
        if not ln:
            if not blank and out:
                out.append("")
            blank = True
        else:
            out.append(ln)
            blank = False
    return "\n".join(out).strip()
