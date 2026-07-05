#!/usr/bin/env python3
"""
AI File Analyzer v1.0
=====================
Analyzes Adobe Illustrator (.ai) files in a directory and generates
detailed interactive HTML and CSV reports including thumbnails, metadata,
font inventories, and artboard dimensions.

Requirements: Python 3.8+, PyMuPDF (pip install PyMuPDF)
Platform:     Windows 10/11 (also works on macOS/Linux)
"""

import os
import sys
import csv
import re
import html as html_module
import base64
import argparse
import textwrap
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Dependency check
# ---------------------------------------------------------------------------
try:
    import fitz  # PyMuPDF (traditional import)
except ImportError:
    try:
        import pymupdf as fitz  # PyMuPDF >= 1.24 alternative import
    except ImportError:
        print()
        print("  ERROR: Required package 'PyMuPDF' is not installed.")
        print("  Please run:  pip install PyMuPDF")
        print("  Or run setup.bat to install all dependencies.")
        print()
        input("  Press Enter to exit...")
        sys.exit(1)


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def format_file_size(size_bytes):
    """Convert bytes to human-readable file size."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def escape(text):
    """HTML-escape a string for safe embedding in HTML."""
    return html_module.escape(str(text))


# ---------------------------------------------------------------------------
# Core analyser
# ---------------------------------------------------------------------------

class AIFileAnalyzer:
    """Scans a directory for .ai files and produces HTML + CSV reports."""

    THUMBNAIL_SCALE = 0.3       # Render scale for thumbnails (0.3 = 30%)
    MAX_HEADER_BYTES = 200_000  # Bytes to read for PostScript header parsing

    def __init__(self, input_dir, output_dir=None, recursive=True):
        self.input_dir = Path(input_dir).resolve()
        if output_dir:
            self.output_dir = Path(output_dir).resolve()
        else:
            self.output_dir = self.input_dir / "_ai_analysis_report"
        self.recursive = recursive
        self.results = []
        self.errors = []

    # ------------------------------------------------------------------
    # File discovery
    # ------------------------------------------------------------------

    def discover_files(self):
        """Return a sorted list of .ai file paths in the input directory."""
        if self.recursive:
            files = list(self.input_dir.rglob("*.ai"))
            files += [f for f in self.input_dir.rglob("*.AI") if f not in files]
        else:
            files = list(self.input_dir.glob("*.ai"))
            files += [f for f in self.input_dir.glob("*.AI") if f not in files]
        return sorted(set(files))

    # ------------------------------------------------------------------
    # Single-file analysis
    # ------------------------------------------------------------------

    def analyze_file(self, filepath):
        """Analyse a single .ai file. Returns a metadata dictionary."""
        filepath = Path(filepath)
        stat = filepath.stat()

        result = {
            "filename":          filepath.name,
            "filepath":          str(filepath),
            "relative_path":     str(filepath.relative_to(self.input_dir)),
            "file_size":         stat.st_size,
            "file_size_human":   format_file_size(stat.st_size),
            "file_modified":     datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
            "format_type":       "Unknown",
            "creator_app":       "Unknown",
            "title":             "",
            "author":            "",
            "creation_date":     "Unknown",
            "modification_date": "Unknown",
            "page_count":        0,
            "width_pt":          0,
            "height_pt":         0,
            "width_mm":          0,
            "height_mm":         0,
            "width_in":          0,
            "height_in":         0,
            "dimensions_str":    "Unknown",
            "fonts":             [],
            "thumbnail_b64":     None,
            "pdf_compatible":    False,
            "errors":            [],
        }

        # --- Attempt PDF-compatible parsing (Illustrator 9+) ----------
        try:
            doc = fitz.open(str(filepath))
            result["pdf_compatible"] = True
            result["format_type"] = "PDF-Compatible AI"

            # Metadata
            meta = doc.metadata or {}
            result["creator_app"]       = meta.get("creator", "") or "Unknown"
            result["title"]             = meta.get("title", "") or ""
            result["author"]            = meta.get("author", "") or ""
            result["creation_date"]     = self._parse_date(meta.get("creationDate", ""))
            result["modification_date"] = self._parse_date(meta.get("modDate", ""))
            result["page_count"]        = doc.page_count

            if doc.page_count > 0:
                # Dimensions from first page (points → mm / inches)
                page = doc[0]
                rect = page.rect
                result["width_pt"]  = round(rect.width, 2)
                result["height_pt"] = round(rect.height, 2)
                result["width_mm"]  = round(rect.width * 25.4 / 72, 1)
                result["height_mm"] = round(rect.height * 25.4 / 72, 1)
                result["width_in"]  = round(rect.width / 72, 2)
                result["height_in"] = round(rect.height / 72, 2)
                result["dimensions_str"] = (
                    f"{result['width_mm']} \u00d7 {result['height_mm']} mm  "
                    f"({result['width_in']} \u00d7 {result['height_in']} in)"
                )

                # Fonts (scan up to 10 pages)
                fonts_set = set()
                for pg_num in range(min(doc.page_count, 10)):
                    try:
                        pg = doc[pg_num]
                        for font_tuple in pg.get_fonts(full=True):
                            # font_tuple layout: (xref, ext, type, basefont, name, encoding, ...)
                            font_name = font_tuple[3] if len(font_tuple) > 3 else ""
                            if font_name:
                                clean = font_name.split("+")[-1].strip()
                                if clean and clean.lower() != "none":
                                    fonts_set.add(clean)
                    except Exception:
                        pass
                result["fonts"] = sorted(fonts_set)

                # Thumbnail (render first page at reduced resolution)
                try:
                    mat = fitz.Matrix(self.THUMBNAIL_SCALE, self.THUMBNAIL_SCALE)
                    pix = doc[0].get_pixmap(matrix=mat, alpha=False)
                    result["thumbnail_b64"] = base64.b64encode(pix.tobytes("png")).decode("ascii")
                except Exception as exc:
                    result["errors"].append(f"Thumbnail generation failed: {exc}")

            doc.close()

        except Exception:
            # --- Fallback: legacy PostScript header parsing -----------
            result["pdf_compatible"] = False
            result["format_type"] = "Legacy PostScript AI"
            try:
                self._parse_postscript_header(filepath, result)
            except Exception as ps_err:
                result["errors"].append(f"PostScript parsing failed: {ps_err}")
                result["format_type"] = "Unreadable / Unknown"

        return result

    # ------------------------------------------------------------------
    # Date parsing
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_date(date_str):
        """Convert a PDF date string (D:YYYYMMDDHHmmSS+TZ) to readable text."""
        if not date_str:
            return "Unknown"
        cleaned = re.sub(r"^D:", "", date_str).strip("'")
        cleaned = re.sub(r"[+-]\d{2}'\d{2}'?$", "", cleaned)
        cleaned = re.sub(r"Z$", "", cleaned)
        for fmt, length in [
            ("%Y%m%d%H%M%S", 14),
            ("%Y%m%d%H%M",   12),
            ("%Y%m%d%H",     10),
            ("%Y%m%d",        8),
        ]:
            try:
                dt = datetime.strptime(cleaned[:length], fmt)
                if length >= 14:
                    return dt.strftime("%Y-%m-%d %H:%M:%S")
                return dt.strftime("%Y-%m-%d")
            except (ValueError, IndexError):
                continue
        return date_str  # Return raw string if nothing matched

    # ------------------------------------------------------------------
    # PostScript header fallback
    # ------------------------------------------------------------------

    def _parse_postscript_header(self, filepath, result):
        """Extract basic metadata from a PostScript/EPS-based AI file."""
        with open(filepath, "rb") as fh:
            header = fh.read(self.MAX_HEADER_BYTES).decode("latin-1", errors="replace")

        if not header.startswith("%!PS-Adobe") and not header.startswith("%PDF"):
            result["errors"].append("File does not appear to be a valid AI / PS file")
            return

        # Creator application
        m = re.search(r"%%Creator:\s*(.+)", header)
        if m:
            result["creator_app"] = m.group(1).strip()

        # Creation date
        m = re.search(r"%%CreationDate:\s*(.+)", header)
        if m:
            result["creation_date"] = m.group(1).strip()

        # Bounding box → dimensions
        m = re.search(r"%%BoundingBox:\s*([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)", header)
        if m:
            x1, y1, x2, y2 = (float(v) for v in m.groups())
            w_pt, h_pt = x2 - x1, y2 - y1
            result["width_pt"]  = round(w_pt, 2)
            result["height_pt"] = round(h_pt, 2)
            result["width_mm"]  = round(w_pt * 25.4 / 72, 1)
            result["height_mm"] = round(h_pt * 25.4 / 72, 1)
            result["width_in"]  = round(w_pt / 72, 2)
            result["height_in"] = round(h_pt / 72, 2)
            result["dimensions_str"] = (
                f"{result['width_mm']} \u00d7 {result['height_mm']} mm  "
                f"({result['width_in']} \u00d7 {result['height_in']} in)"
            )

        # Title
        m = re.search(r"%%Title:\s*(.+)", header)
        if m:
            result["title"] = m.group(1).strip().strip("()")

        # Fonts
        fonts_set = set()
        for m in re.finditer(r"%%DocumentFonts:\s*(.+)", header):
            for font in m.group(1).strip().split():
                if font and font != "(atend)":
                    fonts_set.add(font)
        for m in re.finditer(r"%%IncludeFont:\s*(.+)", header):
            fonts_set.add(m.group(1).strip())
        for m in re.finditer(r"/FontName\s*/(\S+)", header):
            fonts_set.add(m.group(1))
        result["fonts"] = sorted(fonts_set)

    # ------------------------------------------------------------------
    # HTML report
    # ------------------------------------------------------------------

    def generate_html_report(self, results, output_path):
        """Write an interactive, self-contained HTML report to *output_path*."""

        # ---- Build card markup for each file -------------------------
        cards_html_parts = []
        for r in results:
            fn_esc   = escape(r["filename"])
            path_esc = escape(r["relative_path"])

            # Thumbnail or placeholder
            if r["thumbnail_b64"]:
                thumb = (
                    f'<img src="data:image/png;base64,{r["thumbnail_b64"]}" '
                    f'alt="Preview of {fn_esc}" class="thumbnail">'
                )
            else:
                thumb = (
                    '<div class="no-thumbnail">'
                    '<svg viewBox="0 0 24 24" width="48" height="48" fill="none" '
                    'stroke="currentColor" stroke-width="1.5">'
                    '<path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/>'
                    '<polyline points="14,2 14,8 20,8"/></svg>'
                    '<span>No Preview</span></div>'
                )

            fonts_html = escape(", ".join(r["fonts"])) if r["fonts"] else '<span class="muted">None detected</span>'

            status_class = "status-ok" if r["pdf_compatible"] else "status-legacy"
            status_text  = "PDF-Compatible" if r["pdf_compatible"] else "Legacy PS"

            errors_html = ""
            if r["errors"]:
                errors_html = (
                    '<div class="card-errors">\u26a0 '
                    + escape("; ".join(r["errors"]))
                    + "</div>"
                )

            card = (
                f'<div class="card"'
                f' data-filename="{escape(r["filename"].lower())}"'
                f' data-fonts="{escape(" ".join(r["fonts"]).lower())}"'
                f' data-creator="{escape(r["creator_app"].lower())}"'
                f' data-format="{escape(r["format_type"].lower())}"'
                f' data-size="{r["file_size"]}"'
                f' data-modified="{escape(r["file_modified"])}">'
                f'<div class="card-preview">{thumb}</div>'
                f'<div class="card-info">'
                f'<h3 class="card-title" title="{fn_esc}">{fn_esc}</h3>'
                f'<div class="card-path" title="{path_esc}">{path_esc}</div>'
                f'<div class="card-meta">'
                f'<div class="meta-row"><span class="meta-label">Format</span>'
                f'<span class="meta-value"><span class="status-badge {status_class}">{status_text}</span></span></div>'
                f'<div class="meta-row"><span class="meta-label">Creator</span>'
                f'<span class="meta-value">{escape(r["creator_app"])}</span></div>'
                f'<div class="meta-row"><span class="meta-label">Dimensions</span>'
                f'<span class="meta-value">{escape(r["dimensions_str"])}</span></div>'
                f'<div class="meta-row"><span class="meta-label">File Size</span>'
                f'<span class="meta-value">{escape(r["file_size_human"])}</span></div>'
                f'<div class="meta-row"><span class="meta-label">Created</span>'
                f'<span class="meta-value">{escape(r["creation_date"])}</span></div>'
                f'<div class="meta-row"><span class="meta-label">Modified</span>'
                f'<span class="meta-value">{escape(r["file_modified"])}</span></div>'
                f'<div class="meta-row"><span class="meta-label">Pages</span>'
                f'<span class="meta-value">{r["page_count"]}</span></div>'
                f'<div class="meta-row fonts-row"><span class="meta-label">Fonts</span>'
                f'<span class="meta-value fonts-value">{fonts_html}</span></div>'
                f'</div>'  # card-meta
                f'{errors_html}'
                f'</div>'  # card-info
                f'</div>'  # card
            )
            cards_html_parts.append(card)

        cards_markup = "\n".join(cards_html_parts)

        # ---- Summary statistics --------------------------------------
        total_files     = len(results)
        pdf_compat      = sum(1 for r in results if r["pdf_compatible"])
        legacy          = total_files - pdf_compat
        total_size      = sum(r["file_size"] for r in results)
        all_fonts       = set()
        for r in results:
            all_fonts.update(r["fonts"])
        unique_fonts    = len(all_fonts)
        files_with_err  = sum(1 for r in results if r["errors"])

        fonts_items = "".join(f"<li>{escape(f)}</li>" for f in sorted(all_fonts))
        if not fonts_items:
            fonts_items = '<li class="muted">No fonts detected</li>'

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        source_dir_esc = escape(str(self.input_dir))

        # ---- Assemble full HTML --------------------------------------
        # NOTE: CSS and JS curly braces are *not* inside an f-string;
        # they are written via separate string concatenation to avoid
        # the need for {{ }} escaping throughout the entire template.
        html_content = self._html_template(
            timestamp=timestamp,
            source_dir=source_dir_esc,
            total_files=total_files,
            pdf_compat=pdf_compat,
            legacy=legacy,
            total_size_human=format_file_size(total_size),
            unique_fonts=unique_fonts,
            files_with_err=files_with_err,
            fonts_items=fonts_items,
            cards_markup=cards_markup,
        )

        with open(output_path, "w", encoding="utf-8") as fh:
            fh.write(html_content)

    @staticmethod
    def _html_template(*, timestamp, source_dir, total_files, pdf_compat,
                       legacy, total_size_human, unique_fonts,
                       files_with_err, fonts_items, cards_markup):
        """Return the complete HTML string for the report."""
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AI File Analysis Report</title>
<style>
:root {{
  --bg-primary:#0f1117;--bg-secondary:#1a1d27;--bg-card:#1e2130;
  --bg-card-hover:#252840;--border-color:#2d3148;--text-primary:#e8eaed;
  --text-secondary:#9aa0b4;--text-muted:#5f6580;
  --accent-blue:#4a9eff;--accent-purple:#a78bfa;--accent-green:#34d399;
  --accent-amber:#fbbf24;--accent-red:#f87171;
  --gradient-1:linear-gradient(135deg,#4a9eff 0%,#a78bfa 100%);
  --radius:12px;--radius-sm:8px;
  --shadow-hover:0 8px 32px rgba(74,158,255,.15);
}}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:'Segoe UI',-apple-system,BlinkMacSystemFont,sans-serif;
  background:var(--bg-primary);color:var(--text-primary);line-height:1.6;min-height:100vh}}
.header{{background:var(--bg-secondary);border-bottom:1px solid var(--border-color);
  padding:32px 40px;position:sticky;top:0;z-index:100;backdrop-filter:blur(20px)}}
.header-content{{max-width:1600px;margin:0 auto}}
.header h1{{font-size:28px;font-weight:700;background:var(--gradient-1);
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;margin-bottom:4px}}
.header-subtitle{{color:var(--text-secondary);font-size:14px}}
.stats-bar{{display:flex;gap:24px;margin-top:20px;flex-wrap:wrap}}
.stat-item{{background:var(--bg-card);border:1px solid var(--border-color);
  border-radius:var(--radius-sm);padding:12px 20px;min-width:140px}}
.stat-value{{font-size:24px;font-weight:700;color:var(--accent-blue)}}
.stat-label{{font-size:12px;color:var(--text-muted);text-transform:uppercase;letter-spacing:.5px}}
.toolbar{{max-width:1600px;margin:24px auto;padding:0 40px;display:flex;gap:16px;align-items:center;flex-wrap:wrap}}
.search-box{{flex:1;min-width:250px;position:relative}}
.search-box input{{width:100%;padding:10px 16px 10px 40px;background:var(--bg-secondary);
  border:1px solid var(--border-color);border-radius:var(--radius-sm);
  color:var(--text-primary);font-size:14px;outline:none;transition:border-color .2s}}
.search-box input:focus{{border-color:var(--accent-blue)}}
.search-box::before{{content:"\\1F50D";position:absolute;left:12px;top:50%;transform:translateY(-50%);font-size:14px}}
.filter-btn{{padding:10px 16px;background:var(--bg-secondary);border:1px solid var(--border-color);
  border-radius:var(--radius-sm);color:var(--text-secondary);font-size:13px;cursor:pointer;transition:all .2s}}
.filter-btn:hover,.filter-btn.active{{background:var(--bg-card-hover);border-color:var(--accent-blue);color:var(--text-primary)}}
.sort-select{{padding:10px 16px;background:var(--bg-secondary);border:1px solid var(--border-color);
  border-radius:var(--radius-sm);color:var(--text-primary);font-size:13px;cursor:pointer;outline:none}}
.main-content{{max-width:1600px;margin:0 auto;padding:0 40px 60px}}
.results-count{{color:var(--text-muted);font-size:13px;margin-bottom:16px}}
.cards-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(480px,1fr));gap:20px}}
.card{{background:var(--bg-card);border:1px solid var(--border-color);border-radius:var(--radius);
  overflow:hidden;display:flex;transition:all .3s ease}}
.card:hover{{border-color:rgba(74,158,255,.3);box-shadow:var(--shadow-hover);transform:translateY(-2px)}}
.card-preview{{width:180px;min-height:200px;background:#12141c;display:flex;align-items:center;
  justify-content:center;flex-shrink:0;overflow:hidden;border-right:1px solid var(--border-color)}}
.thumbnail{{max-width:100%;max-height:100%;object-fit:contain}}
.no-thumbnail{{display:flex;flex-direction:column;align-items:center;gap:8px;color:var(--text-muted);font-size:12px}}
.card-info{{flex:1;padding:16px;min-width:0}}
.card-title{{font-size:15px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;margin-bottom:2px}}
.card-path{{font-size:11px;color:var(--text-muted);white-space:nowrap;overflow:hidden;
  text-overflow:ellipsis;margin-bottom:12px;font-family:'Cascadia Code','Fira Code',monospace}}
.card-meta{{display:flex;flex-direction:column;gap:4px}}
.meta-row{{display:flex;gap:8px;font-size:12px;line-height:1.8}}
.meta-label{{color:var(--text-muted);min-width:80px;flex-shrink:0}}
.meta-value{{color:var(--text-secondary);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.fonts-row .meta-value{{white-space:normal}}
.status-badge{{display:inline-block;padding:1px 8px;border-radius:4px;font-size:11px;font-weight:600}}
.status-ok{{background:rgba(52,211,153,.15);color:var(--accent-green)}}
.status-legacy{{background:rgba(251,191,36,.15);color:var(--accent-amber)}}
.card-errors{{margin-top:8px;padding:8px;background:rgba(248,113,113,.1);border-radius:6px;font-size:11px;color:var(--accent-red)}}
.muted{{color:var(--text-muted)}}
.fonts-summary{{max-width:1600px;margin:24px auto;padding:0 40px}}
.fonts-summary details{{background:var(--bg-secondary);border:1px solid var(--border-color);border-radius:var(--radius-sm);padding:16px}}
.fonts-summary summary{{cursor:pointer;color:var(--accent-blue);font-weight:600;font-size:14px}}
.fonts-summary ul{{margin-top:12px;columns:3;column-gap:24px;list-style:none}}
.fonts-summary li{{padding:2px 0;font-size:13px;color:var(--text-secondary);break-inside:avoid}}
.fonts-summary li::before{{content:"\\2022";color:var(--accent-purple);margin-right:8px}}
footer{{text-align:center;padding:20px;color:var(--text-muted);font-size:12px;border-top:1px solid var(--border-color)}}
@media(max-width:768px){{
  .cards-grid{{grid-template-columns:1fr}}
  .card{{flex-direction:column}}
  .card-preview{{width:100%;min-height:150px;border-right:none;border-bottom:1px solid var(--border-color)}}
  .header{{padding:20px}}
  .toolbar,.main-content,.fonts-summary{{padding:0 20px}}
  .fonts-summary ul{{columns:1}}
}}
</style>
</head>
<body>
<div class="header"><div class="header-content">
<h1>AI File Analysis Report</h1>
<div class="header-subtitle">Generated on {timestamp} &nbsp;&bull;&nbsp; Source: {source_dir}</div>
<div class="stats-bar">
  <div class="stat-item"><div class="stat-value">{total_files}</div><div class="stat-label">Total Files</div></div>
  <div class="stat-item"><div class="stat-value">{pdf_compat}</div><div class="stat-label">PDF-Compatible</div></div>
  <div class="stat-item"><div class="stat-value">{legacy}</div><div class="stat-label">Legacy PostScript</div></div>
  <div class="stat-item"><div class="stat-value">{total_size_human}</div><div class="stat-label">Total Size</div></div>
  <div class="stat-item"><div class="stat-value">{unique_fonts}</div><div class="stat-label">Unique Fonts</div></div>
  <div class="stat-item"><div class="stat-value">{files_with_err}</div><div class="stat-label">Warnings</div></div>
</div>
</div></div>

<div class="fonts-summary"><details>
<summary>&#128203; All Unique Fonts Across Files ({unique_fonts} found)</summary>
<ul>{fonts_items}</ul>
</details></div>

<div class="toolbar">
  <div class="search-box"><input type="text" id="searchInput" placeholder="Search by filename, font, or creator..." oninput="filterCards()"></div>
  <button class="filter-btn active" onclick="setFilter('all',this)">All ({total_files})</button>
  <button class="filter-btn" onclick="setFilter('pdf',this)">PDF-Compatible ({pdf_compat})</button>
  <button class="filter-btn" onclick="setFilter('legacy',this)">Legacy ({legacy})</button>
  <select class="sort-select" id="sortSelect" onchange="sortCards()">
    <option value="name-asc">Sort: Name (A&#8594;Z)</option>
    <option value="name-desc">Sort: Name (Z&#8594;A)</option>
    <option value="size-desc">Sort: Size (Largest)</option>
    <option value="size-asc">Sort: Size (Smallest)</option>
    <option value="date-desc">Sort: Modified (Newest)</option>
    <option value="date-asc">Sort: Modified (Oldest)</option>
  </select>
</div>

<div class="main-content">
<div class="results-count" id="resultsCount">Showing {total_files} files</div>
<div class="cards-grid" id="cardsGrid">
{cards_markup}
</div>
</div>

<footer>AI File Analyzer Report &nbsp;&bull;&nbsp; Generated {timestamp}</footer>

<script>
var currentFilter='all';
function filterCards(){{var q=document.getElementById('searchInput').value.toLowerCase(),
  cards=document.querySelectorAll('.card'),v=0;
  cards.forEach(function(c){{var fn=c.dataset.filename||'',fo=c.dataset.fonts||'',cr=c.dataset.creator||'',
    fmt=c.dataset.format||'';
    var ms=!q||fn.indexOf(q)!==-1||fo.indexOf(q)!==-1||cr.indexOf(q)!==-1;
    var mf=currentFilter==='all'||(currentFilter==='pdf'&&fmt.indexOf('pdf')!==-1)||
      (currentFilter==='legacy'&&fmt.indexOf('postscript')!==-1);
    var show=ms&&mf;c.style.display=show?'':'none';if(show)v++}});
  document.getElementById('resultsCount').textContent='Showing '+v+' of {total_files} files'}}
function setFilter(f,btn){{currentFilter=f;
  document.querySelectorAll('.filter-btn').forEach(function(b){{b.classList.remove('active')}});
  btn.classList.add('active');filterCards()}}
function sortCards(){{var grid=document.getElementById('cardsGrid'),
  cards=Array.prototype.slice.call(grid.querySelectorAll('.card')),
  s=document.getElementById('sortSelect').value;
  cards.sort(function(a,b){{switch(s){{
    case'name-asc':return(a.dataset.filename||'').localeCompare(b.dataset.filename||'');
    case'name-desc':return(b.dataset.filename||'').localeCompare(a.dataset.filename||'');
    case'size-desc':return parseInt(b.dataset.size||0)-parseInt(a.dataset.size||0);
    case'size-asc':return parseInt(a.dataset.size||0)-parseInt(b.dataset.size||0);
    case'date-desc':return(b.dataset.modified||'').localeCompare(a.dataset.modified||'');
    case'date-asc':return(a.dataset.modified||'').localeCompare(b.dataset.modified||'');
    }}return 0}});
  cards.forEach(function(c){{grid.appendChild(c)}})}}
</script>
</body>
</html>"""

    # ------------------------------------------------------------------
    # CSV report
    # ------------------------------------------------------------------

    def generate_csv_report(self, results, output_path):
        """Write a CSV spreadsheet to *output_path*."""
        fieldnames = [
            "Filename", "Relative Path", "File Size", "File Size (Bytes)",
            "Format Type", "PDF Compatible", "Creator Application",
            "Title", "Author", "Creation Date", "File Modified Date",
            "Page Count", "Width (mm)", "Height (mm)", "Width (in)", "Height (in)",
            "Width (pt)", "Height (pt)", "Fonts", "Warnings",
        ]
        with open(output_path, "w", newline="", encoding="utf-8-sig") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames)
            writer.writeheader()
            for r in results:
                writer.writerow({
                    "Filename":            r["filename"],
                    "Relative Path":       r["relative_path"],
                    "File Size":           r["file_size_human"],
                    "File Size (Bytes)":   r["file_size"],
                    "Format Type":         r["format_type"],
                    "PDF Compatible":      "Yes" if r["pdf_compatible"] else "No",
                    "Creator Application": r["creator_app"],
                    "Title":               r["title"],
                    "Author":              r["author"],
                    "Creation Date":       r["creation_date"],
                    "File Modified Date":  r["file_modified"],
                    "Page Count":          r["page_count"],
                    "Width (mm)":          r["width_mm"],
                    "Height (mm)":         r["height_mm"],
                    "Width (in)":          r["width_in"],
                    "Height (in)":         r["height_in"],
                    "Width (pt)":          r["width_pt"],
                    "Height (pt)":         r["height_pt"],
                    "Fonts":               "; ".join(r["fonts"]),
                    "Warnings":            "; ".join(r["errors"]),
                })

    # ------------------------------------------------------------------
    # Main pipeline
    # ------------------------------------------------------------------

    def run(self):
        """Execute the full analysis pipeline. Returns True on success."""
        print()
        print("=" * 60)
        print("  AI File Analyzer v1.0")
        print("=" * 60)
        print()

        # Validate input
        if not self.input_dir.exists():
            print(f"  ERROR: Directory not found: {self.input_dir}")
            return False
        if not self.input_dir.is_dir():
            print(f"  ERROR: Not a directory: {self.input_dir}")
            return False

        print(f"  Scanning:   {self.input_dir}")
        print(f"  Recursive:  {'Yes' if self.recursive else 'No'}")
        print()

        files = self.discover_files()
        if not files:
            print("  No .ai files found in the specified directory.")
            return False

        print(f"  Found {len(files)} .ai file(s)")
        print()

        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Analyse each file
        print("  Analyzing files...")
        print("  " + "-" * 50)
        width = len(str(len(files)))

        for i, fpath in enumerate(files, 1):
            name = fpath.name
            display = name if len(name) <= 40 else name[:37] + "..."
            print(f"  [{i:>{width}}/{len(files)}] {display}", end="", flush=True)
            try:
                result = self.analyze_file(fpath)
                self.results.append(result)
                marker = "\u2713" if result["pdf_compatible"] else "\u25cb"
                print(f"  {marker}")
            except Exception as exc:
                print(f"  \u2717 Error: {exc}")
                self.errors.append((str(fpath), str(exc)))

        print("  " + "-" * 50)
        print()

        # Generate reports
        html_path = self.output_dir / "ai_analysis_report.html"
        csv_path  = self.output_dir / "ai_analysis_report.csv"

        print("  Generating reports...")
        self.generate_html_report(self.results, html_path)
        print(f"    \u2713 HTML Report: {html_path}")
        self.generate_csv_report(self.results, csv_path)
        print(f"    \u2713 CSV Report:  {csv_path}")

        # Summary
        print()
        print("  " + "=" * 50)
        print("  SUMMARY")
        print("  " + "=" * 50)
        print(f"    Total files analyzed:  {len(self.results)}")
        print(f"    PDF-compatible:        {sum(1 for r in self.results if r['pdf_compatible'])}")
        print(f"    Legacy PostScript:     {sum(1 for r in self.results if not r['pdf_compatible'])}")
        print(f"    With thumbnails:       {sum(1 for r in self.results if r['thumbnail_b64'])}")
        all_fonts = set()
        for r in self.results:
            all_fonts.update(r["fonts"])
        print(f"    Unique fonts found:    {len(all_fonts)}")
        print(f"    Total size:            {format_file_size(sum(r['file_size'] for r in self.results))}")
        if self.errors:
            print(f"    Errors:                {len(self.errors)}")
        print()
        print(f"  Reports saved to: {self.output_dir}")
        print()

        return True


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Analyze Adobe Illustrator (.ai) files and generate reports.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
        Examples
        --------
          python analyze_ai_files.py "C:\\Design Files\\Logos"
          python analyze_ai_files.py "D:\\Archive" -o "D:\\Reports"
          python analyze_ai_files.py "C:\\Projects" --no-recursive
        """),
    )
    parser.add_argument("directory", help="Path to the directory containing .ai files")
    parser.add_argument("-o", "--output", default=None,
                        help="Output directory for reports (default: <directory>/_ai_analysis_report)")
    parser.add_argument("--no-recursive", action="store_true",
                        help="Do not scan subdirectories")
    args = parser.parse_args()

    analyzer = AIFileAnalyzer(
        input_dir=args.directory,
        output_dir=args.output,
        recursive=not args.no_recursive,
    )

    success = analyzer.run()

    if success:
        html_path = analyzer.output_dir / "ai_analysis_report.html"
        try:
            import webbrowser
            webbrowser.open(str(html_path))
            print("  HTML report opened in your default browser.")
            print()
        except Exception:
            print("  Open the HTML report manually in your web browser.")
            print()

    input("  Press Enter to exit...")


if __name__ == "__main__":
    main()
