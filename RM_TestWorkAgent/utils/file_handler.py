import os
import hashlib
import uuid
from typing import Dict, Any
from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage
import logging

class FileHandler:
    """Handle file uploads, storage, and validation"""
    
    def __init__(self, storage_path: str):
        self.storage_path = storage_path
        self.logger = logging.getLogger(__name__)
        
        # Ensure storage directory exists
        os.makedirs(storage_path, exist_ok=True)
    
    def save_file(self, file: FileStorage, subfolder: str = '') -> Dict[str, Any]:
        """Save uploaded file and return file information"""
        try:
            if not file or file.filename == '':
                return {'success': False, 'error': 'No file provided'}
            
            # Validate file
            validation = self.validate_file(file)
            if not validation['valid']:
                return {'success': False, 'error': validation['error']}
            
            # Generate unique filename
            original_filename = secure_filename(file.filename)
            file_extension = os.path.splitext(original_filename)[1]
            unique_filename = f"{uuid.uuid4().hex}{file_extension}"
            
            # Create subfolder if specified
            target_dir = os.path.join(self.storage_path, subfolder) if subfolder else self.storage_path
            os.makedirs(target_dir, exist_ok=True)
            
            # Save file
            file_path = os.path.join(target_dir, unique_filename)
            file.save(file_path)
            
            # Calculate file hash
            file_hash = self.calculate_file_hash(file_path)
            
            # Get file info
            file_size = os.path.getsize(file_path)
            file_type = self.get_file_type(original_filename)
            
            return {
                'success': True,
                'filename': unique_filename,
                'original_filename': original_filename,
                'file_path': file_path,
                'file_size': file_size,
                'file_type': file_type,
                'file_hash': file_hash
            }
            
        except Exception as e:
            self.logger.error(f'File save error: {str(e)}')
            return {'success': False, 'error': str(e)}
    
    def validate_file(self, file: FileStorage) -> Dict[str, Any]:
        """Validate uploaded file"""
        try:
            if not file or file.filename == '':
                return {'valid': False, 'error': 'No file provided'}
            
            # Check file size
            file.seek(0, 2)  # Seek to end
            file_size = file.tell()
            file.seek(0)  # Reset to beginning
            
            max_size = 16 * 1024 * 1024  # 16MB
            if file_size > max_size:
                return {
                    'valid': False, 
                    'error': f'File size ({self._format_file_size(file_size)}) exceeds maximum allowed size ({self._format_file_size(max_size)})'
                }
            
            # Check file extension
            allowed_extensions = {'.xlsx', '.xls', '.pdf', '.jpg', '.jpeg', '.png', '.docx', '.doc'}
            file_extension = os.path.splitext(file.filename)[1].lower()
            
            if file_extension not in allowed_extensions:
                return {
                    'valid': False,
                    'error': f'File type "{file_extension}" not allowed. Supported types: {", ".join(sorted(allowed_extensions))}'
                }
            
            # Basic content validation for Excel files
            if file_extension in {'.xlsx', '.xls'}:
                if not self._validate_excel_content(file):
                    return {
                        'valid': False,
                        'error': 'Invalid Excel file format or corrupted file'
                    }
            
            return {'valid': True}
            
        except Exception as e:
            self.logger.error(f'File validation error: {str(e)}')
            return {'valid': False, 'error': 'File validation failed'}
    
    def _validate_excel_content(self, file: FileStorage) -> bool:
        """Basic validation for Excel file content"""
        try:
            # Read first few bytes to check file signature
            file.seek(0)
            header = file.read(8)
            file.seek(0)
            
            # Check for Excel file signatures
            xlsx_signature = b'\x50\x4B\x03\x04'  # ZIP signature (XLSX)
            xls_signature = b'\xD0\xCF\x11\xE0'   # OLE signature (XLS)
            
            return header.startswith(xlsx_signature) or header.startswith(xls_signature)
            
        except Exception:
            return False
    
    def calculate_file_hash(self, file_path: str) -> str:
        """Calculate SHA256 hash of file"""
        try:
            sha256_hash = hashlib.sha256()
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(chunk)
            return sha256_hash.hexdigest()
            
        except Exception as e:
            self.logger.error(f'Hash calculation error: {str(e)}')
            return ''
    
    def get_file_type(self, filename: str) -> str:
        """Determine file type from filename"""
        extension = os.path.splitext(filename)[1].lower()
        
        type_mapping = {
            '.xlsx': 'excel',
            '.xls': 'excel',
            '.pdf': 'pdf',
            '.jpg': 'image',
            '.jpeg': 'image',
            '.png': 'image',
            '.docx': 'document',
            '.doc': 'document'
        }
        
        return type_mapping.get(extension, 'unknown')
    
    def delete_file(self, file_path: str) -> bool:
        """Delete file safely"""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                self.logger.info(f'File deleted: {file_path}')
                return True
            return False
            
        except Exception as e:
            self.logger.error(f'File deletion error: {str(e)}')
            return False
    
    def get_file_info(self, file_path: str) -> Dict[str, Any]:
        """Get comprehensive file information"""
        try:
            if not os.path.exists(file_path):
                return {'exists': False}
            
            stat = os.stat(file_path)
            filename = os.path.basename(file_path)
            
            return {
                'exists': True,
                'filename': filename,
                'size': stat.st_size,
                'created': stat.st_ctime,
                'modified': stat.st_mtime,
                'file_type': self.get_file_type(filename),
                'hash': self.calculate_file_hash(file_path)
            }
            
        except Exception as e:
            self.logger.error(f'File info error: {str(e)}')
            return {'exists': False, 'error': str(e)}
    
    def create_backup(self, file_path: str) -> str:
        """Create backup copy of file"""
        try:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f'Source file not found: {file_path}')
            
            backup_dir = os.path.join(self.storage_path, 'backups')
            os.makedirs(backup_dir, exist_ok=True)
            
            filename = os.path.basename(file_path)
            name, ext = os.path.splitext(filename)
            backup_filename = f"{name}_backup_{uuid.uuid4().hex[:8]}{ext}"
            backup_path = os.path.join(backup_dir, backup_filename)
            
            # Copy file
            with open(file_path, 'rb') as src, open(backup_path, 'wb') as dst:
                dst.write(src.read())
            
            self.logger.info(f'Backup created: {backup_path}')
            return backup_path
            
        except Exception as e:
            self.logger.error(f'Backup creation error: {str(e)}')
            raise
    
    def cleanup_old_files(self, max_age_days: int = 30) -> int:
        """Clean up files older than specified days"""
        try:
            import time
            
            current_time = time.time()
            max_age_seconds = max_age_days * 24 * 60 * 60
            deleted_count = 0
            
            for root, dirs, files in os.walk(self.storage_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    
                    try:
                        file_age = current_time - os.path.getctime(file_path)
                        
                        if file_age > max_age_seconds:
                            os.remove(file_path)
                            deleted_count += 1
                            self.logger.info(f'Cleaned up old file: {file_path}')
                            
                    except Exception as e:
                        self.logger.warning(f'Failed to clean up file {file_path}: {str(e)}')
            
            self.logger.info(f'Cleanup completed: {deleted_count} files removed')
            return deleted_count
            
        except Exception as e:
            self.logger.error(f'Cleanup error: {str(e)}')
            return 0
    
    def _format_file_size(self, bytes_size: int) -> str:
        """Format file size in human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes_size < 1024:
                return f"{bytes_size:.1f} {unit}"
            bytes_size /= 1024
        return f"{bytes_size:.1f} TB"
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage directory statistics"""
        try:
            total_size = 0
            file_count = 0
            type_counts = {}
            
            for root, dirs, files in os.walk(self.storage_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    
                    try:
                        size = os.path.getsize(file_path)
                        total_size += size
                        file_count += 1
                        
                        file_type = self.get_file_type(file)
                        type_counts[file_type] = type_counts.get(file_type, 0) + 1
                        
                    except Exception:
                        continue
            
            return {
                'total_size': total_size,
                'total_size_formatted': self._format_file_size(total_size),
                'file_count': file_count,
                'type_breakdown': type_counts,
                'storage_path': self.storage_path
            }
            
        except Exception as e:
            self.logger.error(f'Storage stats error: {str(e)}')
            return {
                'total_size': 0,
                'total_size_formatted': '0 B',
                'file_count': 0,
                'type_breakdown': {},
                'storage_path': self.storage_path,
                'error': str(e)
            }
