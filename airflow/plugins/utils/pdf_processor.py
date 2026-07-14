import os
import logging
from typing import List, Dict, Any
from langchain_text_splitters import RecursiveCharacterTextSplitter
import pypdf

logger = logging.getLogger(__name__)

class PDFProcessor:
    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )

    def extract_and_chunk(self, pdf_path: str) -> List[Dict[str, Any]]:
        """
        Extracts text from a PDF page-by-page, splits it into chunks, 
        and returns a list of dictionaries containing chunk text and page metadata.
        """
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF file not found at {pdf_path}")

        chunks = []
        try:
            reader = pypdf.PdfReader(pdf_path)
            total_pages = len(reader.pages)
            logger.info(f"Processing PDF: {pdf_path} (Total Pages: {total_pages})")

            for page_num in range(total_pages):
                page = reader.pages[page_num]
                text = page.extract_text()
                if not text or not text.strip():
                    logger.warning(f"Skipping page {page_num + 1} of {pdf_path}: No text found.")
                    continue

                page_chunks = self.splitter.split_text(text)
                for idx, chunk in enumerate(page_chunks):
                    chunks.append({
                        "text_content": chunk,
                        "metadata": {
                            "page": page_num + 1,
                            "chunk_within_page": idx,
                            "total_pages": total_pages
                        }
                    })
            
            logger.info(f"Successfully chunked {pdf_path} into {len(chunks)} chunks.")
        except Exception as e:
            logger.error(f"Error processing PDF {pdf_path}: {e}")
            raise e

        return chunks
