from typing import Optional, Any

class AppError(Exception):
    status_code: int = 500
    detail: str = "Internal server error"
    error_code: str = "INTERNAL_SERVER_ERROR"

    def __init__(self, detail: Optional[str] = None, status_code: Optional[int] = None, error_code: Optional[str] = None):
        if detail:
            self.detail = detail
        if status_code is not None:
            self.status_code = status_code
        if error_code:
            self.error_code = error_code
        super().__init__(self.detail)

class CameraError(AppError):
    status_code: int = 400
    detail: str = "Camera operation failed"
    error_code: str = "CAMERA_ERROR"

class InferenceError(AppError):
    status_code: int = 500
    detail: str = "Inference execution failed"
    error_code: str = "INFERENCE_ERROR"

class TrackingError(AppError):
    status_code: int = 500
    detail: str = "Object tracking failed"
    error_code: str = "TRACKING_ERROR"

class AlertError(AppError):
    status_code: int = 400
    detail: str = "Alert configuration or processing failed"
    error_code: str = "ALERT_ERROR"

class ConfigError(AppError):
    status_code: int = 400
    detail: str = "Invalid configuration"
    error_code: str = "CONFIG_ERROR"

class StorageError(AppError):
    status_code: int = 500
    detail: str = "Database or storage operation failed"
    error_code: str = "STORAGE_ERROR"

class AuthError(AppError):
    status_code: int = 401
    detail: str = "Authentication failed"
    error_code: str = "AUTH_ERROR"
