"""
License Plate Recognition Pipeline
Handles video processing, plate extraction, and database storage
"""
import os
import sys
from datetime import datetime


class LicensePlatePipeline:
    """End-to-end pipeline for processing videos and saving to database"""
    
    def __init__(self, model, api_path, camera_location="CT11, Kim Van Kim Lu"):
        """
        Initialize pipeline with model and database connection
        
        Args:
            model: PlateRecognizer instance
            api_path: Path to API module folder
            camera_location: Default camera location name
        """
        self.model = model
        self.camera_location = camera_location
        
        # Setup API paths
        if api_path not in sys.path:
            sys.path.insert(0, api_path)
        
        # Import database modules
        from database import SessionLocal
        from models import Camera, Detection
        from crud import create_detection, create_camera, get_camera
        import schemas
        
        self.SessionLocal = SessionLocal
        self.Camera = Camera
        self.Detection = Detection
        self.create_detection = create_detection
        self.create_camera = create_camera
        self.get_camera = get_camera
        self.schemas = schemas
        
        # Initialize camera
        self.camera_id = self._init_camera()
    
    def _init_camera(self):
        """Get or create camera in database"""
        db = self.SessionLocal()
        try:
            camera = db.query(self.Camera).filter(
                self.Camera.location_name == self.camera_location
            ).first()
            
            if not camera:
                camera = self.Camera(
                    location_name=self.camera_location, 
                    status="active"
                )
                db.add(camera)
                db.commit()
                db.refresh(camera)
                print(f"✓ Created camera: {camera.location_name}")
            else:
                print(f"✓ Using existing camera: {camera.location_name}")
            
            return camera.id
        finally:
            db.close()
    
    def process_video(
        self,
        video_path,
        skip_frames=2,
        vote_frames=5,
        similarity_threshold=0.85,
        min_confidence=0.75,
        save_to_db=True,
        verbose=True
    ):
        """
        Process video and extract/save license plates
        
        Args:
            video_path: Path to video file
            skip_frames: Skip every N frames
            vote_frames: Frames for voting consensus
            similarity_threshold: Duplicate detection sensitivity
            min_confidence: Minimum confidence threshold
            save_to_db: Whether to save to database
            verbose: Print progress
        
        Returns:
            dict with detection results and statistics
        """
        if verbose:
            print(f"Processing video: {video_path}")
        
        # Extract plates from video
        detections = self.model.extract_plates_from_video(
            video_path,
            skip_frames=skip_frames,
            vote_frames=vote_frames,
            similarity_threshold=similarity_threshold,
            min_confidence=min_confidence
        )
        
        if verbose:
            print(f"✓ Extracted {len(detections)} unique plates")
        
        # Save to database
        saved = []
        if save_to_db:
            db = self.SessionLocal()
            try:
                for detection_data in detections:
                    try:
                        detection_schema = self.schemas.DetectionCreate(
                            camera_id=self.camera_id,
                            plate_number=detection_data['plate_number'],
                            confidence=detection_data['confidence']
                        )
                        db_detection = self.create_detection(db, detection_schema)
                        saved.append(db_detection)
                        
                        if verbose:
                            print(
                                f"  ✓ {detection_data['plate_number']} "
                                f"(Conf: {detection_data['confidence']:.2f})"
                            )
                    except Exception as e:
                        if verbose:
                            print(f"  ✗ Error: {str(e)}")
            finally:
                db.commit()
                db.close()
        
        return {
            "video": video_path,
            "timestamp": datetime.now(),
            "camera_id": self.camera_id,
            "detections": detections,
            "saved_count": len(saved),
            "total_count": len(detections)
        }
    
    def get_recent_detections(self, limit=20):
        """Query recent detections for this camera"""
        db = self.SessionLocal()
        try:
            detections = db.query(self.Detection).filter(
                self.Detection.camera_id == self.camera_id
            ).order_by(self.Detection.timestamp.desc()).limit(limit).all()
            
            return [
                {
                    'id': d.id,
                    'plate_number': d.plate_number,
                    'confidence': d.confidence,
                    'visitor_type': str(d.visitor_type),
                    'timestamp': d.timestamp
                }
                for d in detections
            ]
        finally:
            db.close()
    
    def visualize_video(self, input_path, output_path):
        """Create visualization video with plate annotations"""
        print(f"Creating visualization...")
        self.model.visualize_video(input_path, output_path)
        print(f"✓ Saved to: {output_path}")
        return output_path
    
    def recalculate_detection_types(self):
        """
        Recalculate visitor types for all historical detections.
        Use this after registering vehicle statuses to fix previous classifications.
        """
        from crud import recalculate_detection_types
        
        db = self.SessionLocal()
        try:
            result = recalculate_detection_types(db, camera_id=self.camera_id)
            print(
                f"✓ Recalculated detection types:\n"
                f"  - Total detections: {result['total_detections']}\n"
                f"  - Updated: {result['updated_count']}\n"
                f"  - Camera: {result['camera_id']}"
            )
            return result
        finally:
            db.close()
