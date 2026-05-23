import logging
import json
import os
from datetime import datetime

class EventLogger:
    """Handles dual logging: JSONL for analytics, Text for system monitoring."""
    def __init__(self, config: dict):
        log_cfg = config.get("logging", {})
        self.jsonl_path = log_cfg.get("jsonl_path", "data/events.jsonl")
        
        # Ensure directories exist
        os.makedirs(os.path.dirname(self.jsonl_path), exist_ok=True)
        
        # Setup standard text logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler(log_cfg.get("text_log_path", "data/system.log"))
            ]
        )
        self.logger = logging.getLogger("EventLogger")

    def log_event(self, event: dict):
        """Append a structured event to the JSONL file."""
        event['ts_iso'] = datetime.utcnow().isoformat()
        with open(self.jsonl_path, 'a') as f:
            f.write(json.dumps(event) + '\n')
        
        # Also print critical security events to console
        if event.get('event_type') in ['person_entered_store', 'person_exited_store', 'no_purchase_exit']:
            self.logger.info(f"EVENT: {event['event_type']} | Track: {event.get('track_id')} | Cam: {event.get('camera_id')}")
