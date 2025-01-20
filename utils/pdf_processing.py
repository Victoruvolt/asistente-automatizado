from PyPDF2 import PdfReader

def read_pdf(file_path):
    try:
        reader = PdfReader(file_path)
        text = " ".join([page.extract_text() for page in reader.pages])
        return text
    except Exception as e:
        return f"Error al leer el PDF: {str(e)}"
