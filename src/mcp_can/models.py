from dataclasses import dataclass
from typing import Any, List, Optional


@dataclass
class Frame:
    timestamp: float
    arbitration_id: int
    data: bytes


@dataclass
class FrameView:
    timestamp: float
    arbitration_id_hex: str
    data: List[int]
    signal_value: Optional[Any] = None


def frame_to_view(frame: Frame, *, signal_value: Optional[Any] = None) -> FrameView:
    return FrameView(
        timestamp=frame.timestamp,
        arbitration_id_hex=hex(frame.arbitration_id),
        data=list(frame.data),
        signal_value=signal_value,
    )

