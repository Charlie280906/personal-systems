#!/usr/bin/env python3
"""
cv_to_gdoc.py - build a two-column CV in a Google Doc from a JSON file.

What it does
  1. Clears the doc body and creates a 1 x 2 table (page set to A4).
  2. Removes every table border.
  3. Fills the right-hand cell with #299d8f.
  4. Writes the JSON content into the two cells, matching the CV template:
        left cell : name, introduction, Education, Certificates/Qualifications,
                    Employment, Work Experience/Volunteering, References
        right cell: Personal details, Skills, Interests/Hobbies
  5. Gives each kind of text its own Google Docs paragraph style, so you can
     restyle everything of the same priority at once:

        TITLE      name                                   (left)
        NORMAL     introduction / descriptions / bullets   (left)
        HEADING_1  section headings                        (left)
        HEADING_2  entry titles  "Role - Company"          (left)
        SUBTITLE   dates                                   (left)
        HEADING_6  certificate names                       (left)
        HEADING_3  sidebar section headings                (right)
        HEADING_4  sidebar labels and skills/hobbies       (right)
        HEADING_5  sidebar values (phone, email, ...)      (right)

     The Docs API cannot edit the named styles themselves, so the script also
     applies matching direct formatting (see STYLES below). To turn that into
     real styles: click one paragraph of a type, then
     Format > Paragraph styles > Update '<style>' to match.

Usage
  pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib
  python cv_to_gdoc.py <DOC_ID_or_URL> cv.json
  python cv_to_gdoc.py cv.json --dry-run          # preview structure, no Google calls

Setup: enable the Google Docs API in Google Cloud, create an OAuth client ID
of type "Desktop app", and save it next to this script as credentials.json.
The first run opens a browser to authorise; the token is cached in token.json.
"""

import argparse
import json
import os
import re
import sys

# --------------------------------------------------------------------------
# Config - tweak these to change the look
# --------------------------------------------------------------------------
SCOPES = ["https://www.googleapis.com/auth/documents"]

TEAL = "#299d8f"
WHITE = "#ffffff"
BLACK = "#000000"
GREY = "#999999"
RULE_GREY = "#666666"
FONT = "DM Sans"

PAGE_W, PAGE_H = 595.28, 841.89      # A4 in points
MARGIN_TOP, MARGIN_BOTTOM = 36, 36
MARGIN_SIDE = 14
LEFT_FRACTION = 0.65                 # share of the table width given to the left column

# Paragraph/text formatting per Google Docs style.
#   para: alignment, spaceAbove, spaceBelow (pt), lineSpacing (%)
#   text: size (pt), bold, italic, underline, color
STYLES = {
    "TITLE": dict(
        para=dict(alignment="CENTER", spaceAbove=0, spaceBelow=6, lineSpacing=100),
        text=dict(size=24, bold=True, italic=False, underline=False, color=TEAL)),
    "NORMAL_TEXT": dict(
        para=dict(alignment="START", spaceAbove=0, spaceBelow=0, lineSpacing=105),
        text=dict(size=10, bold=False, italic=False, underline=False, color=BLACK)),
    "HEADING_1": dict(
        para=dict(alignment="CENTER", spaceAbove=16, spaceBelow=6, lineSpacing=100),
        text=dict(size=16, bold=True, italic=False, underline=True, color=TEAL)),
    "HEADING_2": dict(
        para=dict(alignment="START", spaceAbove=10, spaceBelow=0, lineSpacing=100),
        text=dict(size=11, bold=True, italic=False, underline=False, color=BLACK)),
    "SUBTITLE": dict(
        para=dict(alignment="START", spaceAbove=2, spaceBelow=0, lineSpacing=100),
        text=dict(size=8, bold=False, italic=True, underline=False, color=GREY)),
    "HEADING_6": dict(
        para=dict(alignment="START", spaceAbove=7, spaceBelow=7, lineSpacing=100),
        text=dict(size=10, bold=True, italic=False, underline=False, color=BLACK)),
    "HEADING_3": dict(
        para=dict(alignment="CENTER", spaceAbove=16, spaceBelow=6, lineSpacing=100),
        text=dict(size=11, bold=True, italic=False, underline=True, color=WHITE)),
    "HEADING_4": dict(
        para=dict(alignment="START", spaceAbove=8, spaceBelow=2, lineSpacing=100),
        text=dict(size=9, bold=True, italic=False, underline=False, color=WHITE)),
    "HEADING_5": dict(
        para=dict(alignment="START", spaceAbove=0, spaceBelow=0, lineSpacing=105),
        text=dict(size=9, bold=False, italic=False, underline=False, color=WHITE)),
}

# Inline formatting applied on top of a paragraph's style
RUN_STYLES = {
    "year": dict(size=9, bold=False, italic=True, color=GREY),
}

# Sidebar headings (JSON key -> displayed text)
SIDEBAR_TITLES = {
    "personal details": "Personal details",
    "skills": "Skills",
    "interests/hobbies": "Interests/Hobbies",
}

# Order sections appear in the left column (JSON key, style of its entries)
LEFT_SECTIONS = [
    "education",
    "certificates/qualifications",
    "employment",
    "work experience/volunteering",
    "references",
]


# --------------------------------------------------------------------------
# Content model
# --------------------------------------------------------------------------
class P:
    """One paragraph: a Docs style plus one or more (text, run_style) runs."""

    def __init__(self, style, runs, rule=False, bullet=False):
        self.style = style
        self.runs = [(runs, None)] if isinstance(runs, str) else list(runs)
        self.rule = rule        # horizontal line under this paragraph
        self.bullet = bullet

    @property
    def text(self):
        return "".join(t for t, _ in self.runs)


def cap(s):
    """Capitalise the first letter of each word, keeping the rest as typed.
    'le massif de charlevoix' -> 'Le Massif De Charlevoix'; 'Full-time' stays."""
    return re.sub(r"(^|[\s/])([a-z])", lambda m: m.group(1) + m.group(2).upper(), str(s).strip())


def as_list(v):
    if v is None or v == "":
        return []
    return list(v) if isinstance(v, (list, tuple)) else [v]


def entries_of(section):
    """Education can be a single entry, a list of entries, or a dict of entries."""
    if isinstance(section, list):
        return section
    if isinstance(section, dict):
        if section and all(isinstance(v, dict) for v in section.values()):
            return list(section.values())     # {"a-levels": {...}, "gcses": {...}}
        return [section]                       # one flat entry
    return []


def entry_title(role, company):
    parts = [cap(x) for x in (role, company) if x]
    return " - ".join(parts)


def close_block(block, is_last):
    """Put a rule under the last paragraph of a block (unless it's the final block)."""
    if block and not is_last:
        block[-1].rule = True
    return block


# --------------------------------------------------------------------------
# JSON -> paragraphs
# --------------------------------------------------------------------------
def build_content(data, sort_certs=True):
    # ---------- left cell ----------
    blocks = []

    head = []
    name = data.get("personal details", {}).get("name")
    if name:
        head.append(P("TITLE", name))
    if data.get("introduction"):
        head.append(P("NORMAL_TEXT", data["introduction"]))
    blocks.append(head)

    for key in LEFT_SECTIONS:
        if key not in data or not data[key]:
            continue
        sec = data[key]
        block = [P("HEADING_1", cap(key))]

        if key == "education":
            for e in entries_of(sec):
                # Optional keys not in the base format: "title", "intro"
                if e.get("title"):
                    block.append(P("HEADING_2", e["title"]))
                if e.get("dates"):
                    block.append(P("SUBTITLE", str(e["dates"]).upper()))
                if e.get("intro"):
                    block.append(P("NORMAL_TEXT", e["intro"]))
                for s in as_list(e.get("subjects")):
                    block.append(P("NORMAL_TEXT", s, bullet=True))

        elif key == "certificates/qualifications":
            if sec.get("intro"):
                block.append(P("NORMAL_TEXT", sec["intro"]))
            seen, opts = set(), []
            for item in sec.get("options", []):
                t = (str(item[0]).strip(), str(item[1]).strip() if len(item) > 1 else "")
                if t not in seen:                       # drop exact duplicates
                    seen.add(t)
                    opts.append(t)
            if sort_certs:                               # newest first, stable
                opts.sort(key=lambda t: -int(t[1]) if t[1].isdigit() else 0)
            for title, year in opts:
                runs = [(title, None)]
                if year:
                    runs.append(("  " + year, "year"))
                block.append(P("HEADING_6", runs))

        elif key in ("employment", "work experience/volunteering"):
            for company, e in sec.items():
                block.append(P("HEADING_2", entry_title(e.get("role"), company)))
                if e.get("dates"):
                    block.append(P("SUBTITLE", str(e["dates"]).upper()))
                if e.get("description"):
                    block.append(P("NORMAL_TEXT", e["description"]))

        elif key == "references":
            block.append(P("NORMAL_TEXT", sec))

        blocks.append(block)

    left = []
    for i, b in enumerate(blocks):
        left += close_block(b, i == len(blocks) - 1)

    # ---------- right cell ----------
    right = []
    pd = data.get("personal details", {})
    right.append(P("HEADING_3", SIDEBAR_TITLES["personal details"]))
    fields = [
        ("Location:", " / ".join(map(str, as_list(pd.get("location")))), None),
        ("Phone number:", None, as_list(pd.get("phone"))),
        ("Email:", None, as_list(pd.get("email"))),
        ("Driving licences:", ", ".join(map(str, as_list(pd.get("driving licenses")))), None),
    ]
    for label, joined, lines in fields:
        values = [joined] if joined else (lines or [])
        if not values:
            continue
        right.append(P("HEADING_4", label))
        for v in values:
            right.append(P("HEADING_5", str(v)))

    for key in ("skills", "interests/hobbies"):
        items = as_list(data.get(key))
        if items:
            right.append(P("HEADING_3", SIDEBAR_TITLES[key]))
            right += [P("HEADING_4", str(i)) for i in items]

    return left, right


# --------------------------------------------------------------------------
# Docs API request builders
# --------------------------------------------------------------------------
def u16(s):
    """Length in UTF-16 code units, which is how Docs counts indexes."""
    return len(s.encode("utf-16-le")) // 2


def rgb(hexstr):
    h = hexstr.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    return {"red": r, "green": g, "blue": b}


def pt(v):
    return {"magnitude": v, "unit": "PT"}


def text_style(spec):
    """Only the keys present in `spec` are written (and put in the field mask)."""
    ts, fields = {}, []
    if "size" in spec:
        ts["fontSize"] = pt(spec["size"]); fields.append("fontSize")
    for k in ("bold", "italic", "underline"):
        if k in spec:
            ts[k] = spec[k]; fields.append(k)
    if "color" in spec:
        ts["foregroundColor"] = {"color": {"rgbColor": rgb(spec["color"])}}
        fields.append("foregroundColor")
    return ts, fields


def build_cell_requests(paragraphs, start):
    """Requests that write `paragraphs` into an (empty) table cell whose first
    paragraph starts at index `start`. Nothing here shifts indexes after the
    initial insertText, so every range can be computed up front."""
    text = "\n".join(p.text for p in paragraphs)
    reqs = [{"insertText": {"location": {"index": start}, "text": text}}]

    # one font setting for the whole cell
    reqs.append({"updateTextStyle": {
        "range": {"startIndex": start, "endIndex": start + u16(text)},
        "textStyle": {"weightedFontFamily": {"fontFamily": FONT}},
        "fields": "weightedFontFamily"}})

    offset = start
    bullet_groups, current = [], None
    for p in paragraphs:
        n = u16(p.text)
        p_start, p_text_end, p_end = offset, offset + n, offset + n + 1
        spec = STYLES[p.style]

        # paragraph style
        ps = {"namedStyleType": p.style}
        fields = ["namedStyleType", "borderBottom"]
        ps["alignment"] = spec["para"]["alignment"]
        ps["spaceAbove"] = pt(spec["para"]["spaceAbove"])
        ps["spaceBelow"] = pt(spec["para"]["spaceBelow"])
        ps["lineSpacing"] = spec["para"]["lineSpacing"]
        fields += ["alignment", "spaceAbove", "spaceBelow", "lineSpacing"]
        if p.rule:
            ps["borderBottom"] = {
                "color": {"color": {"rgbColor": rgb(RULE_GREY)}},
                "width": pt(0.75), "padding": pt(8), "dashStyle": "SOLID"}
        reqs.append({"updateParagraphStyle": {
            "range": {"startIndex": p_start, "endIndex": p_end},
            "paragraphStyle": ps, "fields": ",".join(fields)}})

        # text style for the whole paragraph, then inline run overrides
        if n:
            ts, tf = text_style(spec["text"])
            reqs.append({"updateTextStyle": {
                "range": {"startIndex": p_start, "endIndex": p_text_end},
                "textStyle": ts, "fields": ",".join(tf)}})
            run_off = p_start
            for run_text, run_style in p.runs:
                rl = u16(run_text)
                if run_style:
                    ts, tf = text_style(RUN_STYLES[run_style])
                    reqs.append({"updateTextStyle": {
                        "range": {"startIndex": run_off, "endIndex": run_off + rl},
                        "textStyle": ts, "fields": ",".join(tf)}})
                run_off += rl

        # collect consecutive bullet paragraphs into one list
        if p.bullet:
            if current is None:
                current = [p_start, p_end]
                bullet_groups.append(current)
            else:
                current[1] = p_end
        else:
            current = None

        offset = p_end

    for s, e in bullet_groups:
        reqs.append({"createParagraphBullets": {
            "range": {"startIndex": s, "endIndex": e},
            "bulletPreset": "BULLET_DISC_CIRCLE_SQUARE"}})
    return reqs


def build_table_requests(table_start):
    loc = {"index": table_start}

    def cell(col, span=1):
        return {"tableCellLocation": {"tableStartLocation": loc, "rowIndex": 0, "columnIndex": col},
                "rowSpan": 1, "columnSpan": span}

    no_border = {"width": pt(0), "dashStyle": "SOLID", "color": {"color": {"rgbColor": rgb(WHITE)}}}   # no color = transparent
    total = PAGE_W - 2 * MARGIN_SIDE
    left_w = round(total * LEFT_FRACTION, 2)
    right_w = round(total - left_w, 2)

    reqs = []
    for idx, w in ((0, left_w), (1, right_w)):
        reqs.append({"updateTableColumnProperties": {
            "tableStartLocation": loc, "columnIndices": [idx],
            "tableColumnProperties": {"widthType": "FIXED_WIDTH", "width": pt(w)},
            "fields": "widthType,width"}})

    reqs.append({"updateTableRowStyle": {
        "tableStartLocation": loc, "rowIndices": [0],
        "tableRowStyle": {"preventOverflow": False},
        "fields": "preventOverflow"}})

    # 2. remove all borders
    reqs.append({"updateTableCellStyle": {
        "tableRange": cell(0, 2),
        "tableCellStyle": {"borderTop": no_border, "borderBottom": no_border,
                           "borderLeft": no_border, "borderRight": no_border},
        "fields": "borderTop,borderBottom,borderLeft,borderRight"}})

    # left cell padding
    reqs.append({"updateTableCellStyle": {
        "tableRange": cell(0),
        "tableCellStyle": {"paddingTop": pt(14), "paddingBottom": pt(14),
                           "paddingLeft": pt(22), "paddingRight": pt(22),
                           "contentAlignment": "TOP"},
        "fields": "paddingTop,paddingBottom,paddingLeft,paddingRight,contentAlignment"}})

    # 3. right cell colour #299d8f
    reqs.append({"updateTableCellStyle": {
        "tableRange": cell(1),
        "tableCellStyle": {"backgroundColor": {"color": {"rgbColor": rgb(TEAL)}},
                           "paddingTop": pt(14), "paddingBottom": pt(14),
                           "paddingLeft": pt(16), "paddingRight": pt(16),
                           "contentAlignment": "TOP"},
        "fields": "backgroundColor,paddingTop,paddingBottom,paddingLeft,paddingRight,contentAlignment"}})
    return reqs


# --------------------------------------------------------------------------
# Google plumbing
# --------------------------------------------------------------------------
def get_service(credentials_file, token_file):
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    creds = None
    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(credentials_file, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_file, "w") as f:
            f.write(creds.to_json())
    return build("docs", "v1", credentials=creds)


def parse_doc_id(s):
    m = re.search(r"/document/d/([A-Za-z0-9_-]+)", s)
    return m.group(1) if m else s


def find_table(doc):
    for el in doc["body"]["content"]:
        if "table" in el:
            return el
    raise RuntimeError("Table was not found in the document after inserting it.")


def tidy_around_table(docs, doc_id):
    """Docs always keeps a paragraph after a table (and may leave one before it).
    Remove the leading one if allowed; shrink whatever can't be removed so it
    doesn't create blank space or an extra page."""
    from googleapiclient.errors import HttpError

    doc = docs.get(documentId=doc_id).execute()
    content = doc["body"]["content"]
    t = next(i for i, e in enumerate(content) if "table" in e)
    leading = [e for e in content[:t] if "paragraph" in e]
    trailing = [e for e in content[t + 1:] if "paragraph" in e]

    def shrink(els):
        out = []
        for e in els:
            rng = {"startIndex": e["startIndex"], "endIndex": e["endIndex"]}
            out.append({"updateParagraphStyle": {
                "range": rng, "fields": "spaceAbove,spaceBelow,lineSpacing",
                "paragraphStyle": {"spaceAbove": pt(0), "spaceBelow": pt(0), "lineSpacing": 100}}})
            out.append({"updateTextStyle": {
                "range": rng, "fields": "fontSize",
                "textStyle": {"fontSize": pt(1)}}})
        return out

    if trailing:
        docs.batchUpdate(documentId=doc_id, body={"requests": shrink(trailing)}).execute()
    if leading:
        try:
            docs.batchUpdate(documentId=doc_id, body={"requests": [{"deleteContentRange": {
                "range": {"startIndex": leading[0]["startIndex"],
                          "endIndex": leading[-1]["endIndex"]}}}]}).execute()
        except HttpError:
            docs.batchUpdate(documentId=doc_id, body={"requests": shrink(leading)}).execute()


def build_doc(service, doc_id, data, sort_certs=True):
    docs = service.documents()
    left, right = build_content(data, sort_certs)

    # --- step 1: clear the body, set the page up, insert the 1x2 table
    doc = docs.get(documentId=doc_id).execute()
    end = doc["body"]["content"][-1]["endIndex"]
    reqs = []
    if end - 1 > 1:
        reqs.append({"deleteContentRange": {"range": {"startIndex": 1, "endIndex": end - 1}}})
    reqs.append({"updateDocumentStyle": {
        "documentStyle": {"pageSize": {"width": pt(PAGE_W), "height": pt(PAGE_H)},
                          "marginTop": pt(MARGIN_TOP), "marginBottom": pt(MARGIN_BOTTOM),
                          "marginLeft": pt(MARGIN_SIDE), "marginRight": pt(MARGIN_SIDE)},
        "fields": "pageSize,marginTop,marginBottom,marginLeft,marginRight"}})
    reqs.append({"insertTable": {"rows": 1, "columns": 2, "location": {"index": 1}}})
    docs.batchUpdate(documentId=doc_id, body={"requests": reqs}).execute()

    # --- step 2: read back the real table/cell indexes
    doc = docs.get(documentId=doc_id).execute()
    table_el = find_table(doc)
    cells = table_el["table"]["tableRows"][0]["tableCells"]
    left_start = cells[0]["content"][0]["startIndex"]
    right_start = cells[1]["content"][0]["startIndex"]

    # --- step 3: borders, colour, and content. The right cell is filled first:
    # it sits later in the document, so filling the left cell afterwards cannot
    # move any index we've already used.
    reqs = build_table_requests(table_el["startIndex"])
    reqs += build_cell_requests(right, right_start)
    reqs += build_cell_requests(left, left_start)
    docs.batchUpdate(documentId=doc_id, body={"requests": reqs}).execute()

    tidy_around_table(docs, doc_id)


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------
def dry_run(data, sort_certs):
    left, right = build_content(data, sort_certs)
    for title, paras in (("LEFT CELL", left), ("RIGHT CELL (#299d8f)", right)):
        print(f"\n=== {title} ===")
        for p in paras:
            flags = (" [bullet]" if p.bullet else "") + (" [rule below]" if p.rule else "")
            t = p.text if len(p.text) < 70 else p.text[:67] + "..."
            print(f"{p.style:<12}{t}{flags}")


def main():
    ap = argparse.ArgumentParser(description="Build a CV in a Google Doc from JSON.")
    ap.add_argument("args", nargs="+", metavar="[DOC_ID_or_URL] JSON_FILE")
    ap.add_argument("--credentials", default="credentials.json")
    ap.add_argument("--token", default="token.json")
    ap.add_argument("--no-sort-certs", action="store_true",
                    help="keep certificates in JSON order instead of newest-first")
    ap.add_argument("--dry-run", action="store_true",
                    help="print the structure that would be written; no Google calls")
    a = ap.parse_args()

    json_path = a.args[-1]
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)

    if a.dry_run:
        dry_run(data, not a.no_sort_certs)
        return
    if len(a.args) < 2:
        ap.error("give a DOC_ID_or_URL followed by the JSON file")

    doc_id = parse_doc_id(a.args[0])
    service = get_service(a.credentials, a.token)
    build_doc(service, doc_id, data, sort_certs=not a.no_sort_certs)
    print(f"Done: https://docs.google.com/document/d/{doc_id}/edit")


if __name__ == "__main__":
    main()