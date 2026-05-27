import os
import sys
import subprocess
from pathlib import Path
from dotenv import load_dotenv

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

# Load environment variables
ENV_PATH = Path(__file__).parent.parent / '.env'
if ENV_PATH.exists():
    print(f"Loading environment variables from: {ENV_PATH}")
else:
    ENV_PATH = Path(__file__).parent.parent.parent / '.env'
    print(f"Fallback to env exists in: {ENV_PATH}")

# Load .env file
load_dotenv(dotenv_path=ENV_PATH)

def main():
    workspace_path = os.getenv("EVIDENTLY_WORKSPACE")
    port = int(os.getenv("EVIDENTLY_PORT"))
    host = os.getenv("EVIDENTLY_HOST")

    # Create workspace directory if it doesn't exist
    Path(workspace_path).mkdir(parents=True, exist_ok=True)

    print(f"🚀 Starting Evidently UI on {host}:{port}")
    print(f"📂 Workspace: {workspace_path}")

    # Create evidently CLI to launch the UI
    try: 
        subprocess.run([
            "evidently", "ui",
            "--workspace", workspace_path,
            "--port", str(port),
            "--host", host
        ], check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Evidently UI exited with error: {e}")
        sys.exit(1)
    except FileNotFoundError:
        print("❌ 'evidently' CLI not found. Is it installed?")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Failed to start Evidently UI: {e}")
        sys.exit(1)

# Entry point
if __name__ == "__main__":
    main()