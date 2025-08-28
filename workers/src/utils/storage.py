"""Storage client for S3/MinIO operations."""

import asyncio
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any
import json

import boto3
from minio import Minio
import structlog

logger = structlog.get_logger(__name__)


class StorageClient:
    """Client for S3/MinIO storage operations."""

    def __init__(self):
        self.minio_client = None
        self.s3_client = None
        self.bucket_name = "ai-patent-explorer"
        self._init_clients()

    def _init_clients(self):
        """Initialize storage clients."""
        try:
            # Initialize MinIO client for local development
            self.minio_client = Minio(
                "localhost:9000",
                access_key="minioadmin",
                secret_key="minioadmin",
                secure=False
            )
            
            # Initialize S3 client for production
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id="YOUR_ACCESS_KEY",
                aws_secret_access_key="YOUR_SECRET_KEY",
                region_name="us-east-1"
            )
            
            # Ensure bucket exists
            self._ensure_bucket_exists()
            
        except Exception as e:
            logger.error("Failed to initialize storage clients", error=str(e))

    def _ensure_bucket_exists(self):
        """Ensure the storage bucket exists."""
        try:
            if self.minio_client:
                if not self.minio_client.bucket_exists(self.bucket_name):
                    self.minio_client.make_bucket(self.bucket_name)
                    logger.info("Created MinIO bucket", bucket=self.bucket_name)
        except Exception as e:
            logger.error("Failed to ensure bucket exists", error=str(e))

    async def upload_file(self, local_path: str, remote_path: str) -> str:
        """Upload a file to storage."""
        try:
            if self.minio_client:
                return await self._upload_to_minio(local_path, remote_path)
            elif self.s3_client:
                return await self._upload_to_s3(local_path, remote_path)
            else:
                raise Exception("No storage client available")
        except Exception as e:
            logger.error("File upload failed", error=str(e), local_path=local_path, remote_path=remote_path)
            raise

    async def download_file(self, remote_path: str) -> Path:
        """Download a file from storage."""
        try:
            if self.minio_client:
                return await self._download_from_minio(remote_path)
            elif self.s3_client:
                return await self._download_from_s3(remote_path)
            else:
                raise Exception("No storage client available")
        except Exception as e:
            logger.error("File download failed", error=str(e), remote_path=remote_path)
            raise

    async def upload_text(self, text: str, remote_path: str) -> str:
        """Upload text content to storage."""
        try:
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
                f.write(text)
                temp_path = f.name
            
            return await self.upload_file(temp_path, remote_path)
        except Exception as e:
            logger.error("Text upload failed", error=str(e), remote_path=remote_path)
            raise

    async def upload_json(self, data: Dict[str, Any], remote_path: str) -> str:
        """Upload JSON data to storage."""
        try:
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
                json.dump(data, f, indent=2)
                temp_path = f.name
            
            return await self.upload_file(temp_path, remote_path)
        except Exception as e:
            logger.error("JSON upload failed", error=str(e), remote_path=remote_path)
            raise

    async def _upload_to_minio(self, local_path: str, remote_path: str) -> str:
        """Upload file to MinIO."""
        try:
            self.minio_client.fput_object(
                self.bucket_name,
                remote_path,
                local_path
            )
            logger.info("File uploaded to MinIO", local_path=local_path, remote_path=remote_path)
            return f"minio://{self.bucket_name}/{remote_path}"
        except Exception as e:
            logger.error("MinIO upload failed", error=str(e))
            raise

    async def _upload_to_s3(self, local_path: str, remote_path: str) -> str:
        """Upload file to S3."""
        try:
            self.s3_client.upload_file(
                local_path,
                self.bucket_name,
                remote_path
            )
            logger.info("File uploaded to S3", local_path=local_path, remote_path=remote_path)
            return f"s3://{self.bucket_name}/{remote_path}"
        except Exception as e:
            logger.error("S3 upload failed", error=str(e))
            raise

    async def _download_from_minio(self, remote_path: str) -> Path:
        """Download file from MinIO."""
        try:
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.tmp')
            temp_path = Path(temp_file.name)
            temp_file.close()
            
            self.minio_client.fget_object(
                self.bucket_name,
                remote_path,
                str(temp_path)
            )
            logger.info("File downloaded from MinIO", remote_path=remote_path, local_path=str(temp_path))
            return temp_path
        except Exception as e:
            logger.error("MinIO download failed", error=str(e))
            raise

    async def _download_from_s3(self, remote_path: str) -> Path:
        """Download file from S3."""
        try:
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.tmp')
            temp_path = Path(temp_file.name)
            temp_file.close()
            
            self.s3_client.download_file(
                self.bucket_name,
                remote_path,
                str(temp_path)
            )
            logger.info("File downloaded from S3", remote_path=remote_path, local_path=str(temp_path))
            return temp_path
        except Exception as e:
            logger.error("S3 download failed", error=str(e))
            raise

    async def delete_file(self, remote_path: str) -> bool:
        """Delete a file from storage."""
        try:
            if self.minio_client:
                self.minio_client.remove_object(self.bucket_name, remote_path)
            elif self.s3_client:
                self.s3_client.delete_object(Bucket=self.bucket_name, Key=remote_path)
            else:
                return False
            
            logger.info("File deleted", remote_path=remote_path)
            return True
        except Exception as e:
            logger.error("File deletion failed", error=str(e), remote_path=remote_path)
            return False

    async def list_files(self, prefix: str = "") -> list:
        """List files in storage with given prefix."""
        try:
            files = []
            if self.minio_client:
                objects = self.minio_client.list_objects(self.bucket_name, prefix=prefix, recursive=True)
                for obj in objects:
                    files.append(obj.object_name)
            elif self.s3_client:
                response = self.s3_client.list_objects_v2(Bucket=self.bucket_name, Prefix=prefix)
                if 'Contents' in response:
                    for obj in response['Contents']:
                        files.append(obj['Key'])
            
            return files
        except Exception as e:
            logger.error("File listing failed", error=str(e), prefix=prefix)
            return []

    def get_signed_url(self, remote_path: str, expires_in: int = 3600) -> str:
        """Get a signed URL for file access."""
        try:
            if self.minio_client:
                return self.minio_client.presigned_get_object(
                    self.bucket_name,
                    remote_path,
                    expires=expires_in
                )
            elif self.s3_client:
                return self.s3_client.generate_presigned_url(
                    'get_object',
                    Params={'Bucket': self.bucket_name, 'Key': remote_path},
                    ExpiresIn=expires_in
                )
            else:
                raise Exception("No storage client available")
        except Exception as e:
            logger.error("Signed URL generation failed", error=str(e), remote_path=remote_path)
            raise
