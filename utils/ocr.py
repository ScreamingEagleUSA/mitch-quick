import pdfplumber
import pytesseract
from PIL import Image
import io
import re
import logging

logger = logging.getLogger(__name__)

def process_pdf_upload(pdf_path):
    """
    Process uploaded PDF and extract auction lot information using OCR
    Returns list of dictionaries with lot information
    """
    extracted_items = []
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                logger.debug(f"Processing page {page_num + 1}")
                
                # First try to extract text directly
                text = page.extract_text()
                if text:
                    items = parse_text_for_lots(text)
                    extracted_items.extend(items)
                else:
                    # Fallback to OCR if no text found
                    logger.debug("No text found, using OCR")
                    img = page.within_bbox((0, 0, page.width, page.height)).to_image()
                    pil_img = img.original
                    
                    # Use pytesseract to extract text
                    ocr_text = pytesseract.image_to_string(pil_img)
                    items = parse_text_for_lots(ocr_text)
                    extracted_items.extend(items)
    
    except Exception as e:
        logger.error(f"Error processing PDF: {str(e)}")
        raise
    
    return extracted_items

def parse_text_for_lots(text):
    """
    Parse extracted text to identify auction lots
    This is a basic implementation - can be enhanced based on specific auction house formats
    """
    items = []
    
    # Common patterns for auction lots
    lot_patterns = [
        r'(?i)lot\s+(\d+)[:\.\s]+(.+?)(?=lot\s+\d+|$)',  # "Lot 123: Description"
        r'(\d+)\.\s+(.+?)(?=\d+\.|$)',  # "123. Description"
        r'(\d+)\s+(.+?)(?=\n\d+\s+|$)',  # "123 Description"
    ]
    
    for pattern in lot_patterns:
        matches = re.finditer(pattern, text, re.MULTILINE | re.DOTALL)
        
        for match in matches:
            lot_number = match.group(1).strip()
            description = match.group(2).strip()
            
            # Clean up description
            description = re.sub(r'\s+', ' ', description)  # Normalize whitespace
            description = description[:200]  # Limit length
            
            # Extract title (first few words)
            title_words = description.split()[:8]  # First 8 words as title
            title = ' '.join(title_words)
            
            if len(title) > 5:  # Only add if we have a reasonable title
                items.append({
                    'lot_number': lot_number,
                    'title': title,
                    'description': description
                })
    
    # Remove duplicates based on lot number
    seen_lots = set()
    unique_items = []
    for item in items:
        if item['lot_number'] not in seen_lots:
            seen_lots.add(item['lot_number'])
            unique_items.append(item)
    
    return unique_items

def extract_price_estimates(text):
    """
    Extract price estimates from auction text
    Returns tuple of (low_estimate, high_estimate)
    """
    # Common patterns for price estimates
    price_patterns = [
        r'\$(\d+(?:,\d{3})*)\s*-\s*\$?(\d+(?:,\d{3})*)',  # $100 - $200 or $100 - 200
        r'Est\.?\s*\$?(\d+(?:,\d{3})*)\s*-\s*\$?(\d+(?:,\d{3})*)',  # Est. $100-200
        r'Estimate:?\s*\$?(\d+(?:,\d{3})*)\s*-\s*\$?(\d+(?:,\d{3})*)',  # Estimate: $100-200
    ]
    
    for pattern in price_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            low = float(match.group(1).replace(',', ''))
            high = float(match.group(2).replace(',', ''))
            return (low, high)
    
    return (None, None)
