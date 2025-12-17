"""Storage service for file uploads and code generation."""
import os
import importlib.util
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Tuple, Optional
from urllib.parse import urlparse

import aiofiles
import httpx

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class BaseStorageService(ABC):
    """Abstract base class for storage services."""

    @abstractmethod
    async def save_uploaded_file(
        self, file_content: bytes, filename: str, tenant_id: Optional[str], document_id: str
    ) -> Tuple[str, str]:
        """Save an uploaded file and return its path and filename."""
        pass

    @abstractmethod
    async def save_file_from_url(
        self,
        file_url: str,
        tenant_id: Optional[str],
        document_id: str,
        original_filename_override: Optional[str] = None,
    ) -> Tuple[str, str]:
        """Download and save a file from URL."""
        pass

    @abstractmethod
    async def delete_file(
        self, file_path_or_uri: str, tenant_id: Optional[str], document_id: str
    ) -> bool:
        """Delete a file."""
        pass

    @abstractmethod
    def get_file_path(self, tenant_id: Optional[str], document_id: str) -> str:
        """Get the file path for a document."""
        pass


class LocalStorageService(BaseStorageService):
    """Local filesystem storage service."""

    def __init__(self, base_path: str = None):
        self.base_path = Path(base_path or settings.LOCAL_STORAGE_PATH)
        self.base_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"LocalStorageService initialized. Base path: {self.base_path.resolve()}")

    def _get_save_path(self, tenant_id: Optional[str], filename: str) -> Path:
        """Construct storage path: base_path / [tenant_X] / filename."""
        current_path = self.base_path
        if tenant_id:
            current_path = current_path / f"tenant_{tenant_id}"
        current_path.mkdir(parents=True, exist_ok=True)
        return current_path / filename

    async def save_uploaded_file(
        self, file_content: bytes, filename: str, tenant_id: Optional[str], document_id: str
    ) -> Tuple[str, str]:
        """Save uploaded file content."""
        file_extension = Path(filename).suffix or ".bin"
        file_location = self._get_save_path(tenant_id, document_id).with_suffix(file_extension)

        try:
            async with aiofiles.open(file_location, "wb") as out_file:
                await out_file.write(file_content)
            logger.info(f"File '{filename}' saved to: {file_location}")
            return str(file_location.resolve()), document_id
        except Exception as e:
            logger.error(f"Error saving file '{file_location}': {e}", exc_info=True)
            raise IOError(f"Could not save file: {e}")

    async def save_file_from_url(
        self,
        file_url: str,
        tenant_id: Optional[str],
        document_id: str,
        original_filename_override: Optional[str] = None,
    ) -> Tuple[str, str]:
        """Download and save file from URL."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                logger.info(f"Downloading file from URL: {file_url}")
                response = await client.get(file_url)
                response.raise_for_status()
                file_content = response.content
                logger.info(f"Downloaded {len(file_content)} bytes from {file_url}")
        except Exception as e:
            logger.error(f"Error downloading from '{file_url}': {e}", exc_info=True)
            raise IOError(f"Could not download file: {e}")

        filename = original_filename_override or os.path.basename(urlparse(file_url).path) or document_id
        file_extension = Path(file_url).suffix or ".bin"
        file_location = self._get_save_path(tenant_id, document_id).with_suffix(file_extension)

        try:
            async with aiofiles.open(file_location, "wb") as out_file:
                await out_file.write(file_content)
            logger.info(f"File saved to: {file_location}")
            return str(file_location.resolve()), document_id
        except Exception as e:
            logger.error(f"Error saving downloaded file: {e}", exc_info=True)
            raise IOError(f"Could not save downloaded file: {e}")

    def get_file_path(self, tenant_id: Optional[str], document_id: str) -> str:
        """Get absolute path for a document."""
        path = self._get_save_path(tenant_id, document_id)
        return str(path.resolve())

    async def delete_file(
        self, file_path_or_uri: str, tenant_id: Optional[str], document_id: str
    ) -> bool:
        """Delete a file and clean up empty directories."""
        file_path = Path(file_path_or_uri)
        try:
            if file_path.exists() and file_path.is_file():
                os.remove(file_path)
                logger.info(f"File deleted: {file_path}")

                # Remove empty tenant directory
                parent_dir = file_path.parent
                if parent_dir != self.base_path and parent_dir.is_dir():
                    if not any(parent_dir.iterdir()):
                        try:
                            parent_dir.rmdir()
                            logger.debug(f"Removed empty directory: {parent_dir}")
                        except OSError as e:
                            logger.warning(f"Could not remove directory {parent_dir}: {e}")
                return True
            else:
                logger.warning(f"File not found for deletion: {file_path}")
                return False
        except Exception as e:
            logger.error(f"Error deleting file {file_path}: {e}", exc_info=True)
            return False

    def get_file_extension(self, tenant_id: str, document_id: str) -> Optional[str]:
        """Find file extension for a document."""
        directory = self._get_save_path(tenant_id, "").parent
        if not directory.exists():
            return None

        for entry in os.listdir(directory):
            full_path = os.path.join(directory, entry)
            if os.path.isfile(full_path):
                name, ext = os.path.splitext(entry)
                if name == document_id:
                    return ext.lstrip(".")
        return None


class S3StorageService(BaseStorageService):
    """AWS S3 storage service (placeholder implementation)."""

    def __init__(self, bucket_name: str = None):
        self.bucket_name = bucket_name or settings.S3_BUCKET_NAME
        logger.info(f"S3StorageService initialized for bucket '{self.bucket_name}'")
        if not self.bucket_name:
            raise ValueError("S3_BUCKET_NAME not configured")
        # TODO: Initialize boto3 client
        # self.s3_client = boto3.client('s3', ...)

    def _get_s3_key(self, tenant_id: Optional[str], filename: str) -> str:
        """Construct S3 key: [tenant_X/]filename."""
        return "/".join(filter(None, [f"tenant_{tenant_id}" if tenant_id else None, filename]))

    async def save_uploaded_file(
        self, file_content: bytes, filename: str, tenant_id: Optional[str], document_id: str
    ) -> Tuple[str, str]:
        """Save file to S3."""
        s3_key = self._get_s3_key(tenant_id, filename)
        logger.warning(f"S3 save_uploaded_file: PLACEHOLDER. Would upload to '{s3_key}'")
        # TODO: Implement actual S3 upload
        # self.s3_client.put_object(Bucket=self.bucket_name, Key=s3_key, Body=file_content)
        s3_uri = f"s3://{self.bucket_name}/{s3_key}"
        return s3_uri, filename

    async def save_file_from_url(
        self,
        file_url: str,
        tenant_id: Optional[str],
        document_id: str,
        original_filename_override: Optional[str] = None,
    ) -> Tuple[str, str]:
        """Download and save file to S3."""
        logger.warning(f"S3 save_file_from_url: PLACEHOLDER for URL {file_url}")
        filename = original_filename_override or os.path.basename(urlparse(file_url).path) or document_id
        s3_key = self._get_s3_key(tenant_id, filename)
        return f"s3://{self.bucket_name}/{s3_key}", filename

    def get_file_path(self, tenant_id: Optional[str], document_id: str) -> str:
        """Get S3 URI for a document."""
        s3_key = self._get_s3_key(tenant_id, document_id)
        return f"s3://{self.bucket_name}/{s3_key}"

    async def delete_file(
        self, file_path_or_uri: str, tenant_id: Optional[str], document_id: str
    ) -> bool:
        """Delete file from S3."""
        logger.warning(f"S3 delete_file: PLACEHOLDER for URI '{file_path_or_uri}'")
        # TODO: Implement actual S3 delete
        # s3_key = self._get_s3_key(tenant_id, document_id)
        # self.s3_client.delete_object(Bucket=self.bucket_name, Key=s3_key)
        return True


class CodeStorageService:
    """Service for saving and managing generated code files."""

    def __init__(self, base_path: str = "connector"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def setup_tenant_folder(tenant_id: str) -> str:
        """Create tenant folder for code storage."""
        base_dir = Path("code") / tenant_id
        base_dir.mkdir(parents=True, exist_ok=True)
        os.chmod(base_dir, 0o755)
        return str(base_dir)

    async def save_code(
        self,
        code: str,
        tenant_id: str,
        connector_name: str,
        file_extension: str = ".py",
        format_code: bool = True,
    ) -> str:
        """Format and save generated code."""
        if format_code:
            try:
                import black
                mode = black.Mode()
                formatted_code = black.format_str(code, mode=mode)
            except ImportError:
                logger.warning("black not installed, saving unformatted code")
                formatted_code = code
            except Exception as e:
                logger.warning(f"Code formatting failed: {e}, saving unformatted")
                formatted_code = code
        else:
            formatted_code = code

        base_dir = self.base_path / tenant_id
        base_dir.mkdir(parents=True, exist_ok=True)
        file_path = base_dir / f"{connector_name}{file_extension}"

        with open(file_path, "w") as f:
            f.write(formatted_code)

        os.chmod(file_path, 0o644)
        logger.info(f"Code saved to: {file_path}")
        return str(file_path)

    async def update_code(
        self,
        code: str,
        path: str,
        format_code: bool = True,
    ) -> str:
        """Update existing code file."""
        if format_code:
            try:
                import black
                mode = black.Mode()
                formatted_code = black.format_str(code, mode=mode)
            except ImportError:
                formatted_code = code
            except Exception:
                formatted_code = code
        else:
            formatted_code = code

        with open(path, "w") as f:
            f.write(formatted_code)

        os.chmod(path, 0o644)
        return path

    @staticmethod
    def get_agent_file_path(tenant_id: str, agent_id: str) -> Path:
        """Get file path for an agent's code."""
        return Path("connector") / tenant_id / f"{agent_id}.py"

    @staticmethod
    def load_agent_module(file_path: Path):
        """Dynamically load an agent's Python file as a module."""
        if not file_path.exists():
            raise FileNotFoundError(f"Agent file not found: {file_path}")

        spec = importlib.util.spec_from_file_location("agent_module", file_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module


def get_storage_service() -> BaseStorageService:
    """Factory function to get the appropriate storage service."""
    storage_type = getattr(settings, "STORAGE_TYPE", "local")
    if storage_type == "s3":
        return S3StorageService()
    return LocalStorageService()


def get_code_storage_service() -> CodeStorageService:
    """Get code storage service instance."""
    return CodeStorageService()
