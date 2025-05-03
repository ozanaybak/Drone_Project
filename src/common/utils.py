import json
import time
import logging
from typing import Any

logger = logging.getLogger(__name__)

def timestamp() -> int:
    """
    Return the current time as a UNIX timestamp (integer seconds).
    """
    return int(time.time())

def load_json(path: str) -> Any:
    """
    Load and return the JSON content from the specified file path.
    Raises FileNotFoundError or JSONDecodeError on failure, which are logged.
    """
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load JSON from {path}: {e}")
        raise

def dump_json(path: str, obj: Any) -> None:
    """
    Dump the given object as pretty-printed JSON to the specified file path.
    Raises IOError on failure, which is logged.
    """
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(obj, f, indent=2, ensure_ascii=False)
        logger.debug(f"JSON written to {path}")
    except Exception as e:
        logger.error(f"Failed to write JSON to {path}: {e}")
        raise