import logging
import tempfile
import os
from typing import List, Dict, Any
import pdfplumber
import pytesseract
from PIL import Image
import io
import re

logger = logging.getLogger(__name__)

class OCRParser:
    """Parse auction lot sheets from PDF files using OCR"""
    
    def __init__(self):
        self.lot_patterns = [
            r'(?i)lot\s*#?\s*(\d+)',  # Lot # or Lot number
            r'(?i)item\s*#?\s*(\d+)',  # Item # or Item number
            r'^\s*(\d+)\s*[-.]',       # Number at start of line
        ]
        
        # Common description patterns to clean up
        self.description_patterns = [
            r'\$\d+(?:\.\d{2})?',  # Remove price estimates
            r'(?i)est\.?\s*\$?\d+',  # Remove estimates
            r'(?i)reserve\s*\$?\d+',  # Remove reserve prices
        ]
    
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extract text from PDF using pdfplumber first, fallback to OCR"""
        try:
            # Try pdfplumber first (for PDFs with text)
            with pdfplumber.open(pdf_path) as pdf:
                text = ""
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
                
                if text.strip():
                    logger.info("Successfully extracted text using pdfplumber")
                    return text
            
            # Fallback to OCR if no text found
            logger.info("No text found with pdfplumber, falling back to OCR")
            return self._ocr_pdf_pages(pdf_path)
            
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {e}")
            return ""
    
    def _ocr_pdf_pages(self, pdf_path: str) -> str:
        """Extract text using OCR on PDF pages converted to images"""
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(pdf_path)
            text = ""
            
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                pix = page.get_pixmap()
                img_data = pix.tobytes("png")
                
                # Convert to PIL Image
                image = Image.open(io.BytesIO(img_data))
                
                # Run OCR on the image
                page_text = pytesseract.image_to_string(image)
                text += page_text + "\n"
            
            doc.close()
            return text
            
        except ImportError:
            logger.error("PyMuPDF not available, cannot perform OCR on PDF")
            return ""
        except Exception as e:
            logger.error(f"Error performing OCR on PDF: {e}")
            return ""
    
    def parse_lots_from_text(self, text: str) -> List[Dict[str, Any]]:
        """Parse lot information from extracted text"""
        lots = []
        lines = text.split('\n')
        current_lot = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Try to find lot number
            lot_number = self._extract_lot_number(line)
            if lot_number:
                # Save previous lot if exists
                if current_lot:
                    lots.append(current_lot)
                
                # Start new lot
                current_lot = {
                    'lot_number': lot_number,
                    'title': self._clean_title(line),
                    'description': '',
                    'planned_max_bid': None,
                    'target_resale_price': None
                }
            elif current_lot:
                # Add to description of current lot
                cleaned_line = self._clean_description(line)
                if cleaned_line:
                    if current_lot['description']:
                        current_lot['description'] += ' ' + cleaned_line
                    else:
                        current_lot['description'] = cleaned_line
        
        # Don't forget the last lot
        if current_lot:
            lots.append(current_lot)
        
        return lots
    
    def _extract_lot_number(self, line: str) -> str:
        """Extract lot number from a line"""
        for pattern in self.lot_patterns:
            match = re.search(pattern, line)
            if match:
                return match.group(1)
        return None
    
    def _clean_title(self, line: str) -> str:
        """Clean up the title by removing lot number and excess whitespace"""
        # Remove lot number patterns
        for pattern in self.lot_patterns:
            line = re.sub(pattern, '', line, count=1)
        
        # Remove common prefixes/suffixes
        line = re.sub(r'^[-.\s]+', '', line)  # Remove leading dashes, dots, spaces
        line = re.sub(r'[-.\s]+$', '', line)  # Remove trailing dashes, dots, spaces
        
        return line.strip()
    
    def _clean_description(self, line: str) -> str:
        """Clean up description by removing prices and estimates"""
        for pattern in self.description_patterns:
            line = re.sub(pattern, '', line)
        
        return line.strip()
    
    def process_pdf_file(self, file_path: str) -> List[Dict[str, Any]]:
        """Main method to process a PDF file and return parsed lots"""
        try:
            # Extract text from PDF
            text = self.extract_text_from_pdf(file_path)
            
            if not text.strip():
                logger.warning("No text could be extracted from PDF")
                return []
            
            # Parse lots from text
            lots = self.parse_lots_from_text(text)
            
            logger.info(f"Successfully parsed {len(lots)} lots from PDF")
            return lots
            
        except Exception as e:
            logger.error(f"Error processing PDF file: {e}")
            return []

def process_uploaded_pdf(file_stream, filename: str) -> List[Dict[str, Any]]:
    """Process an uploaded PDF file and return parsed lot data"""
    parser = OCRParser()
    
    # Save uploaded file to temporary location
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
        file_stream.seek(0)
        temp_file.write(file_stream.read())
        temp_path = temp_file.name
    
    try:
        # Process the PDF
        lots = parser.process_pdf_file(temp_path)
        return lots
    finally:
        # Clean up temporary file
        try:
            os.unlink(temp_path)
        except OSError:
            pass
