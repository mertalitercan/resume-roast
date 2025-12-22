import PyPDF2
from io import BytesIO
from typing import Dict

class PDFService:
    @staticmethod
    def extract_text(pdf_bytes: bytes) -> Dict[str, any]:
        """
        Extract text from PDF bytes.
        Returns: {
            'text': str,
            'page_count': int,
            'word_count': int
        }
        """
        try:
            pdf_file = BytesIO(pdf_bytes)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            
            # Extract all text
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            
            # Clean text
            text = text.strip()
            word_count = len(text.split())
            
            return {
                'text': text,
                'page_count': len(pdf_reader.pages),
                'word_count': word_count
            }
        except Exception as e:
            raise Exception(f"PDF extraction failed: {str(e)}")
