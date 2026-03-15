import sys
from pathlib import Path

# backend/ をパスに追加（routers.runs と models をインポートできるように）
sys.path.insert(0, str(Path(__file__).parent.parent))
