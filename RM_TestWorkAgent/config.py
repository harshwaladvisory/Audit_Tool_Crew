import os
from dataclasses import dataclass
from typing import List

@dataclass
class Config:
    """Application configuration"""
    
    MONGODB_URI: str = os.environ.get("MONGODB_URI", "mongodb://localhost:27017/rm_agent")
    
    FILE_STORAGE: str = os.environ.get("FILE_STORAGE", "./storage")
    MAX_CONTENT_LENGTH: int = 16 * 1024 * 1024
    
    CAPITALIZATION_THRESHOLD: float = float(os.environ.get("CAPITALIZATION_THRESHOLD", "5000"))
    MATERIALITY: float = float(os.environ.get("MATERIALITY", "25000"))
    FY_START: str = os.environ.get("FY_START", "2025-07-01")
    FY_END: str = os.environ.get("FY_END", "2026-06-30")
    
    @property
    def ALLOWED_ACCOUNTS(self) -> List[str]:
        accounts = os.environ.get("ALLOWED_ACCOUNTS", "Repair & Maintenance;Repairs;Maintenance")
        return [acc.strip() for acc in accounts.split(";")]
    
    STRATIFICATION_BANDS = [
        (0, 1000),
        (1000, 5000),
        (5000, 10000),
        (10000, 25000),
        (25000, float('inf'))
    ]
    
    SAMPLE_SIZES = {
        (0, 1000): 3,
        (1000, 5000): 5,
        (5000, 10000): 8,
        (10000, 25000): 10,
        (25000, float('inf')): 15
    }
    
    ATTRIBUTE_CHECKS = {
        1: "Amount is calculated correctly and agrees to support",
        2: "Proper initiation/authorization/recording/classification/presentation",
        3: "Documents canceled/marked paid to prevent duplicate payment",
        4: "Disbursement relates to current fiscal year",
        5: "PO approved before service/purchase",
        6: "Internal controls followed (segregation, approvals, documentation)",
        7: "Expenditure correctly accounted for (expense vs capital)"
    }