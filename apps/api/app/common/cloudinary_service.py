import os
from datetime import datetime, timezone
from typing import Optional, BinaryIO
from uuid import UUID
import logging

import cloudinary
import cloudinary.uploader
from cloudinary.utils import cloudinary_url
from fastapi import UploadFile, HTTPException

logger = logging.getLogger(__name__)


class CloudinaryService:
    def __init__(self, config):
        self.config = config
        self.config.configure()

    async def upload_document(
        self,
        file: UploadFile,
        organization_id: UUID,
        document_id: Optional[UUID] = None,
    ) -> dict:
        """
        Upload document to Cloudinary with proper organization structure.
        Does NOT use metadata fields (requires pre-created fields in Cloudinary).
        """
        logger.info(f"Cloudinary upload: file={file.filename}, org={organization_id}")
        
        # Validate file size
        await self._validate_file_size(file)
        
        # Validate file format
        await self._validate_file_format(file)
        
        # Read file content
        content = await file.read()
        logger.info(f"File read: {len(content)} bytes")
        
        # Generate public ID with organization structure
        public_id = self._generate_public_id(organization_id, file.filename, document_id)
        logger.info(f"Generated public_id: {public_id}")
        
        try:
            # Upload to Cloudinary (without metadata - it requires pre-created fields)
            result = cloudinary.uploader.upload(
                content,
                public_id=public_id,
                folder=f"{self.config.folder}/{organization_id}",
                resource_type=self.config.resource_type,
                overwrite=True,
                tags=[str(organization_id), "knowledge_document"],
            )
            
            logger.info(f"Cloudinary upload success: {result['public_id']}")
            
            return {
                "public_id": result["public_id"],
                "url": result["secure_url"],
                "format": result.get("format", ""),
                "resource_type": result["resource_type"],
                "size_bytes": result["bytes"],
                "created_at": result.get("created_at", ""),
            }
            
        except Exception as e:
            logger.error(f"Cloudinary upload failed: {str(e)}")
            raise ValueError(f"Cloudinary upload failed: {str(e)}")
            
        finally:
            await file.seek(0)  # Reset file pointer

    async def delete_document(self, public_id: str) -> bool:
        """
        Delete document from Cloudinary
        """
        try:
            result = cloudinary.uploader.destroy(
                public_id,
                resource_type=self.config.resource_type,
            )
            success = result.get("result") == "ok"
            if success:
                logger.info(f"Deleted from Cloudinary: {public_id}")
            else:
                logger.warning(f"Failed to delete from Cloudinary: {public_id}")
            return success
        except Exception as e:
            logger.error(f"Failed to delete from Cloudinary: {str(e)}")
            return False

    async def get_document_url(self, public_id: str, expiration_seconds: int = 3600) -> str:
        """
        Generate a signed URL for document access
        """
        try:
            url, _ = cloudinary_url(
                public_id,
                resource_type=self.config.resource_type,
                type="upload",
                sign_url=False,
                expires_at=int(datetime.now(timezone.utc).timestamp()) + expiration_seconds,
            )
            return url
        except Exception as e:
            logger.error(f"Failed to generate URL: {str(e)}")
            raise ValueError(f"Failed to generate download URL: {str(e)}")

    def _generate_public_id(
        self,
        organization_id: UUID,
        filename: str,
        document_id: Optional[UUID] = None,
    ) -> str:
        """
        Generate structured public ID for Cloudinary
        """
        # Remove extension from filename
        base_name = filename.rsplit('.', 1)[0] if '.' in filename else filename
        # Clean the filename (replace spaces/special chars)
        base_name = "".join(c if c.isalnum() or c in "_-" else "_" for c in base_name)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        
        if document_id:
            return f"{base_name}_{str(document_id)[:8]}_{timestamp}"
        return f"{base_name}_{timestamp}"

    async def _validate_file_size(self, file: UploadFile) -> None:
        """
        Validate file size doesn't exceed maximum
        """
        max_size = self.config.max_file_size_mb * 1024 * 1024
        
        # Read file to check size
        content = await file.read()
        file_size = len(content)
        await file.seek(0)  # Reset pointer
        
        if file_size > max_size:
            raise ValueError(
                f"File size ({file_size / 1024 / 1024:.1f}MB) exceeds maximum allowed size "
                f"of {self.config.max_file_size_mb}MB"
            )
        
        if file_size == 0:
            raise ValueError("File is empty")

    async def _validate_file_format(self, file: UploadFile) -> None:
        """
        Validate file format is allowed
        """
        if not file.filename:
            raise ValueError("Filename is required")
        
        file_extension = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
        
        if file_extension not in self.config.allowed_formats:
            raise ValueError(
                f"File format '.{file_extension}' is not allowed. "
                f"Allowed formats: {', '.join(self.config.allowed_formats)}"
            )