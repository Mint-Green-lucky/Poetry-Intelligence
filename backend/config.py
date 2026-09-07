# © 2026 BUPT_Mint-Green
# All rights reserved.

import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_DIR / ".env")
DATA_ROOT = PROJECT_DIR / "a_datasets"
THU_DATA_DIR = DATA_ROOT / "Thu-Datasets-master"
FRONTEND_DIR = PROJECT_DIR / "frontend" / "dist"

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

CCPC_TRAIN = THU_DATA_DIR / "CCPC" / "ccpc_train_v1.0.json"
CCPC_VALID = THU_DATA_DIR / "CCPC" / "ccpc_valid_v1.0.json"
CCPC_TEST = THU_DATA_DIR / "CCPC" / "ccpc_test_v1.0.json"
CHINESE_POETRY_ARCHIVE = DATA_ROOT / "chinese-poetry-master.zip"
FSPC_DATA = THU_DATA_DIR / "FSPC" / "FSPC_V1.0.json"
PQED_DATA = THU_DATA_DIR / "PQED" / "PQED_V0.1.json"
CRRD_PINGSHENG = THU_DATA_DIR / "CRRD" / "pingsheng.txt"
CRRD_ZESHENG = THU_DATA_DIR / "CRRD" / "zesheng.txt"
CRRD_PINGSHUI = THU_DATA_DIR / "CRRD" / "pingshui.txt"

# SQLite 保存历史、长期记忆、运行轨迹和作品版本；Chroma 只保存诗词知识向量。
SELF_EVOLVING_DB = PROJECT_DIR / "evolving_logs.db"
EVOLVE_THRESHOLD = int(os.getenv("EVOLVE_THRESHOLD", "50"))
MAX_CCPC_IN_MEMORY = int(os.getenv("MAX_CCPC_IN_MEMORY", "30000"))
CHROMA_DIR = PROJECT_DIR / "storage" / "chroma"
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-zh-v1.5")
VECTOR_RAG_ENABLED = os.getenv("VECTOR_RAG_ENABLED", "true").lower() == "true"
LIVE_API_KEY = os.getenv("LIVE_API_KEY", OPENAI_API_KEY)
LIVE_ENABLED = os.getenv("LIVE_ENABLED", "").lower() == "true" if os.getenv("LIVE_ENABLED") else bool(LIVE_API_KEY)
LIVE_REALTIME_URL = os.getenv("LIVE_REALTIME_URL", "wss://api.openai.com/v1/realtime")
LIVE_MODEL = os.getenv("LIVE_MODEL", "gpt-4o-realtime-preview")
LIVE_VOICE = os.getenv("LIVE_VOICE", "alloy")
MAX_HISTORY = int(os.getenv("MAX_HISTORY", "8"))
EVOLUTION_MIN_DELTA = float(os.getenv("EVOLUTION_MIN_DELTA", "0.02"))
EVOLUTION_ROLLBACK_WINDOW = int(os.getenv("EVOLUTION_ROLLBACK_WINDOW", "10"))

# MCP（Model Context Protocol）默认关闭：未设置 MCP_ENABLED=true 或未配置
# mcp_servers.json 时，不会连接任何外部 Server，也不会向工具目录新增条目。
MCP_ENABLED = os.getenv("MCP_ENABLED", "false").lower() == "true"
MCP_SERVERS_CONFIG = PROJECT_DIR / "mcp_servers.json"
MCP_CALL_TIMEOUT = float(os.getenv("MCP_CALL_TIMEOUT", "15"))
