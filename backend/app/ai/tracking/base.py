from abc import ABC, abstractmethod
import supervision as sv

class TrackerBase(ABC):
    @abstractmethod
    def update(self, detections: sv.Detections) -> sv.Detections:
        pass

    @abstractmethod
    def reset(self) -> None:
        pass
