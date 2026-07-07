from enum import Enum

class CameraStatus(str, Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    CONNECTING = "connecting"
    ERROR = "error"

class CameraType(str, Enum):
    RTSP = "rtsp"
    ONVIF = "onvif"
    USB = "usb"
    FILE = "file"
    HTTP = "http"
    MOCK = "mock"

class StreamType(str, Enum):
    MAIN = "main"
    SUB = "sub"
    THIRD = "third"

class AlertSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"

class AlertStatus(str, Enum):
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"

class EventType(str, Enum):
    DETECTION = "detection"
    TRACKING = "tracking"
    TRACK_START = "track_start"
    TRACK_END = "track_end"
    ZONE_ENTRY = "zone_entry"
    ZONE_EXIT = "zone_exit"
    LINE_CROSS = "line_cross"
    DWELL_START = "dwell_start"
    DWELL_END = "dwell_end"
    INTRUSION = "intrusion"
    LOITERING = "loitering"
    NO_PURCHASE_EXIT = "no_purchase_exit"
    ALERT = "alert"
    CAMERA_STATUS = "camera_status"

class InferenceBackendType(str, Enum):
    CPU = "cpu"
    CUDA = "cuda"
    DIRECTML = "directml"
    OPENVINO = "openvino"
    TENSORRT = "tensorrt"

class ZoneType(str, Enum):
    POLYGON = "polygon"
    LINE = "line"
