from evidently import metrics
import json
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path
from pydantic import BaseModel
import pandas as pd
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

try:
    from evidently import Report
    from evidently.metrics import (
        ValueDrift,
        MeanValue,
        MissingValueCount,
        QuantileValue,
        StdValue,
        DriftedColumnsCount,
    )
    EVIDENTLY_AVAILABLE = True
except ImportError:
    EVIDENTLY_AVAILABLE = False

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
            sentiment = self._analyze_sentiment(prompt.response)
            entity_count = len([w for w in prompt.response.split() if w[0].isupper()])
            complexity = min(1.0, len(prompt.response) / 500.0)

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
                return pd.DataFrame()

            data = []
            with open(self.features_file, "r") as f:
                for line in f:
                    if line.strip():
                        data.append(json.loads(line))

            if not data:
                return pd.DataFrame()

            df = pd.DataFrame(data)
            if "timestamp" in df.columns:
                df["timestamp"] = pd.to_datetime(df["timestamp"])
            return df
        
        except Exception as e:
            logger.error(f"❌ Failed to load features data: {e}")
            return pd.DataFrame()
    
    async def generate_report_from_db(self, db: AsyncSession, days: int = 365) -> Optional[str]:
        """
        Generate Evidently AI report from PostgreSQL LLM interactions.
        For Evidently 0.7.21 - using ColumnSummaryMetric
        """
        try:
            # Get data from PostgreSQL
            query = text(f"""
                SELECT 
                    created_at as timestamp,
                    user_id,
                    session_id,
                    prompt,
                    response,
                    response_time_ms,
                    tokens_used,
                    cost
                FROM analytics.llm_interactions
                WHERE created_at >= NOW() - INTERVAL '{days} DAY'
                ORDER BY created_at DESC
            """)
            
            result = await db.execute(query)
            rows = result.fetchall()
            
            logger.info(f"📊 Found {len(rows) if rows else 0} records for report generation")
            
            if not rows or len(rows) < 2:
                logger.warning(f"⚠️ Not enough data to generate report (need at least 2 records, have {len(rows) if rows else 0})")
                return None
            
            # Convert to DataFrame
            data = []
            for row in rows:
                prompt_text = row[3] if row[3] else ""
                response_text = row[4] if row[4] else ""
                
                prompt_length = len(prompt_text.split()) if prompt_text else 0
                response_length = len(response_text.split()) if response_text else 0
                
                data.append({
                    "timestamp": row[0],
                    "response_time_ms": float(row[5]) if row[5] else 0,
                    "tokens_used": int(row[6]) if row[6] else 0,
                    "cost": float(row[7]) if row[7] else 0,
                    "prompt_length": prompt_length,
                    "response_length": response_length,
                    "user_id": str(row[1]) if row[1] else "unknown",
                    "session_id": str(row[2]) if row[2] else "unknown"
                })
            
            df = pd.DataFrame(data)
            
            # Ensure numeric columns are properly typed
            numeric_cols = ['response_time_ms', 'tokens_used', 'cost', 'prompt_length', 'response_length']
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
            logger.info(f"📊 Prepared DataFrame with {len(df)} records")
            logger.info(f"📊 Columns: {df.columns.tolist()}")
            
            # Split into reference and current
            split_idx = max(1, len(df) // 2)
            reference_df = df.iloc[:split_idx].copy()
            current_df = df.iloc[split_idx:].copy()
            
            # Drop non-numeric columns for drift detection
            drop_cols = ['timestamp', 'user_id', 'session_id']
            reference_df = reference_df.drop(columns=[c for c in drop_cols if c in reference_df.columns], errors='ignore')
            current_df = current_df.drop(columns=[c for c in drop_cols if c in current_df.columns], errors='ignore')

            if not EVIDENTLY_AVAILABLE:
                logger.warning("⚠️ Evidently not available, falling back to simple report")
                return await self._generate_simple_report_from_db(db, days)
            
            # Create report with available metrics for version 0.7.21
            report = Report(metrics=[
                DriftedColumnsCount(),
                MeanValue(column="response_time_ms"),
                MeanValue(column="tokens_used"),
                MeanValue(column="prompt_length"),
                StdValue(column="response_time_ms"),
                StdValue(column="tokens_used"),
                QuantileValue(column="response_time_ms", quantile=0.95),
                MissingValueCount(column="response_time_ms"),
                MissingValueCount(column="tokens_used"),
                ValueDrift(column="response_time_ms"),
                ValueDrift(column="tokens_used"),
            ])

            report.run(
                reference_data=reference_df,
                current_data=current_df
            )
            
            # Save report — evidently 0.7.21 stores no accessible results post-run
            # Build HTML directly from DataFrame stats
            timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
            report_path = self.reports_dir / f"llm_report_{timestamp_str}.html"

            try:
                html_content = self._generate_evidently_html(df, reference_df, current_df)
                with open(report_path, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                logger.info(f"✅ Saved evidently report as HTML at {report_path}")
            except Exception as e:
                logger.error(f"❌ Failed to save report: {e}")
                return await self._generate_simple_report_from_db(db, days)

            logger.info(f"✅ Generated LLM report at {report_path}")
            return str(report_path)

        except ImportError as e:
            logger.error(f"❌ Evidently import error: {e}")
            return await self._generate_simple_report_from_db(db, days)

        except Exception as e:
            logger.error(f"❌ Failed to generate LLM report from DB: {e}")
            return await self._generate_simple_report_from_db(db, days)    
    
    async def _generate_simple_report_from_db(self, db: AsyncSession, days: int = 365) -> Optional[str]:
        """Generate simple HTML report without Evidently"""
        try:
            query = text(f"""
                SELECT 
                    created_at as timestamp,
                    user_id,
                    response_time_ms,
                    tokens_used,
                    prompt,
                    response
                FROM analytics.llm_interactions
                WHERE created_at >= NOW() - INTERVAL '{days} DAY'
                ORDER BY created_at DESC
            """)
            
            result = await db.execute(query)
            rows = result.fetchall()
            
            if not rows:
                return None
            
            data = []
            for row in rows:
                data.append({
                    "timestamp": row[0],
                    "user_id": str(row[1]) if row[1] else "unknown",
                    "response_time_ms": float(row[2]) if row[2] else 0,
                    "tokens_used": int(row[3]) if row[3] else 0,
                    "prompt": (row[4] or "")[:100],
                    "response": (row[5] or "")[:100]
                })
            
            df = pd.DataFrame(data)
            html_content = self._generate_evidently_html(df, [])
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            report_path = self.reports_dir / f"llm_simple_report_{timestamp}.html"
            
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            logger.info(f"✅ Generated simple report at {report_path}")
            return str(report_path)
            
        except Exception as e:
            logger.error(f"❌ Failed to generate simple report: {e}")
            return None
    
    def _generate_evidently_html(self, df: pd.DataFrame, reference_df: pd.DataFrame, current_df: pd.DataFrame) -> str:
        """Generate HTML report comparing reference vs current data (evidently 0.7.21 compatible)"""
        
        def safe_mean(d, col):
            return round(float(d[col].mean()), 2) if col in d.columns and len(d) > 0 else 0.0

        ref_stats = {
            "count": len(reference_df),
            "avg_response_time": safe_mean(reference_df, "response_time_ms"),
            "avg_tokens": safe_mean(reference_df, "tokens_used"),
            "avg_prompt_length": safe_mean(reference_df, "prompt_length"),
        }
        cur_stats = {
            "count": len(current_df),
            "avg_response_time": safe_mean(current_df, "response_time_ms"),
            "avg_tokens": safe_mean(current_df, "tokens_used"),
            "avg_prompt_length": safe_mean(current_df, "prompt_length"),
        }

        def drift_badge(ref_val, cur_val):
            if ref_val == 0:
                return "<span style='color:gray'>N/A</span>"
            pct = abs(cur_val - ref_val) / ref_val * 100
            color = "green" if pct < 10 else "orange" if pct < 30 else "red"
            return f"<span style='color:{color}'>{'↑' if cur_val > ref_val else '↓'} {pct:.1f}%</span>"
        return f"""<!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>LLM Monitoring Report</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }}
                    .container {{ max-width: 1100px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                    h1 {{ color: #333; border-bottom: 2px solid #4CAF50; padding-bottom: 10px; }}
                    h2 {{ color: #555; margin-top: 30px; }}
                    table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
                    th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
                    th {{ background: #4CAF50; color: white; }}
                    tr:hover {{ background: #f9f9f9; }}
                    .badge {{ padding: 3px 8px; border-radius: 4px; font-size: 12px; }}
                </style>
            </head>
            <body>
            <div class="container">
                <h1>📊 LLM Monitoring Report</h1>
                <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} &nbsp;|&nbsp; Total records: {len(df)}</p>
                <h2>📈 Reference vs Current Comparison</h2>
                <table>
                    <thead><tr><th>Metric</th><th>Reference ({ref_stats['count']} records)</th><th>Current ({cur_stats['count']} records)</th><th>Drift</th></tr></thead>
                    <tbody>
                        <tr>
                            <td>Avg Response Time (ms)</td>
                            <td>{ref_stats['avg_response_time']}</td>
                            <td>{cur_stats['avg_response_time']}</td>
                            <td>{drift_badge(ref_stats['avg_response_time'], cur_stats['avg_response_time'])}</td>
                        </tr>
                        <tr>
                            <td>Avg Tokens Used</td>
                            <td>{ref_stats['avg_tokens']}</td>
                            <td>{cur_stats['avg_tokens']}</td>
                            <td>{drift_badge(ref_stats['avg_tokens'], cur_stats['avg_tokens'])}</td>
                        </tr>
                        <tr>
                            <td>Avg Prompt Length</td>
                            <td>{ref_stats['avg_prompt_length']}</td>
                            <td>{cur_stats['avg_prompt_length']}</td>
                            <td>{drift_badge(ref_stats['avg_prompt_length'], cur_stats['avg_prompt_length'])}</td>
                        </tr>
                    </tbody>
                </table>
            </div>
            </body>
            </html>"""

        
    def get_report_list(self) -> List[Dict[str, Any]]:
        """Get list of all generated reports"""
        try:
            reports = []
            for file in self.reports_dir.glob("*.html"):
                reports.append({
                    "name": file.name,
                    "path": str(file),
                    "size": file.stat().st_size,
                    "modified": datetime.fromtimestamp(file.stat().st_mtime).isoformat()
                })
            reports.sort(key=lambda x: x["modified"], reverse=True)
            return reports
        except Exception as e:
            logger.error(f"❌ Failed to list reports: {e}")
            return []
        
    def get_statistics(self) -> Dict[str, Any]:
        """Get LLM Statistics"""
        try:
            df = self._load_features_df()

            if df.empty:
                return {"message": "No data available"}
            
            numeric_cols = ["prompt_length", "response_length", "response_time_ms", "tokens_used", "complexity_score"]
            
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