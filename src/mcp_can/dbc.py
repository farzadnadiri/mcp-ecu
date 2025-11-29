from functools import lru_cache
from typing import Any, Dict

import cantools


@lru_cache(maxsize=4)
def load_dbc(path: str) -> cantools.database.Database:
    return cantools.database.load_file(path)


def decode_frame(
    db: cantools.database.Database,
    arbitration_id: int,
    data: bytes,
) -> Dict[str, Any]:
    message = db.get_message_by_frame_id(arbitration_id)
    return message.decode(data)

