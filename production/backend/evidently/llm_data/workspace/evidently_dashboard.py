from evidently.metrics import DriftedColumnsCount
from sqlalchemy import column
import pandas as pd
import json
import os
from datetime import datetime
from evidently.report import Report
from evidently.metrics import MeanValue, ValueDrift, MissingValueCount
from evidently.ui.workspace import Workspace

# 1. Setup local workspace path (relative to the script directory)
# Resolves to: production/backend/evidently/llm_data/workspace
WORKSPACE_PATH = "../workspace" 
FEATURES_FILE = "../features.jsonl"

def load_reference_from_jsonl(features_file_path: str) -> pd.DataFrame:
    """Loads historical features logged by the production monitor to use as a baseline"""
    if not os.path.exists(features_file_path):
        print(f"⚠️ Features file not found at: {features_file_path}")
        return pd.DataFrame()

    data = []
    with open(features_file_path, "r") as f:
        for line in f:
            if line.strip():
                data.append(json.loads(line))

    df = pd.DataFrame(data)
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"])

    return df

# Usage
if __name__ == "__main__":
    # Load production baseline features
    df = load_reference_from_jsonl(FEATURES_FILE)

    if df.empty or len(df) < 4:
        print("❌ Not enough reference data to compute monitoring metrics (need at least 4 records).")
    else:
        # Split features into Reference vs Current
        split_idx = len(df) // 2
        ref_df = df.iloc[:split_idx].copy()
        cur_df = df.iloc[split_idx:].copy()

        # Clean non-numeric columns for drift analysis
        drop_cols = ['timestamp', 'sentiment']
        ref_df = ref_df.drop(columns=[c for c in drop_cols if c in ref_df.columns], errors='ignore')
        cur_df = cur_df.drop(columns=[c for c in drop_cols if c in cur_df.columns], errors='ignore')

        # Intialized workspace & project
        ws = Workspace.create(WORKSPACE_PATH)
        project = None
        for p in ws.list_projects():
            if p.name == "LLM Monitoring":
                project = p
                break

        if not project:
            project= ws.create_project("LLM Monitoring")
            project.description = "Dashboard for LLM performance & data drift monitoring"
            project.save()

        # Run report comparing reference vs current production logs
        report = Report(metrics=[
            MeanValue(column="response_time_ms"),
            ValueDrift(column="response_time_ms"),
            MeanValue(column="tokens_used"),
            ValueDrift(column="tokens_used"),
            MissingValueCount(column="response_time_ms"),
            MissingValueCount(column="tokens_used"),
            #DriftedColumnsCount(),
            #MeanValue(column="sentiment"),
            #ValueDrift(column="sentiment"),
            #MeanValue(column="entity_count"),
            #ValueDrift(column="entity_count"),
            #MeanValue(column="complexity_score"),
            #ValueDrift(column="complexity_score"),
        ])

        report.run(reference_data=ref_df, current_data=cur_df)

        # Add to dashboard
        ws.add_report(project.id, report)
        print(f"✅ Dashboard updated with a new snapshot!")
        print(f"Launch the dashboard locally via:")
        print(f"  evidently ui --workspace {os.path.abspath(WORKSPACE_PATH)}")