import cv2
import time
import yaml
import logging
import signal
import sys
from pathlib import Path

# Import local modules
from camera_manager import CameraManager
from detector import get_detector
from tracker import ObjectTracker
from zone_engine import ZoneEngine
from event_engine import EventEngine
from logger import EventLogger
from db_manager import DBManager

logger = logging.getLogger(__name__)

class Pipeline:
    def __init__(self, config_path: str = "../config.yaml"):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)

        # Initialize Components
        self.logger = EventLogger(self.config)
        self.db = DBManager(self.config)
        self.camera_manager = CameraManager(self.config)
        self.detector = get_detector(self.config)
        self.tracker = ObjectTracker(self.config)
        
        # We will initialize ZoneEngine and EventEngine per-camera dynamically 
        # because zones are specific to each camera's resolution.
        self.zone_engines = {}
        self.event_engines = {}
        
        self.running = False

    def start(self):
        self.running = True
        logger.info("🚀 Starting Shopping Analytics Pipeline...")
        
        try:
            while self.running:
                loop_start = time.time()
                
                for cam_id in self.camera_manager.streams.keys():
                    ret, frame = self.camera_manager.get_frame(cam_id)
                    if not ret or frame is None:
                        continue

                    # Initialize engines for this camera if not done yet
                    if cam_id not in self.zone_engines:
                        h, w, _ = frame.shape
                        cam_config = next((c for c in self.config['cameras'] if c['id'] == cam_id), None)
                        if cam_config:
                            self.zone_engines[cam_id] = ZoneEngine(cam_id, cam_config['zones'], (w, h))
                            self.event_engines[cam_id] = EventEngine(self.config, self.logger, self.db)
                        else:
                            continue

                    # 1. Detect
                    detections = self.detector.detect(frame)
                    
                    # 2. Track
                    tracked_detections = self.tracker.update(detections)

                    # 3. Zone Logic
                    zone_engine = self.zone_engines[cam_id]
                    polygon_states, line_crossings = zone_engine.process_detections(tracked_detections)

                    # 4. Event Logic
                    event_engine = self.event_engines[cam_id]
                    event_engine.update(cam_id, tracked_detections, polygon_states, line_crossings, time.time())

                    # 5. Visualization (Optional: Display for debugging)
                    # Uncomment below to show video feed with annotations
                    # annotated_frame = tracked_detections.annotate(scene=frame.copy())
                    # cv2.imshow(f"Feed: {cam_id}", annotated_frame)
                    
                    # Break on 'q' key
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        self.stop()
                        break

                # Control FPS / Loop speed
                elapsed = time.time() - loop_start
                if elapsed < 0.03: # Cap at ~30 FPS logic loop
                    time.sleep(0.03 - elapsed)

        except KeyboardInterrupt:
            logger.info("Interrupted by user.")
        finally:
            self.stop()

    def stop(self):
        if not self.running:
            return
        self.running = False
        logger.info("🛑 Stopping pipeline...")
        self.camera_manager.stop_all()
        self.db.close()
        cv2.destroyAllWindows()
        logger.info("Pipeline stopped gracefully.")

def main():
    # Setup signal handling for clean exit
    def signal_handler(sig, frame):
        if 'pipeline' in globals():
            pipeline.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    pipeline = Pipeline()
    pipeline.start()

if __name__ == "__main__":
    main()
