import json
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path
from pydantic import BaseModel
import pandas as pd

from evidently import Report
from evidently.presets import DataSummaryPreset

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
    timestamp: datetime
    prompt_length: int
    response_length: int
    response_time_ms: float
    tokens_used: int
    sentiment: str
    entity_count: int
    complexity_score: float

# =================================================================
# LLM Audit Service
# =================================================================

class LLMMonitor:
    """Monitor LLM chat features and detect drift using Evidently AI"""

    def __init__(self, storage_path: str = "/app/evidently/llm_data"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.prompts_file = self.storage_path / "prompts.jsonl"
        self.features_file = self.storage_path / "features.jsonl"
        self.reports_dir = self.storage_path / "reports"
        self.reports_dir.mkdir(exist_ok=True)
        logger.info(f"📊 LLMMonitor initialized with storage path: {self.storage_path}")

    def log_prompt(self, prompt: LLMPrompt) -> None:
        """Log LLM prompt to storage"""
        try:
            with open(self.prompts_file, "a") as f:
                f.write(prompt.model_dump_json() + "\n")
            logger.debug(f"✅ Logged LLM prompt for user_id={prompt.user_id}, session_id={prompt.session_id}")

            # Extract features for monitoring
            self.extract_features(prompt)

        except Exception as e:
            logger.error(f"❌ Failed to log LLM prompt: {e}")

    def extract_features(self, prompt: LLMPrompt) -> Optional[LLMFeatureSet]:
        """Extract features from LLM interaction for monitoring"""
        try:
            response_time = prompt.response_time_ms
            prompt_length = len(prompt.prompt.split())
            response_length = len(prompt.response.split())
            sentiment = self._analyze_sentiment(prompt.response)  # Sentiment analysis
            entity_count = len([w for w in prompt.response.split() if w[0].isupper()])  # Entity recognition/extraction
            complexity = min(1.0, len(prompt.response) / 500.0)  # Complexity score (0-1)

            features = LLMFeatureSet(
                timestamp=prompt.timestamp,
                prompt_length=prompt_length,
                response_length=response_length,
                response_time_ms=response_time,
                tokens_used=prompt.tokens_used,
                sentiment=sentiment,
                entity_count=entity_count,
                complexity_score=complexity
            )

            with open(self.features_file, "a") as f:
                f.write(features.model_dump_json() + "\n")

            logger.debug(f"✅ Extracted features for user_id={prompt.user_id}, session_id={prompt.session_id}")
            return features
        
        except Exception as e:
            logger.error(f"❌ Failed to extract features from LLM prompt: {e}")
            raise

    def _analyze_sentiment(self, text: str) -> str:
        """Sentiment analysis placeholder - replace with actual model or library"""
        try:
            from textblob import TextBlob
            blob = TextBlob(text)
            polarity = blob.sentiment.polarity

            # Create logic statement
            if polarity > 0.1:
                return "positive"
            elif polarity < -0.1:
                return "negative"
            else:
                return "neutral"
        except:
            return "neutral"
        
    def _load_features_df(self) -> pd.DataFrame:
        """Load features from JSON file"""
        try:
            if not self.features_file.exists():
                return pd.DataFrame()  # Return empty DataFrame if file doesn't exist

            data = []
            with open(self.features_file, "r") as f:
                for line in f:
                    if line.strip():
                        data.append(json.loads(line)) # Inserting data as dicts to preserve types

            if not data:
                return pd.DataFrame()  # Return empty DataFrame if no data

            df = pd.DataFrame(data)  # Convert to DataFrame
            if "timestamp" in df.columns:
                df["timestamp"] = pd.to_datetime(df["timestamp"])
            return df
        
        except Exception as e:
            logger.error(f"❌ Failed to load features data: {e}")
            return pd.DataFrame()
    
    def generate_report(self) -> Optional[str]:
        """Generate Evidently AI report for LLM feature drift detection"""
        try:
            if not self.features_file.exists():
                logger.warning("⚠️ No features data available to generate report.")
                return None
            
            # Load data from storage
            df = self._load_features_df()

            if df.empty or len(df) < 2:
                logger.warning("⚠️ Not enough data to generate report (need at least 2 records).")
                return None
            
            # Split reference (first 50%) and current (last 50%) datasets
            split_idx = max(1, len(df) // 2)  # Ensure at least one record in reference
            reference_df = df.iloc[:split_idx].drop(columns=['timestamp', 'sentiment'], errors='ignore') # First 50% as reference
            current_df = df.iloc[split_idx:].drop(columns=['timestamp', 'sentiment'], errors='ignore') # Last 50% as current

            # Create Evidently report
            report = Report(metrics=[DataSummaryPreset()])
            report.run(
                reference_data=reference_df,
                current_data=current_df,
                column_mapping=None
            )

            # Save report to HTML file
            report_path = self.reports_dir / f"llm_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
            report.save_html(str)(report_path)

            logger.info(f"✅ Generated LLM report at {report_path}")
            return str(report_path)
        
        except Exception as e:
            logger.error(f"❌ Failed to generate LLM report: {e}")
            return None
        
        
    def get_statistics(self) -> Dict[str, Any]:
        """Get LLM Statistics"""
        try:
            df = self._load_features_df()

            if df.empty:
                return {"message": "No data available"}
            
            numeric_cols = ["prompt_length", "response_length", "response_time_ms", "tokens_used", "complexity_score"]
            
            # statistics
            stats = {
                "total_interactions": len(df),
                "avg_response_time_ms": round(float(df["response_time_ms"].mean()), 2),
                "avg_tokens_used": round(float(df["tokens_used"].mean()), 2),
                "avg_prompt_length": round(float(df["prompt_length"].mean()), 2),
                "avg_response_length": round(float(df["response_length"].mean()), 2),
                "avg_complexity_score": round(float(df["complexity_score"].mean()), 2),
                "sentiment_distribution": df["sentiment"].value_counts().to_dict(),
                "prompt_score_correlation": df[numeric_cols].corr().mean().round(4).to_dict(),
            }

            return stats
        
        except Exception as e:
            logger.error(f"❌ Failed to compute LLM statistics: {e}")
            return {"error": str(e)}
        
# LLM Singleton
llm_monitor = LLMMonitor()