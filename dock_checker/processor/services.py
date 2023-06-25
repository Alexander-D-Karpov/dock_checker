from typing import Tuple
from io import BytesIO
import re
import fitz
from django.core.cache import cache
from rest_framework.exceptions import NotFound


def get_task_status(pk: str) -> dict:
    if cache.get(f"{pk}-processed") is None:
        raise NotFound("given task does not exist")
    created = cache.get_or_set(f"{pk}-processed", 0)
    total = cache.get_or_set(f"{pk}-total", 0)
    features_loaded = cache.get_or_set(f"{pk}-features_loaded", False)
    error = cache.get_or_set(f"{pk}-error", False)
    error_description = cache.get_or_set(f"{pk}-error_description", "")
    return {
        "processed": created,
        "total": total,
        "features_loaded": features_loaded,
        "error": error,
        "error_description": error_description,
    }


def extract_info(input_file: str):
    """
    Extracts file info
    """
    # Open the PDF
    pdfDoc = fitz.open(input_file)
    output = {
        "File": input_file,
        "Encrypted": ("True" if pdfDoc.isEncrypted else "False"),
    }
    # If PDF is encrypted the file metadata cannot be extracted
    if not pdfDoc.isEncrypted:
        for key, value in pdfDoc.metadata.items():
            output[key] = value
    # To Display File Info
    print("## File Information ##################################################")
    print("\n".join("{}:{}".format(i, j) for i, j in output.items()))
    print("######################################################################")
    return True, output


def search_for_text(lines, search_str):
    """
    Search for the search string within the document lines
    """
    if search_str in lines:
        return search_str


def redact_matching_data(page, matched_values):
    """
    Redacts matching values
    """
    matches_found = 0
    # Loop throughout matching values
    for val in matched_values:
        matches_found += 1
        matching_val_area = page.search_for(val)
        # Redact matching values
        [
            page.addRedactAnnot(area, text=" ", fill=(0, 0, 0))
            for area in matching_val_area
        ]
    # Apply the redaction
    page.apply_redactions()
    return matches_found


def frame_matching_data(page, matched_values):
    """
    frames matching values
    """
    matches_found = 0
    # Loop throughout matching values
    for val in matched_values:
        matches_found += 1
        matching_val_area = page.search_for(val)
        for area in matching_val_area:
            if isinstance(area, fitz.fitz.Rect):
                # Draw a rectangle around matched values
                annot = page.addRectAnnot(area)
                # , fill = fitz.utils.getColor('black')
                annot.setColors(stroke=fitz.utils.getColor("red"))
                # If you want to remove matched data
                # page.addFreetextAnnot(area, ' ')
                annot.update()
    return matches_found


def highlight_matching_data(page, matched_values, type):
    """
    Highlight matching values
    """
    matches_found = 0
    # Loop throughout matching values
    for val in matched_values:
        matches_found += 1
        matching_val_area = page.search_for(val)
        # print("matching_val_area",matching_val_area)
        highlight = None
        if type == "Highlight":
            highlight = page.add_highlight_annot(matching_val_area)
        elif type == "Squiggly":
            highlight = page.add_squiggly_annot(matching_val_area)
        elif type == "Underline":
            highlight = page.add_underline_annot(matching_val_area)
        elif type == "Strikeout":
            highlight = page.add_strikeout_annot(matching_val_area)
        else:
            highlight = page.add_highlight_annot(matching_val_area)
        # To change the highlight colar
        # highlight.setColors({"stroke":(0,0,1),"fill":(0.75,0.8,0.95) })
        # highlight.setColors(stroke = fitz.utils.getColor('white'), fill = fitz.utils.getColor('red'))
        # highlight.setColors(colors= fitz.utils.getColor('red'))
        highlight.update()
    return matches_found


def process_data(
    input_file: str,
    search_str: str,
    pages: Tuple = None,
    action: str = "Highlight",
):
    """
    Process the pages of the PDF File
    """
    # Open the PDF
    pdfDoc = fitz.open(input_file)
    # Save the generated PDF to memory buffer
    output_buffer = BytesIO()
    total_matches = 0
    # Iterate through pages
    for pg in range(len(pdfDoc)):
        # If required for specific pages
        if pages:
            if str(pg) not in pages:
                continue
        # Select the page
        page = pdfDoc[pg]
        # Get Matching Data
        # Split page by lines
        page_lines = page.get_text("text")
        matched_values = search_for_text(page_lines, search_str)
        if matched_values:
            if action == "Redact":
                matches_found = redact_matching_data(page, matched_values)
            elif action == "Frame":
                matches_found = frame_matching_data(page, matched_values)
            elif action in ("Highlight", "Squiggly", "Underline", "Strikeout"):
                matches_found = highlight_matching_data(page, matched_values, action)
            else:
                matches_found = highlight_matching_data(
                    page, matched_values, "Highlight"
                )
            total_matches += matches_found
    print(
        f"{total_matches} Match(es) Found of Search String {search_str} In Input File: {input_file}"
    )
    # Save to output
    pdfDoc.save(output_buffer)
    pdfDoc.close()
    # Save the output buffer to the output file
    with open(input_file, mode="wb") as f:
        f.write(output_buffer.getbuffer())

