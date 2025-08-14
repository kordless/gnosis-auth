"""
Storage Service for Gnosis Auth

Handles all storage operations:
- User-partitioned file storage
- Automatic cloud/local switching
- File metadata tracking
- Secure access control

Storage Structure:
- Local Development:
    storage/
    ├── models/              # NDB model data (JSON files)
    │   ├── User.json
    │   ├── ApiToken.json
    │   └── Transaction.json
    └── users/               # User file storage
        └── {user_hash}/
            ├── uploads/
            ├── documents/
            └── temp/
            
- Production (Cloud):
- NDB models → Google Datastore
- Files → GCS bucket under users/{user_hash}/
"""

import os
import io
import json
import hashlib
import logging
from typing import Dict, Any, Optional, Union, BinaryIO, List
from pathlib import Path
from datetime import datetime, timedelta

from core.config import config, STORAGE_PATH, USERS_DIR, GCS_BUCKET_NAME
from core.lib.util import compute_user_hash, sanitize_filename

logger = logging.getLogger(__name__)

# Try to import GCS
try:
    from google.cloud import storage
    GCS_AVAILABLE = True
except ImportError:
    logger.warning("Could not import GCS. Cloud storage will not be available.")
    GCS_AVAILABLE = False


def get_storage_config():
    """
    Get current storage configuration.
    
    Returns:
        dict: Configuration details including:
            - environment: Current environment (development/staging/production)
            - use_cloud_storage: Whether using cloud storage
            - storage_path: Base storage directory
            - users_path: Path for user files
            - gcs_bucket: GCS bucket name (if applicable)
    """
    return {
        'environment': config.ENVIRONMENT,
        'use_cloud_storage': config.use_cloud_storage,
        'storage_path': STORAGE_PATH,
        'users_path': USERS_DIR,
        'gcs_bucket': GCS_BUCKET_NAME if config.use_cloud_storage else None,
        'gcs_available': GCS_AVAILABLE
    }


class StorageService:
    """
    Storage service that handles user-partitioned file operations
    """
    
    def __init__(self, user_email: Optional[str] = None):
        """Initialize the storage service based on environment"""
        self._gcs_client = None
        self._bucket_name = GCS_BUCKET_NAME
        self._storage_path = STORAGE_PATH
        self._user_email = user_email
        self._user_hash = compute_user_hash(user_email) if user_email else None
        
        # Initialize based on environment
        if config.use_cloud_storage and GCS_AVAILABLE:
            self._init_gcs()
        else:
            # Ensure local directories exist
            self._ensure_local_dirs()
    
    def _init_gcs(self):
        """Initialize Google Cloud Storage client"""
        try:
            self._gcs_client = storage.Client()
            # Check if bucket exists
            try:
                bucket = self._gcs_client.get_bucket(self._bucket_name)
                logger.debug(f"Connected to existing GCS bucket: {self._bucket_name}")
            except Exception:
                # Try to create bucket if it doesn't exist
                try:
                    bucket = self._gcs_client.create_bucket(self._bucket_name)
                    logger.info(f"Created GCS bucket: {self._bucket_name}")
                except Exception as e:
                    logger.error(f"Could not create GCS bucket {self._bucket_name}: {e}")
                    raise
            
            logger.info(f"GCS client initialized for bucket {self._bucket_name}")
        except Exception as e:
            logger.error(f"Failed to initialize GCS: {str(e)}")
            raise
    
    def _ensure_local_dirs(self):
        """Ensure all required local directories exist"""
        # Create base storage directory
        os.makedirs(self._storage_path, exist_ok=True)
        os.makedirs(USERS_DIR, exist_ok=True)
        
        # Create user directory if user_hash is available
        if self._user_hash:
            user_dir = os.path.join(USERS_DIR, self._user_hash)
            os.makedirs(user_dir, exist_ok=True)
            os.makedirs(os.path.join(user_dir, 'uploads'), exist_ok=True)
            os.makedirs(os.path.join(user_dir, 'documents'), exist_ok=True)
            os.makedirs(os.path.join(user_dir, 'temp'), exist_ok=True)
        
        logger.debug(f"Ensured local storage directories exist: {self._storage_path}")
    
    def set_user_email(self, email: Optional[str]):
        """Update the user email and recompute hash"""
        self._user_email = email
        self._user_hash = compute_user_hash(email) if email else None
        
        # Ensure user directories exist in local mode
        if not config.use_cloud_storage and self._user_hash:
            self._ensure_local_dirs()
        
        logger.debug(f"User context updated: email={email}, hash={self._user_hash}")
    
    def get_user_path(self, subfolder: str = "") -> str:
        """Get the user-specific storage path"""
        if not self._user_hash:
            raise ValueError("No user context set - call set_user_email() first")
        
        base_path = f"users/{self._user_hash}"
        if subfolder:
            return f"{base_path}/{subfolder}"
        return base_path
    
    def get_absolute_user_path(self, subfolder: str = "") -> str:
        """Get absolute path for local storage"""
        if config.use_cloud_storage:
            raise ValueError("Absolute paths not applicable in cloud storage mode")
        
        if not self._user_hash:
            raise ValueError("No user context set")
        
        user_dir = os.path.join(USERS_DIR, self._user_hash)
        if subfolder:
            return os.path.join(user_dir, subfolder)
        return user_dir
    
    async def save_file(self, content: Union[bytes, str], filename: str, subfolder: str = "uploads") -> Dict[str, str]:
        """
        Save a file to user-partitioned storage
        
        Args:
            content: File content (bytes or string)
            filename: Filename to save
            subfolder: Subfolder within user directory (uploads, documents, temp)
            
        Returns:
            Dict with file information (path, url, size, etc.)
        """
        if not self._user_hash:
            raise ValueError("No user context set - call set_user_email() first")
        
        # Sanitize filename
        safe_filename = sanitize_filename(filename)
        
        # Convert string to bytes if needed
        if isinstance(content, str):
            content = content.encode('utf-8')
        
        user_path = self.get_user_path(subfolder)
        full_path = f"{user_path}/{safe_filename}"
        
        file_size = len(content)
        
        if config.use_cloud_storage and self._gcs_client:
            # Save to GCS
            bucket = self._gcs_client.bucket(self._bucket_name)
            blob = bucket.blob(full_path)
            
            # Set content type based on file extension
            content_type = self._guess_content_type(safe_filename)
            blob.content_type = content_type
            
            blob.upload_from_string(content)
            logger.info(f"Saved file to GCS: {full_path} ({file_size} bytes)")
            
            return {
                'filename': safe_filename,
                'path': full_path,
                'url': self.get_file_url(safe_filename, subfolder),
                'size': file_size,
                'content_type': content_type,
                'storage': 'gcs'
            }
        else:
            # Save to local storage
            local_dir = self.get_absolute_user_path(subfolder)
            os.makedirs(local_dir, exist_ok=True)
            
            file_path = os.path.join(local_dir, safe_filename)
            
            with open(file_path, 'wb') as f:
                f.write(content)
            
            logger.info(f"Saved file locally: {file_path} ({file_size} bytes)")
            
            return {
                'filename': safe_filename,
                'path': file_path,
                'url': self.get_file_url(safe_filename, subfolder),
                'size': file_size,
                'content_type': self._guess_content_type(safe_filename),
                'storage': 'local'
            }
    
    async def get_file(self, filename: str, subfolder: str = "uploads") -> bytes:
        """
        Retrieve a file from user-partitioned storage
        
        Args:
            filename: Filename to retrieve
            subfolder: Subfolder within user directory
            
        Returns:
            File content as bytes
        """
        if not self._user_hash:
            raise ValueError("No user context set")
        
        user_path = self.get_user_path(subfolder)
        full_path = f"{user_path}/{filename}"
        
        if config.use_cloud_storage and self._gcs_client:
            # Get from GCS
            bucket = self._gcs_client.bucket(self._bucket_name)
            blob = bucket.blob(full_path)
            
            if not blob.exists():
                raise FileNotFoundError(f"File not found: {filename}")
            
            content = blob.download_as_bytes()
            logger.debug(f"Retrieved file from GCS: {full_path}")
            return content
        else:
            # Get from local storage
            file_path = os.path.join(self.get_absolute_user_path(subfolder), filename)
            
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"File not found: {filename}")
            
            with open(file_path, 'rb') as f:
                content = f.read()
            
            logger.debug(f"Retrieved file locally: {file_path}")
            return content
    
    async def delete_file(self, filename: str, subfolder: str = "uploads") -> bool:
        """
        Delete a file from user-partitioned storage
        
        Args:
            filename: Filename to delete
            subfolder: Subfolder within user directory
            
        Returns:
            True if deletion was successful
        """
        if not self._user_hash:
            raise ValueError("No user context set")
        
        user_path = self.get_user_path(subfolder)
        full_path = f"{user_path}/{filename}"
        
        if config.use_cloud_storage and self._gcs_client:
            # Delete from GCS
            bucket = self._gcs_client.bucket(self._bucket_name)
            blob = bucket.blob(full_path)
            
            if blob.exists():
                blob.delete()
                logger.info(f"Deleted file from GCS: {full_path}")
                return True
            else:
                logger.warning(f"File not found for deletion: {full_path}")
                return False
        else:
            # Delete from local storage
            file_path = os.path.join(self.get_absolute_user_path(subfolder), filename)
            
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Deleted file locally: {file_path}")
                return True
            else:
                logger.warning(f"File not found for deletion: {file_path}")
                return False
    
    async def list_files(self, subfolder: str = "uploads", prefix: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List files in user-partitioned storage
        
        Args:
            subfolder: Subfolder within user directory
            prefix: Optional prefix to filter files
            
        Returns:
            List of file metadata
        """
        if not self._user_hash:
            raise ValueError("No user context set")
        
        user_path = self.get_user_path(subfolder)
        search_path = f"{user_path}/"
        if prefix:
            search_path += prefix
        
        files = []
        
        if config.use_cloud_storage and self._gcs_client:
            # List from GCS
            bucket = self._gcs_client.bucket(self._bucket_name)
            blobs = bucket.list_blobs(prefix=search_path)
            
            for blob in blobs:
                # Skip directory markers
                if blob.name.endswith('/'):
                    continue
                
                # Extract filename from full path
                filename = blob.name.replace(f"{user_path}/", "")
                
                files.append({
                    'filename': filename,
                    'size': blob.size,
                    'created': blob.time_created,
                    'modified': blob.updated,
                    'content_type': blob.content_type,
                    'md5_hash': blob.md5_hash,
                    'etag': blob.etag,
                    'storage': 'gcs'
                })
        else:
            # List from local storage
            local_dir = self.get_absolute_user_path(subfolder)
            if not os.path.exists(local_dir):
                return files
            
            for filename in os.listdir(local_dir):
                file_path = os.path.join(local_dir, filename)
                
                # Skip directories
                if os.path.isdir(file_path):
                    continue
                
                # Apply prefix filter
                if prefix and not filename.startswith(prefix):
                    continue
                
                stat = os.stat(file_path)
                
                files.append({
                    'filename': filename,
                    'size': stat.st_size,
                    'created': datetime.fromtimestamp(stat.st_ctime),
                    'modified': datetime.fromtimestamp(stat.st_mtime),
                    'content_type': self._guess_content_type(filename),
                    'storage': 'local'
                })
        
        return files
    
    def get_file_url(self, filename: str, subfolder: str = "uploads", expiry_hours: int = 24) -> str:
        """
        Get a URL for accessing a file
        
        Args:
            filename: Filename
            subfolder: Subfolder within user directory
            expiry_hours: Hours until URL expires (for signed URLs)
            
        Returns:
            URL for accessing the file
        """
        if not self._user_hash:
            raise ValueError("No user context set")
        
        if config.use_cloud_storage and self._gcs_client:
            # Generate signed URL for GCS
            user_path = self.get_user_path(subfolder)
            full_path = f"{user_path}/{filename}"
            
            bucket = self._gcs_client.bucket(self._bucket_name)
            blob = bucket.blob(full_path)
            
            expiration = datetime.utcnow() + timedelta(hours=expiry_hours)
            
            try:
                signed_url = blob.generate_signed_url(
                    version="v4",
                    expiration=expiration,
                    method="GET"
                )
                return signed_url
            except Exception as e:
                logger.error(f"Failed to generate signed URL: {e}")
                # Fallback to relative URL
                return f"/storage/{self._user_hash}/{subfolder}/{filename}"
        else:
            # Return relative URL for local files (served through app)
            return f"/storage/{self._user_hash}/{subfolder}/{filename}"
    
    def get_user_storage_usage(self) -> Dict[str, int]:
        """
        Get storage usage statistics for the current user
        
        Returns:
            Dict with storage usage information
        """
        if not self._user_hash:
            raise ValueError("No user context set")
        
        total_size = 0
        file_count = 0
        
        subfolders = ['uploads', 'documents', 'temp']
        usage_by_folder = {}
        
        for subfolder in subfolders:
            folder_size = 0
            folder_files = 0
            
            try:
                files = await self.list_files(subfolder)
                for file_info in files:
                    folder_size += file_info['size']
                    folder_files += 1
                
                usage_by_folder[subfolder] = {
                    'size': folder_size,
                    'files': folder_files
                }
                
                total_size += folder_size
                file_count += folder_files
                
            except Exception as e:
                logger.warning(f"Could not get usage for {subfolder}: {e}")
                usage_by_folder[subfolder] = {'size': 0, 'files': 0}
        
        return {
            'total_size': total_size,
            'total_files': file_count,
            'by_folder': usage_by_folder,
            'user_hash': self._user_hash
        }
    
    def _guess_content_type(self, filename: str) -> str:
        """Guess content type from filename"""
        ext = filename.lower().split('.')[-1] if '.' in filename else ''
        content_types = {
            'txt': 'text/plain',
            'md': 'text/markdown',
            'html': 'text/html',
            'css': 'text/css',
            'js': 'text/javascript',
            'json': 'application/json',
            'xml': 'application/xml',
            'pdf': 'application/pdf',
            'doc': 'application/msword',
            'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'xls': 'application/vnd.ms-excel',
            'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'ppt': 'application/vnd.ms-powerpoint',
            'pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            'png': 'image/png',
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'gif': 'image/gif',
            'svg': 'image/svg+xml',
            'webp': 'image/webp',
            'mp3': 'audio/mpeg',
            'wav': 'audio/wav',
            'mp4': 'video/mp4',
            'webm': 'video/webm',
            'zip': 'application/zip',
            'tar': 'application/x-tar',
            'gz': 'application/gzip',
            'rar': 'application/x-rar-compressed',
        }
        return content_types.get(ext, 'application/octet-stream')


# Singleton instance
_storage_instance = None

def get_storage_service(user_email: Optional[str] = None) -> StorageService:
    """Get or create a storage service instance"""
    global _storage_instance
    if _storage_instance is None or (user_email and _storage_instance._user_email != user_email):
        _storage_instance = StorageService(user_email)
    elif user_email:
        _storage_instance.set_user_email(user_email)
    return _storage_instance


# Cleanup utilities
async def cleanup_temp_files(max_age_hours: int = 24):
    """Clean up temporary files older than specified age"""
    cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
    
    if config.use_cloud_storage and GCS_AVAILABLE:
        # Clean up GCS temp files
        try:
            client = storage.Client()
            bucket = client.bucket(GCS_BUCKET_NAME)
            blobs = bucket.list_blobs(prefix="users/")
            
            deleted_count = 0
            for blob in blobs:
                if '/temp/' in blob.name and blob.time_created < cutoff_time:
                    blob.delete()
                    deleted_count += 1
            
            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} temp files from GCS")
        except Exception as e:
            logger.error(f"Failed to clean up GCS temp files: {e}")
    else:
        # Clean up local temp files
        try:
            deleted_count = 0
            for user_dir in os.listdir(USERS_DIR):
                temp_dir = os.path.join(USERS_DIR, user_dir, 'temp')
                if os.path.exists(temp_dir):
                    for filename in os.listdir(temp_dir):
                        file_path = os.path.join(temp_dir, filename)
                        if os.path.isfile(file_path):
                            file_time = datetime.fromtimestamp(os.path.getctime(file_path))
                            if file_time < cutoff_time:
                                os.remove(file_path)
                                deleted_count += 1
            
            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} temp files from local storage")
        except Exception as e:
            logger.error(f"Failed to clean up local temp files: {e}")


async def get_global_storage_stats() -> Dict[str, Any]:
    """Get global storage statistics across all users"""
    stats = {
        'total_users': 0,
        'total_size': 0,
        'total_files': 0,
        'by_user': []
    }
    
    if config.use_cloud_storage and GCS_AVAILABLE:
        # Get stats from GCS
        try:
            client = storage.Client()
            bucket = client.bucket(GCS_BUCKET_NAME)
            blobs = bucket.list_blobs(prefix="users/")
            
            user_stats = {}
            for blob in blobs:
                path_parts = blob.name.split('/')
                if len(path_parts) >= 2:
                    user_hash = path_parts[1]
                    if user_hash not in user_stats:
                        user_stats[user_hash] = {'size': 0, 'files': 0}
                    user_stats[user_hash]['size'] += blob.size
                    user_stats[user_hash]['files'] += 1
            
            stats['total_users'] = len(user_stats)
            for user_hash, user_data in user_stats.items():
                stats['total_size'] += user_data['size']
                stats['total_files'] += user_data['files']
                stats['by_user'].append({
                    'user_hash': user_hash,
                    'size': user_data['size'],
                    'files': user_data['files']
                })
        except Exception as e:
            logger.error(f"Failed to get GCS storage stats: {e}")
    else:
        # Get stats from local storage
        try:
            if os.path.exists(USERS_DIR):
                for user_hash in os.listdir(USERS_DIR):
                    user_dir = os.path.join(USERS_DIR, user_hash)
                    if os.path.isdir(user_dir):
                        user_size = 0
                        user_files = 0
                        
                        for root, dirs, files in os.walk(user_dir):
                            for file in files:
                                file_path = os.path.join(root, file)
                                try:
                                    user_size += os.path.getsize(file_path)
                                    user_files += 1
                                except OSError:
                                    pass
                        
                        stats['total_size'] += user_size
                        stats['total_files'] += user_files
                        stats['by_user'].append({
                            'user_hash': user_hash,
                            'size': user_size,
                            'files': user_files
                        })
                
                stats['total_users'] = len(stats['by_user'])
        except Exception as e:
            logger.error(f"Failed to get local storage stats: {e}")
    
    return stats
