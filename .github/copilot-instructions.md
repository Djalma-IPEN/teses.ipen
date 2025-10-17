# IPEN Academic Document Generator - AI Agent Instructions

This guide helps AI agents understand and work with the IPEN Academic Document Generator, a Flask-based web application for generating academic documents.

## Project Overview

This application generates standardized academic documents (theses and dissertations) for IPEN (Instituto de Pesquisas Energéticas e Nucleares). It converts web form data into properly formatted PDF documents following institutional standards.

### Key Components

- **Flask Backend** (`app.py`): Handles form submission, PDF generation, and document processing
- **HTML Form** (`templates/formulario.html`): Rich web interface with dynamic fields and formatting options
- **PDF Generation**: Uses ReportLab for creating standardized academic documents
- **Static Resources** (`static/`): Contains images and assets for PDF generation

## Core Patterns

### Document Types and Validation

Each document type has specific required fields defined in `CAMPOS_POR_DOCUMENTO`:
```python
CAMPOS_POR_DOCUMENTO = {
    "capa": ["nivel", "area", "nome_completo", "sobrenome", "titulo", "ano", "orientador_completo"],
    # ... other document types
}
```

### HTML Cleaning and Processing

Always use `clean_html_for_reportlab()` when processing HTML content for PDF generation. It handles:
- Removal of unsupported HTML attributes
- Whitespace normalization
- Special handling of `<p>`, `<div>`, and `<br>` tags

### Form Data Processing

Form fields may contain rich text with formatting. Key considerations:
- Use BeautifulSoup for HTML parsing
- Preserve specific formatting tags (font, color, etc.)
- Handle multilingual content (Portuguese/English)

## Development Workflow

1. **Environment Setup**:
   ```bash
   python -m venv venv
   . venv/Scripts/activate  # Windows
   pip install -r requirements.txt
   ```

2. **Running the Application**:
   ```bash
   flask run --debug
   ```

3. **Testing Document Generation**:
   - Access http://localhost:5000
   - Fill the form with test data
   - Check generated PDFs for formatting consistency

## Integration Points

- **ReportLab Integration**: Custom styling and formatting through `ParagraphStyle` definitions
- **Form-to-PDF Pipeline**: Form data → HTML cleaning → PDF generation with proper academic formatting
- **Repository Integration**: Generated citations include IPEN repository links

## Best Practices

1. Always validate form data against `CAMPOS_POR_DOCUMENTO` before processing
2. Use `static_file_path()` for accessing static resources
3. Handle HTML content through `clean_html_for_reportlab()` before PDF generation
4. Follow IPEN's citation format rules when modifying citation-related code