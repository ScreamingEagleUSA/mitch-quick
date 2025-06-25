"""
Unit tests for OCR parser functionality
"""
import pytest
import tempfile
import os
from unittest.mock import Mock, patch, mock_open
from utils.ocr_parser import OCRParser, process_uploaded_pdf


class TestOCRParser:
    """Test OCR parser class"""

    def setUp(self):
        """Set up test fixtures"""
        self.parser = OCRParser()

    def test_init(self):
        """Test OCR parser initialization"""
        parser = OCRParser()
        assert parser.lot_patterns is not None
        assert len(parser.lot_patterns) > 0
        assert parser.description_patterns is not None

    def test_extract_lot_number_basic(self):
        """Test basic lot number extraction"""
        parser = OCRParser()
        
        test_cases = [
            ("Lot #1", "1"),
            ("LOT 25", "25"),
            ("Item #123", "123"),
            ("lot 45", "45"),
            ("ITEM 67", "67"),
            ("1. Antique Chair", "1"),
            ("25 - Victorian Table", "25"),
        ]
        
        for text, expected in test_cases:
            result = parser._extract_lot_number(text)
            assert result == expected, f"Failed for text: '{text}'"

    def test_extract_lot_number_no_match(self):
        """Test lot number extraction with no matches"""
        parser = OCRParser()
        
        test_cases = [
            "No lot number here",
            "Just some text",
            "Price: $100",
            "",
        ]
        
        for text in test_cases:
            result = parser._extract_lot_number(text)
            assert result is None, f"Should not match: '{text}'"

    def test_clean_title_basic(self):
        """Test title cleaning functionality"""
        parser = OCRParser()
        
        test_cases = [
            ("Lot #1 - Antique Chair", "Antique Chair"),
            ("LOT 25 Victorian Table", "Victorian Table"),
            ("Item #123: Beautiful Vase", "Beautiful Vase"),
            ("45. Wooden Cabinet", "Wooden Cabinet"),
            ("  Lot 67   Vintage Clock  ", "Vintage Clock"),
        ]
        
        for input_text, expected in test_cases:
            result = parser._clean_title(input_text)
            assert result == expected, f"Failed for input: '{input_text}'"

    def test_clean_description_basic(self):
        """Test description cleaning functionality"""
        parser = OCRParser()
        
        test_cases = [
            ("Beautiful antique chair est. $500", "Beautiful antique chair"),
            ("Vintage table Reserve $200", "Vintage table"),
            ("Nice vase Est $100-150", "Nice vase"),
            ("Clean description", "Clean description"),
        ]
        
        for input_text, expected in test_cases:
            result = parser._clean_description(input_text)
            assert result.strip() == expected, f"Failed for input: '{input_text}'"

    def test_parse_lots_from_text_basic(self):
        """Test parsing lots from basic text"""
        parser = OCRParser()
        
        test_text = """
        Lot 1 - Antique Chair
        Beautiful wooden chair from 1800s
        
        Lot 2 - Victorian Table
        Mahogany dining table
        
        Item 3: Vintage Clock
        Working grandfather clock
        """
        
        lots = parser.parse_lots_from_text(test_text)
        
        assert len(lots) == 3
        
        assert lots[0]['lot_number'] == '1'
        assert 'Antique Chair' in lots[0]['title']
        assert 'Beautiful wooden chair' in lots[0]['description']
        
        assert lots[1]['lot_number'] == '2'
        assert 'Victorian Table' in lots[1]['title']
        
        assert lots[2]['lot_number'] == '3'
        assert 'Vintage Clock' in lots[2]['title']

    def test_parse_lots_from_text_no_lots(self):
        """Test parsing with no recognizable lots"""
        parser = OCRParser()
        
        test_text = """
        This is just some random text
        with no lot numbers or items
        Nothing to parse here
        """
        
        lots = parser.parse_lots_from_text(test_text)
        assert len(lots) == 0

    def test_parse_lots_from_text_empty(self):
        """Test parsing empty or whitespace text"""
        parser = OCRParser()
        
        for text in ["", "   ", "\n\n", None]:
            if text is not None:
                lots = parser.parse_lots_from_text(text)
                assert len(lots) == 0

    def test_parse_lots_complex_format(self):
        """Test parsing lots with complex formatting"""
        parser = OCRParser()
        
        test_text = """
        1. ANTIQUE FURNITURE - Lot includes Victorian chair 
           circa 1890, excellent condition, est. $300-500
           
        2. COLLECTIBLES & POTTERY
           Various items including vase, plates
           Reserve: $150
           
        25A. Mixed lot tools
             Hand tools and power tools
        """
        
        lots = parser.parse_lots_from_text(test_text)
        
        assert len(lots) >= 2  # Should find at least lots 1 and 2
        
        # Check first lot
        lot1 = next((lot for lot in lots if lot['lot_number'] == '1'), None)
        assert lot1 is not None
        assert 'ANTIQUE FURNITURE' in lot1['title']
        assert 'Victorian chair' in lot1['description']

    @patch('pdfplumber.open')
    def test_extract_text_from_pdf_with_text(self, mock_pdfplumber):
        """Test PDF text extraction when PDF contains text"""
        parser = OCRParser()
        
        # Mock PDF with extractable text
        mock_page = Mock()
        mock_page.extract_text.return_value = "Lot 1 - Test Item"
        
        mock_pdf = Mock()
        mock_pdf.pages = [mock_page]
        mock_pdf.__enter__ = Mock(return_value=mock_pdf)
        mock_pdf.__exit__ = Mock(return_value=None)
        
        mock_pdfplumber.return_value = mock_pdf
        
        result = parser.extract_text_from_pdf("test.pdf")
        assert result == "Lot 1 - Test Item\n"
        mock_pdfplumber.assert_called_once_with("test.pdf")

    @patch('pdfplumber.open')
    def test_extract_text_from_pdf_no_text(self, mock_pdfplumber):
        """Test PDF text extraction when PDF has no extractable text"""
        parser = OCRParser()
        
        # Mock PDF with no extractable text
        mock_page = Mock()
        mock_page.extract_text.return_value = None
        
        mock_pdf = Mock()
        mock_pdf.pages = [mock_page]
        mock_pdf.__enter__ = Mock(return_value=mock_pdf)
        mock_pdf.__exit__ = Mock(return_value=None)
        
        mock_pdfplumber.return_value = mock_pdf
        
        with patch.object(parser, '_ocr_pdf_pages', return_value="OCR result"):
            result = parser.extract_text_from_pdf("test.pdf")
            assert result == "OCR result"

    def test_extract_text_from_pdf_file_not_found(self):
        """Test PDF text extraction with non-existent file"""
        parser = OCRParser()
        
        result = parser.extract_text_from_pdf("nonexistent.pdf")
        assert result == ""

    @patch('fitz.open')
    @patch('pytesseract.image_to_string')
    def test_ocr_pdf_pages(self, mock_tesseract, mock_fitz):
        """Test OCR processing of PDF pages"""
        parser = OCRParser()
        
        # Mock PyMuPDF document
        mock_page = Mock()
        mock_pixmap = Mock()
        mock_pixmap.tobytes.return_value = b"fake_image_data"
        mock_page.get_pixmap.return_value = mock_pixmap
        
        mock_doc = Mock()
        mock_doc.__len__ = Mock(return_value=1)
        mock_doc.load_page.return_value = mock_page
        mock_doc.close = Mock()
        
        mock_fitz.return_value = mock_doc
        mock_tesseract.return_value = "OCR extracted text"
        
        with patch('PIL.Image.open'):
            result = parser._ocr_pdf_pages("test.pdf")
            assert "OCR extracted text" in result

    @patch('fitz.open', side_effect=ImportError())
    def test_ocr_pdf_pages_no_pymupdf(self, mock_fitz):
        """Test OCR processing when PyMuPDF is not available"""
        parser = OCRParser()
        
        result = parser._ocr_pdf_pages("test.pdf")
        assert result == ""

    def test_process_pdf_file_integration(self):
        """Test complete PDF processing workflow"""
        parser = OCRParser()
        
        with patch.object(parser, 'extract_text_from_pdf') as mock_extract:
            mock_extract.return_value = """
            Lot 1 - Antique Chair
            Beautiful wooden chair
            
            Lot 2 - Victorian Table
            Mahogany dining table
            """
            
            result = parser.process_pdf_file("test.pdf")
            
            assert len(result) == 2
            assert result[0]['lot_number'] == '1'
            assert result[1]['lot_number'] == '2'

    def test_process_pdf_file_no_text(self):
        """Test PDF processing when no text is extracted"""
        parser = OCRParser()
        
        with patch.object(parser, 'extract_text_from_pdf', return_value=""):
            result = parser.process_pdf_file("test.pdf")
            assert len(result) == 0

    def test_process_pdf_file_exception(self):
        """Test PDF processing with exception"""
        parser = OCRParser()
        
        with patch.object(parser, 'extract_text_from_pdf', side_effect=Exception("Test error")):
            result = parser.process_pdf_file("test.pdf")
            assert len(result) == 0


class TestProcessUploadedPDF:
    """Test the process_uploaded_pdf function"""

    def test_process_uploaded_pdf_basic(self):
        """Test processing uploaded PDF with mock file stream"""
        mock_file_stream = Mock()
        mock_file_stream.seek = Mock()
        mock_file_stream.read.return_value = b"fake pdf content"
        
        with patch('tempfile.NamedTemporaryFile') as mock_temp_file:
            mock_temp_file.return_value.__enter__.return_value.name = "temp.pdf"
            
            with patch('utils.ocr_parser.OCRParser') as mock_parser_class:
                mock_parser = Mock()
                mock_parser.process_pdf_file.return_value = [
                    {'lot_number': '1', 'title': 'Test Item', 'description': 'Test description'}
                ]
                mock_parser_class.return_value = mock_parser
                
                with patch('os.unlink'):
                    result = process_uploaded_pdf(mock_file_stream, "test.pdf")
                    
                    assert len(result) == 1
                    assert result[0]['lot_number'] == '1'
                    mock_parser.process_pdf_file.assert_called_once()

    def test_process_uploaded_pdf_exception(self):
        """Test processing uploaded PDF with exception"""
        mock_file_stream = Mock()
        mock_file_stream.seek.side_effect = Exception("Test error")
        
        result = process_uploaded_pdf(mock_file_stream, "test.pdf")
        assert result == []

    def test_process_uploaded_pdf_cleanup(self):
        """Test that temporary files are cleaned up"""
        mock_file_stream = Mock()
        mock_file_stream.seek = Mock()
        mock_file_stream.read.return_value = b"fake pdf content"
        
        with patch('tempfile.NamedTemporaryFile') as mock_temp_file:
            temp_file_mock = Mock()
            temp_file_mock.name = "temp.pdf"
            mock_temp_file.return_value.__enter__.return_value = temp_file_mock
            
            with patch('utils.ocr_parser.OCRParser'):
                with patch('os.unlink') as mock_unlink:
                    process_uploaded_pdf(mock_file_stream, "test.pdf")
                    mock_unlink.assert_called_once_with("temp.pdf")


class TestOCRParserRobustness:
    """Test OCR parser robustness and edge cases"""

    def test_unicode_handling(self):
        """Test handling of unicode characters"""
        parser = OCRParser()
        
        test_text = """
        Lot 1 - Café Table
        Beautiful table with café style
        
        Lot 2 - Naïve Art Piece
        Unique naïve art from artist
        """
        
        lots = parser.parse_lots_from_text(test_text)
        assert len(lots) == 2
        assert 'Café' in lots[0]['title']

    def test_special_characters(self):
        """Test handling of special characters"""
        parser = OCRParser()
        
        test_text = """
        Lot #1 - "Antique" Chair & Table
        Beautiful furniture set w/ intricate details
        
        Lot 2: Vase (circa 1900's)
        Pottery vase from early 1900's
        """
        
        lots = parser.parse_lots_from_text(test_text)
        assert len(lots) == 2

    def test_malformed_lot_numbers(self):
        """Test handling of malformed lot numbers"""
        parser = OCRParser()
        
        test_text = """
        Lot ABC - Should not match
        Regular text here
        
        Lot 123X - Might match the number part
        Some description
        """
        
        lots = parser.parse_lots_from_text(test_text)
        # Should be robust enough to handle or ignore malformed entries

    def test_very_long_descriptions(self):
        """Test handling of very long descriptions"""
        parser = OCRParser()
        
        long_description = "Very long description " * 100
        test_text = f"""
        Lot 1 - Test Item
        {long_description}
        
        Lot 2 - Another Item
        Short description
        """
        
        lots = parser.parse_lots_from_text(test_text)
        assert len(lots) == 2
        assert len(lots[0]['description']) > 1000

    def test_mixed_formatting(self):
        """Test handling of mixed formatting styles"""
        parser = OCRParser()
        
        test_text = """
        LOT #001 - First Item
        Description here
        
        lot 2: Second Item
        Another description
        
        Item #3 Third Item
        Yet another description
        
        4. Fourth Item
        Final description
        """
        
        lots = parser.parse_lots_from_text(test_text)
        assert len(lots) >= 3  # Should catch most of these

    def test_empty_lots(self):
        """Test handling of lots with missing information"""
        parser = OCRParser()
        
        test_text = """
        Lot 1 -
        
        Lot 2 - Item with no description
        
        Lot 3
        Has description but no title separator
        """
        
        lots = parser.parse_lots_from_text(test_text)
        # Should handle gracefully without crashing
        assert isinstance(lots, list)

    def test_performance_large_text(self):
        """Test performance with large text input"""
        parser = OCRParser()
        
        # Create large text with many lots
        large_text = ""
        for i in range(1000):
            large_text += f"Lot {i} - Item {i}\nDescription for item {i}\n\n"
        
        import time
        start_time = time.time()
        lots = parser.parse_lots_from_text(large_text)
        end_time = time.time()
        
        # Should complete in reasonable time (adjust threshold as needed)
        assert end_time - start_time < 5.0  # 5 seconds max
        assert len(lots) == 1000


if __name__ == '__main__':
    pytest.main([__file__])
