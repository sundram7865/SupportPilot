import io
from typing import Optional
import logging

import PyPDF2
import docx
import markdown
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class ContentExtractor:
    """Extract text content from various file formats"""
    
    @staticmethod
    async def extract_text(file_content: bytes, file_type: str, file_name: str) -> Optional[str]:
        """
        Extract text content based on file type
        """
        extractors = {
            'pdf': ContentExtractor._extract_from_pdf,
            'txt': ContentExtractor._extract_from_text,
            'md': ContentExtractor._extract_from_markdown,
            'csv': ContentExtractor._extract_from_csv,
            'json': ContentExtractor._extract_from_json,
            'xml': ContentExtractor._extract_from_xml,
            'docx': ContentExtractor._extract_from_docx,
        }
        
        file_extension = file_name.rsplit('.', 1)[-1].lower() if '.' in file_name else file_type
        
        extractor = extractors.get(file_extension)
        if not extractor:
            logger.warning(f"No extractor for file type: {file_extension}")
            return None
        
        try:
            return extractor(file_content)
        except Exception as e:
            logger.error(f"Failed to extract content from {file_name}: {str(e)}")
            return None
    
    @staticmethod
    def _extract_from_pdf(content: bytes) -> str:
        """Extract text from PDF"""
        pdf_file = io.BytesIO(content)
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        
        text_parts = []
        for page in pdf_reader.pages:
            text = page.extract_text()
            if text:
                text_parts.append(text)
        
        return "\n\n".join(text_parts)
    
    @staticmethod
    def _extract_from_text(content: bytes) -> str:
        """Extract text from plain text files"""
        return content.decode('utf-8', errors='ignore')
    
    @staticmethod
    def _extract_from_markdown(content: bytes) -> str:
        """Extract text from markdown, converting to plain text"""
        md_content = content.decode('utf-8', errors='ignore')
        html = markdown.markdown(md_content)
        soup = BeautifulSoup(html, 'html.parser')
        return soup.get_text()
    
    @staticmethod
    def _extract_from_csv(content: bytes) -> str:
        """Extract text from CSV"""
        return content.decode('utf-8', errors='ignore')
    
    @staticmethod
    def _extract_from_json(content: bytes) -> str:
        """Extract text from JSON"""
        import json
        data = json.loads(content.decode('utf-8', errors='ignore'))
        return json.dumps(data, indent=2)
    
    @staticmethod
    def _extract_from_xml(content: bytes) -> str:
        """Extract text from XML"""
        soup = BeautifulSoup(content, 'xml')
        return soup.get_text()
    
    @staticmethod
    def _extract_from_docx(content: bytes) -> str:
        """Extract text from DOCX"""
        docx_file = io.BytesIO(content)
        doc = docx.Document(docx_file)
        
        text_parts = []
        for paragraph in doc.paragraphs:
            if paragraph.text:
                text_parts.append(paragraph.text)
        
        return "\n\n".join(text_parts)