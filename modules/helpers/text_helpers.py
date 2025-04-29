import html

def format_longtext(data, max_length=30000):
    """ Formate un champ longtext pour l'afficher dans une liste (abrégé + multi-lignes). """
    if isinstance(data, dict):
        text = data.get("text", "")
    else:
        text = str(data)

    text = text.replace("\n", " ").strip()

    if len(text) > max_length:
        return text[:max_length] + "..."
    return text

def format_multiline_text(data, max_length=30000):
    """Like format_longtext but *preserves* newlines for HTML <pre‑wrap> output."""
    if isinstance(data, dict):
        text = data.get("text", "")
    else:
        text = str(data)

    # keep your paragraph breaks
    text = text.replace("\r\n", "\n").strip()

    # truncate if too long
    if len(text) > max_length:
        return text[:max_length] + "…"
    return text

def rtf_to_html(rtf):
    """
    Convert RTF-JSON {"text":…, "formatting":…}
    into safe HTML with <strong>, <em>, <u> and <br>.
    """
    # 1) get raw text and formatting map
    text = rtf.get("text", "") if isinstance(rtf, dict) else str(rtf)
    fm   = rtf.get("formatting", {}) if isinstance(rtf, dict) else {}

    # 2) collect all the runs, coercing to ints
    tag_map = {"bold":"strong", "italic":"em", "underline":"u"}
    opens, closes = {}, {}
    for fmt, ranges in fm.items():
        tag = tag_map.get(fmt)
        if not tag:
            continue
        for start, end in ranges:
            try:
                s, e = int(start), int(end)
            except (TypeError, ValueError):
                continue
            if s < 0:        s = 0
            if e < s:        e = s
            if s > len(text): s = len(text)
            if e > len(text): e = len(text)
            opens.setdefault(s, []).append(tag)
            closes.setdefault(e, []).append(tag)

    # 3) build the HTML one character at a time
    out = []
    for i, ch in enumerate(text):
        # first close any tags at this position
        for tag in closes.get(i, []):
            out.append(f"</{tag}>")
        # then open any tags here
        for tag in opens.get(i, []):
            out.append(f"<{tag}>")

        # now the character (escaped or <br> for newline)
        if ch == "\n":
            out.append("<br>")
        else:
            out.append(html.escape(ch))

    # 4) close any tags hanging at end-of-text
    for tag in closes.get(len(text), []):
        out.append(f"</{tag}>")

    return "".join(out)