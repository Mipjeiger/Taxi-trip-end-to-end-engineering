import json
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path
from pydantic import BaseModel
import pandas as pd

from evidently.report import Report
from evidently.metrics import TextOverviewMetrics, TextDescriptorsDriftMetrics
from evidently.test_suite import TestSuite
from evidently.tests import TestColumnShareOfMissingValues

logger = logging.getLogger(__name__)

# =================================================================
# Pydantic Models for LLM Audit
# =================================================================

class LLMPrompt(BaseModel):
    """LLM prompt audit record"""
    timestamp: datetime
    user_id: str
    session_id: str
    prompt: str
    model: str
    temperature: float
    response: str
    response_time_ms: float
    tokens_used: int
    cost: float
    quality_score: Optional[float] = None 

class LLMFeatureSet(BaseModel):
    """Aggregated features for drift detection and monitoring"""
