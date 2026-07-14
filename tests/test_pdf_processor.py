import pytest
from unittest.mock import MagicMock, patch
from utils.pdf_processor import PDFProcessor

def test_pdf_processor_initialization():
    processor = PDFProcessor(chunk_size=100, chunk_overlap=10)
    assert processor.chunk_size == 100
    assert processor.chunk_overlap == 10

def test_pdf_processor_extract_and_chunk_empty_file():
    processor = PDFProcessor()
    with pytest.raises(FileNotFoundError):
        processor.extract_and_chunk("non_existent_file.pdf")

@patch("pypdf.PdfReader")
@patch("os.path.exists")
def test_pdf_processor_extract_and_chunk_mocked(mock_exists, mock_pdf_reader):
    mock_exists.return_value = True
    
    # Mocking PDF Reader and Pages
    mock_reader = MagicMock()
    
    mock_page_1 = MagicMock()
    mock_page_1.extract_text.return_value = "Acme Corp Policy. Vacation allocation is 20 days per year."
    
    mock_page_2 = MagicMock()
    mock_page_2.extract_text.return_value = "Office days. Employees work from office three days a week."
    
    mock_reader.pages = [mock_page_1, mock_page_2]
    mock_pdf_reader.return_value = mock_reader

    # Run processor with small chunks to force splits
    processor = PDFProcessor(chunk_size=25, chunk_overlap=5)
    chunks = processor.extract_and_chunk("mock_document.pdf")

    assert len(chunks) > 0
    # Check that text fields exist
    assert "text_content" in chunks[0]
    assert "metadata" in chunks[0]
    
    # Verify metadata fields
    first_chunk_meta = chunks[0]["metadata"]
    assert "page" in first_chunk_meta
    assert "chunk_within_page" in first_chunk_meta
    assert first_chunk_meta["total_pages"] == 2
    
    # Verify page assignment
    assert chunks[0]["metadata"]["page"] == 1
    assert chunks[-1]["metadata"]["page"] == 2
