# AI File Analyzer

**Analyze an entire directory of Adobe Illustrator (`.ai`) files at once — without opening them in Illustrator.**

Generates a visual, interactive HTML report with thumbnails and a CSV spreadsheet containing detailed metadata for every file.

---

## What This Tool Does

For every `.ai` file in your chosen directory (and its subdirectories), the analyzer extracts:

| Data Point           | Description                                               |
| -------------------- | --------------------------------------------------------- |
| **Thumbnail**        | Rendered preview image of the first page/artboard         |
| **Format Type**      | Whether the file is PDF-compatible (v9+) or legacy PostScript |
| **Creator App**      | The version of Illustrator (or other app) that saved it   |
| **Artboard Size**    | Width × Height in millimetres, inches, and points         |
| **Page Count**       | Number of pages/artboards in the file                     |
| **Fonts Used**       | Every font referenced in the document                     |
| **Creation Date**    | When the file was originally created                      |
| **Modification Date**| When the file was last modified on disk                   |
| **File Size**        | Human-readable size (KB / MB / GB)                        |
| **Title & Author**   | Embedded document title and author metadata               |

### Output Reports

1. **HTML Report** (`ai_analysis_report.html`)
   - Self-contained single file — opens in any web browser, no server needed.
   - Dark-themed, card-based layout with embedded thumbnail previews.
   - **Live search** — filter by filename, font name, or creator application.
   - **Format filter** — show only PDF-compatible or only legacy files.
   - **Sorting** — by name, file size, or modification date.
   - **Font inventory** — expandable list of every unique font found across all files.
   - Summary statistics banner (total files, total size, unique fonts, warnings).

2. **CSV Report** (`ai_analysis_report.csv`)
   - Opens directly in Microsoft Excel (UTF-8 with BOM for proper encoding).
   - One row per file with all metadata columns.
   - Ideal for sorting, filtering, or importing into other tools.

---

## Prerequisites

| Requirement        | Version    | Notes                                                    |
| ------------------ | ---------- | -------------------------------------------------------- |
| **Windows**        | 10 or 11   | The `.bat` scripts are Windows-specific. The Python script itself is cross-platform. |
| **Python**         | 3.8+       | Download from [python.org](https://www.python.org/downloads/). |
| **Administrator**  | Yes        | Required for installing Python packages.                 |

> **Important**: During Python installation, you **must** check the box that says  
> **☑ Add Python to PATH**  
> If you miss this step, the setup script will not be able to find Python.

---

## Quick Start (TL;DR)

```
1. Install Python 3.8+ (check "Add to PATH")
2. Double-click  setup.bat        ← one-time setup
3. Double-click  analyze.bat      ← enter your folder path when prompted
4. Open the HTML report in your browser
```

---

## Detailed Setup Instructions

### Step 1 — Install Python

If Python is not already installed on the machine:

1. Go to **https://www.python.org/downloads/**
2. Download the latest **Python 3.x** installer for Windows (64-bit).
3. Run the installer.
4. **On the first screen**, check the box:
   - ☑ **Add Python 3.x to PATH**
5. Click **Install Now** (the default settings are fine).
6. When installation finishes, click **Close**.

**Verify** by opening a new Command Prompt or PowerShell window and running:
```
python --version
```
You should see something like `Python 3.12.4`.

### Step 2 — Run Setup

1. Open the `ai-file-analyzer` folder you received.
2. **Double-click `setup.bat`**.
3. A terminal window will open. It will:
   - Detect your Python installation.
   - Install the required `PyMuPDF` library.
   - Verify the installation.
4. You should see `Setup Complete!` at the end.
5. Press any key to close the window.

> **If you see an error**: Make sure you are running the script from an account with Administrator privileges. You can also right-click `setup.bat` → **Run as administrator**.

### Step 3 — Run the Analysis

You have **two ways** to run the analyzer:

#### Option A — Drag and Drop
1. Open File Explorer and navigate to the folder containing your `.ai` files.
2. **Drag the folder** and drop it directly onto `analyze.bat`.
3. The analysis will start automatically.

#### Option B — Manual Path Entry
1. **Double-click `analyze.bat`**.
2. When prompted, type or paste the full path to your folder of `.ai` files.
   - Example: `C:\Users\John\Documents\Legacy Illustrator Files`
3. Press **Enter**.
4. The analysis will begin.

### Step 4 — View Your Reports

When the analysis finishes, the script:
- Prints a summary in the terminal window.
- **Automatically opens** the HTML report in your default web browser.
- Saves both reports in a subfolder called `_ai_analysis_report` inside the folder you scanned.

```
Your Illustrator Folder\
├── file1.ai
├── file2.ai
├── subfolder\
│   └── file3.ai
└── _ai_analysis_report\           ← Created by the analyzer
    ├── ai_analysis_report.html    ← Interactive visual report
    └── ai_analysis_report.csv     ← Spreadsheet data
```

---

## Command-Line Usage (Advanced)

If you prefer using the command line directly, the Python script supports several options:

```
python analyze_ai_files.py <FOLDER_PATH> [OPTIONS]
```

### Arguments

| Argument                | Description                                                     |
| ----------------------- | --------------------------------------------------------------- |
| `<FOLDER_PATH>`         | **(Required)** Path to the directory containing `.ai` files.    |
| `-o`, `--output <PATH>` | Custom output directory for the reports.                        |
| `--no-recursive`        | Only scan the top-level directory (skip subdirectories).        |
| `-h`, `--help`          | Show the help message and exit.                                 |

### Examples

```powershell
# Scan a folder and all its subfolders (default)
python analyze_ai_files.py "C:\Design Files\Logos"

# Save reports to a specific location
python analyze_ai_files.py "D:\Archive\Illustrator" -o "C:\Users\Me\Desktop\Report"

# Only scan the top-level folder (no subdirectories)
python analyze_ai_files.py "C:\Projects" --no-recursive
```

---

## Understanding the HTML Report

### Summary Bar
The blue stats bar at the top shows:
- **Total Files** — number of `.ai` files found.
- **PDF-Compatible** — files saved with PDF compatibility (Illustrator 9+). These yield the richest data.
- **Legacy PostScript** — older files without PDF compatibility. Metadata is extracted from PostScript headers (no thumbnail available).
- **Total Size** — combined file size of all scanned files.
- **Unique Fonts** — total number of distinct fonts found across all files.
- **Warnings** — files where some metadata could not be extracted.

### Font Inventory
Click the **"All Unique Fonts Across Files"** dropdown to see every font used in the entire collection, sorted alphabetically and displayed in columns.

### Search and Filter
- **Search box** — type any part of a filename, font name, or creator application to filter the cards in real time.
- **Filter buttons** — click "PDF-Compatible" or "Legacy" to show only that format type.
- **Sort dropdown** — reorder cards by name, file size, or modification date.

### File Cards
Each card shows:
- A **thumbnail preview** (for PDF-compatible files) or a placeholder icon.
- The **filename** and its relative path within the scanned directory.
- All extracted metadata (format, creator, dimensions, size, dates, fonts).
- A **warning strip** (in red) if any errors occurred during analysis.

---

## Understanding the CSV Report

The CSV file can be opened in **Microsoft Excel**, **Google Sheets**, or any spreadsheet application. Columns include:

| Column              | Example Value                    |
| ------------------- | -------------------------------- |
| Filename            | `logo_v3.ai`                     |
| Relative Path       | `branding\logos\logo_v3.ai`      |
| File Size           | `2.4 MB`                         |
| File Size (Bytes)   | `2516582`                        |
| Format Type         | `PDF-Compatible AI`              |
| PDF Compatible      | `Yes`                            |
| Creator Application | `Adobe Illustrator 25.4.1`       |
| Title               | `Company Logo`                   |
| Author              | `Jane Doe`                       |
| Creation Date       | `2019-03-15`                     |
| File Modified Date  | `2021-08-22 14:30:05`            |
| Page Count          | `1`                              |
| Width (mm)          | `210.0`                          |
| Height (mm)         | `297.0`                          |
| Width (in)          | `8.27`                           |
| Height (in)         | `11.69`                          |
| Fonts               | `Helvetica; MyriadPro-Regular`   |
| Warnings            | *(empty if no issues)*           |

> **Tip**: Use Excel's filter feature on the "Fonts" column to find every file that uses a specific font — useful for font license audits.

---

## Troubleshooting

### "Python is not installed or not in PATH"
- **Cause**: Python was not installed, or the "Add to PATH" checkbox was not selected during installation.
- **Fix**: Reinstall Python from [python.org](https://www.python.org/downloads/) and make sure to check **☑ Add Python to PATH** on the first screen of the installer. Then restart your terminal / double-click `setup.bat` again.

### "Package installation failed"
- **Cause**: Insufficient permissions or network issues.
- **Fix**: Right-click `setup.bat` → **Run as administrator**. Ensure the machine has internet access.

### Some files show "No Preview" (no thumbnail)
- **Cause**: The file was saved without PDF compatibility (common in Illustrator versions prior to 9, or when "Create PDF Compatible File" was unchecked in Save options).
- **Impact**: Metadata like creator, dimensions, and fonts are still extracted from the PostScript header where possible. Only the visual thumbnail is missing.
- **Fix**: These files can only be thumbnailed by opening them in Illustrator and re-saving with "Create PDF Compatible File" checked.

### Some files show "Unreadable / Unknown" format
- **Cause**: The file may be corrupted, not a genuine Illustrator file, or in a very old format.
- **Impact**: Limited or no metadata will be available for these files. They will still appear in the report with whatever information could be extracted.

### The HTML report is very large (slow to load)
- **Cause**: Thumbnails are embedded as base64 images inside the HTML file. With hundreds of large files, the report can grow large.
- **Fix**: This is by design so the report is a single, shareable file. Try opening it in Chrome or Edge for best performance.

### Excel shows garbled characters in the CSV
- **Cause**: Excel did not detect the UTF-8 encoding.
- **Fix**: The CSV is saved with a UTF-8 BOM which modern Excel (2016+) handles automatically. For older versions: open Excel → Data → From Text/CSV → select the file → choose "UTF-8" encoding.

---

## Technical Notes

### How AI Files Work

Adobe Illustrator files come in two internal formats:

1. **PDF-Compatible (Illustrator 9+)**
   - The `.ai` file is actually a PDF container with an embedded Adobe private data stream.
   - Any PDF reader can render the visual content.
   - This analyzer uses **PyMuPDF** to open the PDF layer, render thumbnails, and extract metadata + fonts.

2. **Legacy PostScript (Illustrator 1–8)**
   - The `.ai` file is pure Adobe PostScript / EPS.
   - No PDF layer exists, so standard PDF tools cannot render them.
   - This analyzer falls back to **regex-based parsing** of the PostScript header to extract `%%Creator`, `%%BoundingBox`, `%%DocumentFonts`, and other DSC (Document Structuring Conventions) comments.

### What is PyMuPDF?

[PyMuPDF](https://pymupdf.readthedocs.io/) (imported as `fitz`) is a high-performance Python binding for the MuPDF rendering engine. It can open PDF, XPS, and several other document formats. It is used here because:
- It renders PDF pages to raster images (for thumbnails) without needing Illustrator installed.
- It parses font tables and metadata from the PDF structure.
- It is a single pip-installable package with no external system dependencies on Windows.

### Security and Privacy

- This tool runs **entirely offline**. No data is uploaded or transmitted.
- The generated HTML report is a static file with no external resource requests.
- All processing happens locally on your machine.

---

## File Listing

```
ai-file-analyzer/
├── README.md              ← This documentation
├── requirements.txt       ← Python package dependency (PyMuPDF)
├── setup.bat              ← One-time setup script (installs dependencies)
├── analyze.bat            ← Run the analyzer (drag-and-drop or prompted)
└── analyze_ai_files.py    ← Main analysis script
```

---

## License

This tool is provided as-is for internal use. No warranty is expressed or implied.
