import cloudinary
import cloudinary.uploader
from cloudinary.utils import cloudinary_url
from pydantic import BaseModel
from typing import Optional
import os


class CloudinaryConfig(BaseModel):
    cloud_name: str
    api_key: str
    api_secret: str
    folder: str = "knowledge_documents"
    resource_type: str = "raw"
    allowed_formats: list[str] = ["pdf", "txt", "md", "csv", "json", "xml"]
    max_file_size_mb: int = 10

    @classmethod
    def from_env(cls) -> "CloudinaryConfig":
        return cls(
            cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME", ""),
            api_key=os.getenv("CLOUDINARY_API_KEY", ""),
            api_secret=os.getenv("CLOUDINARY_API_SECRET", ""),
            folder=os.getenv("CLOUDINARY_FOLDER", "knowledge_documents"),
            resource_type=os.getenv("CLOUDINARY_RESOURCE_TYPE", "raw"),
            allowed_formats=os.getenv("CLOUDINARY_ALLOWED_FORMATS", "pdf,txt,md,csv,json,xml").split(","),
            max_file_size_mb=int(os.getenv("CLOUDINARY_MAX_FILE_SIZE_MB", "10")),
        )

    def configure(self):
        cloudinary.config(
            cloud_name=self.cloud_name,
            api_key=self.api_key,
            api_secret=self.api_secret,
            secure=True,
        )