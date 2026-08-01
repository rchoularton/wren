"""
Journal-specific style definitions for Word document generation.

Extracted from existing paper scripts and made reusable.
"""

from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.style import WD_STYLE_TYPE
from docx.oxml.ns import qn
from docx.oxml import OxmlElement


# Journal style configurations.
# `default` is a clean, double-spaced academic manuscript style used when a
# paper's config.json does not name a journal. The named journal presets below
# are examples — add your own target journal by copying one and adjusting.
JOURNAL_STYLES = {
    'default': {
        'font_name': 'Times New Roman',
        'body_font_size': 12,
        'line_spacing': 2.0,
        'margins': 1.0,  # inches
        'first_line_indent': 0.5,  # inches
        'styles': {
            'Title': {'font_size': 14, 'bold': True, 'space_after': 24, 'line_spacing': 1.0},
            'Author': {'font_size': 12, 'bold': False, 'space_after': 6, 'line_spacing': 1.0},
            'Affiliation': {'font_size': 10, 'bold': False, 'space_after': 12, 'line_spacing': 1.0},
            'Heading1': {'font_size': 12, 'bold': True, 'space_after': 12, 'line_spacing': 2.0},
            'Heading2': {'font_size': 12, 'bold': True, 'space_after': 12, 'line_spacing': 2.0},
            'BodyText': {'font_size': 12, 'bold': False, 'space_after': 0, 'line_spacing': 2.0, 'first_line_indent': 0.5},
            'BodyTextNoIndent': {'font_size': 12, 'bold': False, 'space_after': 0, 'line_spacing': 2.0},
            'Abstract': {'font_size': 12, 'bold': False, 'space_after': 12, 'line_spacing': 2.0},
            'Reference': {'font_size': 10, 'bold': False, 'space_after': 6, 'line_spacing': 1.5},
            'TableText': {'font_size': 10, 'bold': False, 'space_after': 6, 'line_spacing': 1.0},
            'FigureLegend': {'font_size': 10, 'bold': False, 'space_after': 12, 'line_spacing': 1.5},
        }
    },
    'nature_food': {
        'font_name': 'Times New Roman',
        'body_font_size': 12,
        'line_spacing': 2.0,
        'margins': 1.0,  # inches
        'first_line_indent': 0.5,  # inches
        'styles': {
            'Title': {'font_size': 14, 'bold': True, 'space_after': 24, 'line_spacing': 1.0},
            'Author': {'font_size': 12, 'bold': False, 'space_after': 6, 'line_spacing': 1.0},
            'Affiliation': {'font_size': 10, 'bold': False, 'space_after': 12, 'line_spacing': 1.0},
            'Heading1': {'font_size': 12, 'bold': True, 'space_after': 12, 'line_spacing': 2.0},
            'Heading2': {'font_size': 12, 'bold': True, 'space_after': 12, 'line_spacing': 2.0},
            'BodyText': {'font_size': 12, 'bold': False, 'space_after': 0, 'line_spacing': 2.0, 'first_line_indent': 0.5},
            'BodyTextNoIndent': {'font_size': 12, 'bold': False, 'space_after': 0, 'line_spacing': 2.0},
            'Abstract': {'font_size': 12, 'bold': False, 'space_after': 12, 'line_spacing': 2.0},
            'Reference': {'font_size': 10, 'bold': False, 'space_after': 6, 'line_spacing': 1.5},
            'TableText': {'font_size': 10, 'bold': False, 'space_after': 6, 'line_spacing': 1.0},
            'FigureLegend': {'font_size': 10, 'bold': False, 'space_after': 12, 'line_spacing': 1.5},
        }
    },
    'nature_climate_change': {
        'font_name': 'Times New Roman',
        'body_font_size': 12,
        'line_spacing': 2.0,
        'margins': 1.0,
        'first_line_indent': 0.5,
        'styles': {
            'Title': {'font_size': 14, 'bold': True, 'space_after': 24, 'line_spacing': 1.0},
            'Author': {'font_size': 12, 'bold': False, 'space_after': 6, 'line_spacing': 1.0},
            'Affiliation': {'font_size': 10, 'bold': False, 'space_after': 12, 'line_spacing': 1.0},
            'Heading1': {'font_size': 12, 'bold': True, 'space_after': 12, 'line_spacing': 2.0},
            'Heading2': {'font_size': 12, 'bold': True, 'space_after': 12, 'line_spacing': 2.0},
            'BodyText': {'font_size': 12, 'bold': False, 'space_after': 0, 'line_spacing': 2.0, 'first_line_indent': 0.5},
            'BodyTextNoIndent': {'font_size': 12, 'bold': False, 'space_after': 0, 'line_spacing': 2.0},
            'Abstract': {'font_size': 12, 'bold': False, 'space_after': 12, 'line_spacing': 2.0},
            'Reference': {'font_size': 10, 'bold': False, 'space_after': 6, 'line_spacing': 1.5},
            'TableText': {'font_size': 10, 'bold': False, 'space_after': 6, 'line_spacing': 1.0},
            'FigureLegend': {'font_size': 10, 'bold': False, 'space_after': 12, 'line_spacing': 1.5},
        }
    },
    'world_development': {
        'font_name': 'Times New Roman',
        'body_font_size': 12,
        'line_spacing': 2.0,
        'margins': 1.0,
        'first_line_indent': 0.0,  # Elsevier typically no indent
        'styles': {
            'Title': {'font_size': 16, 'bold': True, 'space_after': 24, 'line_spacing': 1.0},
            'Author': {'font_size': 12, 'bold': False, 'space_after': 6, 'line_spacing': 1.0},
            'Affiliation': {'font_size': 10, 'bold': False, 'space_after': 12, 'line_spacing': 1.0},
            'Heading1': {'font_size': 14, 'bold': True, 'space_after': 12, 'line_spacing': 2.0},
            'Heading2': {'font_size': 12, 'bold': True, 'space_after': 12, 'line_spacing': 2.0},
            'BodyText': {'font_size': 12, 'bold': False, 'space_after': 0, 'line_spacing': 2.0},
            'BodyTextNoIndent': {'font_size': 12, 'bold': False, 'space_after': 0, 'line_spacing': 2.0},
            'Abstract': {'font_size': 12, 'bold': False, 'space_after': 12, 'line_spacing': 2.0},
            'Reference': {'font_size': 10, 'bold': False, 'space_after': 6, 'line_spacing': 1.5},
            'TableText': {'font_size': 10, 'bold': False, 'space_after': 6, 'line_spacing': 1.0},
            'FigureLegend': {'font_size': 10, 'bold': False, 'space_after': 12, 'line_spacing': 1.5},
        }
    }
}


def set_document_margins(doc: Document, margin_inches: float = 1.0):
    """Set document margins to specified inches on all sides."""
    for section in doc.sections:
        section.top_margin = Inches(margin_inches)
        section.bottom_margin = Inches(margin_inches)
        section.left_margin = Inches(margin_inches)
        section.right_margin = Inches(margin_inches)


def add_page_numbers(doc: Document):
    """Add centered page numbers to document footer."""
    for section in doc.sections:
        footer = section.footer
        footer.is_linked_to_previous = False
        paragraph = footer.paragraphs[0]
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER

        # Add page number field
        run = paragraph.add_run()
        fldChar1 = OxmlElement('w:fldChar')
        fldChar1.set(qn('w:fldCharType'), 'begin')

        instrText = OxmlElement('w:instrText')
        instrText.set(qn('xml:space'), 'preserve')
        instrText.text = "PAGE"

        fldChar2 = OxmlElement('w:fldChar')
        fldChar2.set(qn('w:fldCharType'), 'end')

        run._r.append(fldChar1)
        run._r.append(instrText)
        run._r.append(fldChar2)


def create_style(doc: Document, name: str, font_name: str = 'Times New Roman',
                 font_size: int = 12, bold: bool = False, space_after: int = 12,
                 line_spacing: float = 2.0, first_line_indent: float = None):
    """Create or modify a paragraph style."""
    try:
        style = doc.styles[name]
    except KeyError:
        style = doc.styles.add_style(name, WD_STYLE_TYPE.PARAGRAPH)

    style.font.name = font_name
    style.font.size = Pt(font_size)
    style.font.bold = bold
    style.paragraph_format.space_after = Pt(space_after)
    style.paragraph_format.line_spacing = line_spacing

    if first_line_indent:
        style.paragraph_format.first_line_indent = Inches(first_line_indent)

    # Set font for East Asian characters too
    rPr = style._element.get_or_add_rPr()
    rFonts = rPr.find(qn('w:rFonts'))
    if rFonts is not None:
        rFonts.set(qn('w:eastAsia'), font_name)

    return style


def apply_journal_styles(doc: Document, journal: str):
    """Apply all styles for a specific journal to a document.

    Falls back to the 'default' academic style for any journal without a
    dedicated preset, so arbitrary journal names in config.json still build.
    """
    if journal not in JOURNAL_STYLES:
        print(f"Note: no style preset for '{journal}' — using 'default'. "
              f"Presets: {list(JOURNAL_STYLES.keys())}")
        journal = 'default'

    config = JOURNAL_STYLES[journal]

    # Set margins
    set_document_margins(doc, config['margins'])

    # Create all styles
    for style_name, style_config in config['styles'].items():
        create_style(
            doc,
            style_name,
            font_name=config['font_name'],
            font_size=style_config['font_size'],
            bold=style_config['bold'],
            space_after=style_config['space_after'],
            line_spacing=style_config['line_spacing'],
            first_line_indent=style_config.get('first_line_indent')
        )

    # Add page numbers
    add_page_numbers(doc)

    return doc
