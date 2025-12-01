# models.py
from datetime import datetime
from bson import ObjectId
from typing import Optional, List, Dict, Any

class DocumentModel:
    """Model for uploaded documents"""
    
    @staticmethod
    def create_document(filename: str, file_type: str, file_size: int, 
                       raw_text: str, extracted_data: List[Dict]) -> Dict:
        return {
            "filename": filename,
            "file_type": file_type,
            "file_size": file_size,
            "raw_text": raw_text,
            "extracted_data": extracted_data,
            "upload_date": datetime.utcnow(),
            "status": "uploaded",
            "metadata": {
                "page_count": len([item for item in extracted_data if 'page' in item]),
                "extraction_methods": list(set([item.get('source', '') for item in extracted_data])),
                "text_length": len(raw_text)
            }
        }

class ProcessingSessionModel:
    """Model for processing sessions"""
    
    @staticmethod
    def create_session(session_id: str, document_id: ObjectId, 
                      filename: str, file_path: str = None) -> Dict:
        return {
            "session_id": session_id,
            "document_id": document_id,
            "filename": filename,
            "file_path": file_path,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "status": "active",
            "processing_steps": [],
            "repeat_count": 0,
            "results_count": 0
        }
    
    @staticmethod
    def add_processing_step(step_name: str, status: str, 
                           data: Dict = None) -> Dict:
        return {
            "step_name": step_name,
            "status": status,
            "timestamp": datetime.utcnow(),
            "data": data or {}
        }

class ProcessedResultModel:
    """Model for AI-processed results"""
    
    @staticmethod
    def create_result(document_id: ObjectId, session_id: str,
                     process_name: str, data: Dict) -> Dict:
        return {
            "document_id": document_id,
            "session_id": session_id,
            "process_name": process_name,
            "description": data.get("Description", ""),
            "objective": data.get("Objective", ""),
            "control_design": data.get("Control Designed", data.get("Control Design", "")),
            "risks": data.get("Risks", ""),
            "gaps": data.get("Gaps", ""),
            "recommendation": data.get("Auditor's Recommendation", data.get("Recommendation", "")),
            "raw_data": data,  # Store complete raw data
            "created_at": datetime.utcnow(),
            "n8n_processed": True,
            "excel_exported": False
        }

class AuditLogModel:
    """Model for audit logs"""
    
    @staticmethod
    def create_log(action_type: str, user_id: str = "system", 
                   details: Dict = None, status: str = "success") -> Dict:
        return {
            "action_type": action_type,
            "user_id": user_id,
            "timestamp": datetime.utcnow(),
            "status": status,
            "details": details or {},
            "ip_address": None  # Can be added from request context
        }