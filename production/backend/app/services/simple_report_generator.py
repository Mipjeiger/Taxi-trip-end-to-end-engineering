import json
import pandas as pd
from datetime import datetime
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class SimpleReportGenerator:
    """Generate simple HTML reports without Evidently"""

    @staticmethod
    def generate_stats_report(df: pd.DataFrame, output_path: Path) -> str:
        """Generate simple statistics report"""
        try:
            stats = {
                "total_interactions": len(df),
                "avg_response_time_ms": df['response_time_ms'].mean() if 'response_time_ms' in df else 0,
                "avg_tokens_used": df['tokens_used'].mean() if 'tokens_used' in df else 0,
                "avg_prompt_length": df['prompt_length'].mean() if 'prompt_length' in df else 0,
                "avg_response_length": df['response_length'].mean() if 'response_length' in df else 0
            }

            # Generate HTML
            html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>LLM Interaction Report</title>   
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }}
                    .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                    h1 {{ color: #333; border-bottom: 2px solid #4CAF50; padding-bottom: 10px; }}
                    .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 20px 0; }}
                    .stat-card {{ background: #f9f9f9; padding: 15px; border-radius: 8px; border-left: 4px solid #4CAF50; }}
                    .stat-value {{ font-size: 24px; font-weight: bold; color: #333; }}
                    .stat-label {{ color: #666; font-size: 14px; }}
                    table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
                    th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
                    th {{ background: #4CAF50; color: white; }}
                    tr:hover {{ background: #f5f5f5; }}
                    .timestamp {{ font-size: 12px; color: #999; margin-top: 20px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>📊 LLM Interaction Report</h1>
                    <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                    
                    <div class="stats">
                        <div class="stat-card">
                            <div class="stat-value">{stats['total_interactions']}</div>
                            <div class="stat-label">Total Interactions</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-value">{stats['avg_response_time_ms']:.1f}ms</div>
                            <div class="stat-label">Avg Response Time</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-value">{stats['avg_tokens_used']:.0f}</div>
                            <div class="stat-label">Avg Tokens Used</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-value">{stats['avg_prompt_length']:.0f}</div>
                            <div class="stat-label">Avg Prompt Length</div>
                        </div>
                    </div>
                    
                    <h2>Recent Interactions</h2>
                    <table>
                        <thead>
                            <tr>
                                <th>Timestamp</th>
                                <th>User</th>
                                <th>Tokens</th>
                                <th>Response Time (ms)</th>
                            </tr>
                        </thead>
                        <tbody>
            """

            # Add rows
            for _, row in df.head(20).iterrows():
                html += f"""
                            <tr>
                                <td>{row.get('timestamp', 'N/A')}</td>
                                <td>{row.get('user_id', 'N/A')[:8]}</td>
                                <td>{row.get('tokens_used', 0)}</td>
                                <td>{row.get('response_time_ms', 0):.0f}</td>
                            </tr>
                """

            html += f"""
                        </tbody>
                    </table>
                    <div class="timestamp">Report generated at {datetime.now().isoformat()}</div>
                </div>
            </body>
            </html>
            """

            # Write to file
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html)

            logger.info(f"Report generated successfully at {output_path}")
            return str(output_path)
        
        except Exception as e:
            logger.error(f"Failed to generate report: {e}")
            return None