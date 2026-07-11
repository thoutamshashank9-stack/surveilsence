from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Tuple

class BehavioralClassifierBase(ABC):
    """
    Abstract base class for retail loss prevention and security behavioral anomaly classifiers.
    """
    @abstractmethod
    def update(
        self,
        track_id: int,
        centroid: Tuple[float, float],
        frame_timestamp: float,
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """
        Process the current tracking state update for a track ID.
        Returns:
            Optional[Dict[str, Any]]: Anomaly event dictionary if detected, else None.
        """
        pass

    @abstractmethod
    def reset(self) -> None:
        """Resets the internal tracking states."""
        pass

    @abstractmethod
    def cleanup(self, max_age_seconds: float = 60.0) -> None:
        """Cleans up internal cache for inactive tracks to prevent memory leaks."""
        pass
