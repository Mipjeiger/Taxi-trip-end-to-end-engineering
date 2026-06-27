import logging
import time
from typing import Dict, Any, Optional
from datetime import datetime
import pandas as pd
import numpy as np

"""
ML Model Monitoring Service
Tracks model performance, success rates, and prediction quality
"""

from app.core.ml_metrics import (
    ML_PREDICTION_COUNTER,
    ML_PREDICTION_ERRORS,
    ML_PREDICTION_LATENCY,
    ML_PREDICTION_VALUES,
    ML_MODEL_CONFIDENCE,
    ML_MODEL_LOAD_STATUS,
    ML_ACTIVE_PREDICTIONS,
    ML_MODEL_INFO,
    ML_CACHE_HITS,
    ML_FEATURE_EXTRACTION_TIME,
    ML_MODEL_PERFORMANCE,
    MLPredictionMetrics,
    record_prediction_values,
    record_cache_hit,
    record_feature_extraction_time,
    set_model_loaded,
    set_model_info,
    set_model_performance
)

logger = logging.getLogger(__name__)

class MLMonitor:
    """Monitor ML model performance and metrics"""

    def __init__(self):
        self.prediction_history = []
        self.max_history = 1000
        self.model_stats = {}

    def track_prediction(
        self,
        model_type: str,
        vehicle_type: str,
        endpoint: str,
        success: bool,
        error_type: Optional[str] = None,
        latency: float = 0.0,
        ctat_pred: Optional[float] = None,
        vtat_pred: Optional[float] = None,
        confidence: Optional[str] = None
    ):
        """Track a single prediction"""
        status = "success" if success else "error"

        # Increment counters
        ML_PREDICTION_COUNTER.labels(
            model_type=model_type,
            status=status,
            vehicle_type=vehicle_type,
            endpoint=endpoint
        ).inc()

        if not success and error_type:
            ML_PREDICTION_ERRORS.labels(
                model_type=model_type,
                error_type=error_type,
                vehicle_type=vehicle_type
            ).inc()

        # Record latency
        if latency > 0:
            ML_PREDICTION_LATENCY.labels(
                model_type=model_type,
                status=status
            ).observe(latency)

        # Record prediction values
        if ctat_pred:
            record_prediction_values(model_type, "ctat", ctat_pred)
        if vtat_pred:
            record_prediction_values(model_type, "vtat", vtat_pred)

        # Record model confidence
        if confidence:
            confidence_score = 0.8 if confidence == "high" else 0.5 if confidence == "medium" else 0.3
            ML_MODEL_CONFIDENCE.labels(
                model_type=model_type,
                vehicle_type=vehicle_type
            ).set(confidence_score)

        # Store in history
        self.prediction_history.append({
            "timestamp": datetime.now().isoformat(),
            "model_type": model_type,
            "vehicle_type": vehicle_type,
            "endpoint": endpoint,
            "success": success,
            "error_type": error_type,
            "latency": latency,
            "ctat_pred": ctat_pred,
            "vtat_pred": vtat_pred,
            "confidence": confidence
        })

        # Trim history
        if len(self.prediction_history) > self.max_history:
            self.prediction_history = self.prediction_history[-self.max_history:]

    def track_cache(self, is_hit: bool):
        """Track cache hit or miss"""
        cache_type = "hit" if is_hit else "miss"
        ML_CACHE_HITS.labels(cache_type=cache_type).inc()

    def track_feature_extraction(self, duration: float):
        """
        Track feature extraction time
        """
        ML_FEATURE_EXTRACTION_TIME.observe(duration)

    def get_prediction_stats(self, hours: int = 24) -> Dict[str, Any]:
        """Get prediction statistics for the last N hours"""
        cutoff = datetime.now().timestamps() - (hours * 3600)

        recent = [
            p for p in self.prediction_history
            if datetime.fromisoformat(p["timestamp"]).timestamp() > cutoff
        ]

        if not recent:
            return {
                "message": "No recent predictions found"
            }
        
        total = len(recent)
        successful = sum(1 for p in recent if p["success"])
        failed = total - successful

        avg_latency = sum(p["latency"] for p in recent) / total if total > 0 else 0

        # Group by model type
        by_model = {}
        for p in recent:
            model = p["model_type"]
            
            if model not in by_model:
                by_model[model] = {
                    "total": 0,
                    "successful": 0,
                    "failed": 0,
                    "latency": []
                }
                by_model[model]["total"] += 1

                if p["success"]:
                    by_model[model]["successful"] += 1
                else:
                    by_model[model]["failed"] += 1
                by_model[model]["latency"].append(p["latency"])

        # Calculate averages
        for model in by_model:
            by_model[model]["avg_latency"] = sum(by_model[model]["latency"]) / len(by_model[model]["latency"]) if by_model[model]["latency"] else 0
            by_model[model]["success_rate"] = (by_model[model]["successful"] / by_model[model]["total"]) * 100 if by_model[model]["total"] > 0 else 0

        return {
            "period_hours": hours,
            "total_predictions": total,
            "successful": successful,
            "failed": failed,
            "success_rate": (successful / total * 100) if total > 0 else 0,
            "avg_latency_seconds": avg_latency,
            "by_model": by_model
        }
    
    def get_error_stats(self, hours: int = 24) -> Dict[str, Any]:
        """Get error statistics for the last N hours"""
        cutoff = datetime.now().timestamp() - (hours * 3600)

        errors = [
            p for p in self.prediction_history
            if not p["success"] and datetime.fromisoformat(p["timestamp"]).timestamp() > cutoff
        ]

        if not errors:
            return {
                "message": "No recent errors found"
            }
        
        error_counts = {}
        for p in errors:
            error_type = p["error_type"] or "Unknown"
            error_counts[error_type] = error_counts.get(error_type, 0) + 1


        return {
            "period_hours": hours,
            "total_errors": len(errors),
            "by_error_type": error_counts,
            "error_rate": (len(errors) / len(self.prediction_history)) * 100 if self.prediction_history else 0
        }
    
    def calculate_model_performance(
        self,
        actual_values: pd.Series,
        predicted_values: pd.Series,
        model_type: str
    ):
        """Calculate and record model performance metrics"""
        try:
            # Mean Absolute Error
            mae = np.mean(np.abs(actual_values - predicted_values))
            set_model_performance(model_type, "mae", mae)

            # Root Mean Squared Error
            rmse = np.sqrt(np.mean((actual_values - predicted_values) ** 2))
            set_model_performance(model_type, "rmse", rmse)

            # R2 Score
            ss_res = np.sum((actual_values - predicted_values) ** 2)
            ss_tot = np.sum((actual_values - np.mean(actual_values)) ** 2)
            r2 = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
            set_model_performance(model_type, "r2", r2)

            # Mean Absolute Percentage Error
            mape = np.mean(np.abs((actual_values - predicted_values) / actual_values)) * 100
            set_model_performance(model_type, "mape", mape)

            logger.info(f"✅ Model performance recorded for {model_type}: MAE={mae:.2f}, RMSE={rmse:.2f}, R²={r2:.2f}, MAPE={mape:.1f}%")

        except Exception as e:
            logger.error(f"❌ Error calculating model performance for {model_type}: {e}")

# Singleton calls
ml_monitor = MLMonitor()