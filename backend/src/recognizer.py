import os
from datetime import datetime
from collections import Counter
import math
import cv2
import torch
from ultralytics import YOLO

from classification import (
    get_digit_model,
    get_letter_model,
    predict_digit,
    predict_digit_with_probabilities,
    predict_letter,
    predict_letter_with_probabilities,
)
from utils import (
    smart_padding,
    sort_objects,
    filter_objects_in_plate,
    remove_character_duplicate_boxes
)


class PlateRecognizer:
    def __init__(
        self, *,
        yolo_ckpt, 
        digit_ckpt, 
        letter_ckpt,
        exp_w_ratio=0.15,
        exp_h_ratio=0.1,
        conf_thresh=0.7,
        iou_char_thresh=0.7
    ):
        self._enable_checkpoint_compatibility()
        self.yolo_model = YOLO(yolo_ckpt)
        self.digit_model = get_digit_model(digit_ckpt)
        self.letter_model = get_letter_model(letter_ckpt)
        self.exp_w_ratio = exp_w_ratio
        self.exp_h_ratio = exp_h_ratio
        self.conf_thresh = conf_thresh
        self.iou_char_thresh = iou_char_thresh

    @staticmethod
    def _enable_checkpoint_compatibility():
        try:
            if getattr(torch.load, "_vietplateai_weights_compat", False):
                return

            original_torch_load = torch.load

            def compat_torch_load(*args, **kwargs):
                kwargs.setdefault("weights_only", False)
                return original_torch_load(*args, **kwargs)

            compat_torch_load._vietplateai_weights_compat = True
            torch.load = compat_torch_load
        except Exception:
            pass

    @staticmethod
    def _compute_plate_bbox(plate):
        if plate is None:
            return None

        (x1, y1), (x2, y2) = plate["landmark"]
        height = plate["height"]
        return {
            "x_min": int(x1),
            "y_min": int(y1 - height / 2),
            "x_max": int(x2),
            "y_max": int(y2 + height / 2),
        }

    @staticmethod
    def _aggregate_ocr_confidence(probabilities):
        if not probabilities:
            return None

        epsilon = 1e-6
        return float(math.exp(sum(math.log(max(prob, epsilon)) for prob in probabilities) / len(probabilities)))

    @staticmethod
    def _combine_confidences(detector_confidence, ocr_confidence):
        if detector_confidence is None and ocr_confidence is None:
            return None
        if detector_confidence is None:
            return ocr_confidence
        if ocr_confidence is None:
            return detector_confidence

        final_confidence = 0.55 * detector_confidence + 0.45 * ocr_confidence
        return float(max(0.0, min(1.0, final_confidence)))

    def detect_batch(self, batch_imgs):
        batch_objects = []
        batch_plates = []

        results = self.yolo_model(
            batch_imgs, 
            conf=self.conf_thresh, 
            iou=0.2, 
            verbose=False
        )

        for img, res in zip(batch_imgs, results):
            height, width = img.shape[:2]
            objects = []
            plate = None
            for box in res.boxes:
                cls = int(box.cls[0].item())
                label = self.yolo_model.names[cls]
                conf = float(box.conf[0].item())
                x_min, y_min, x_max, y_max = map(int, box.xyxy[0].tolist())

                if label in {'one_row', 'two_row'}:
                    landmark1 = (x_min, y_min + (y_max - y_min) / 2)
                    landmark2 = (x_max, y_max - (y_max - y_min) / 2)
                    plate = {
                        'landmark': [landmark1, landmark2],
                        'label': label,
                        'height': y_max - y_min,
                        'conf': conf
                    }
                else:
                    w, h = x_max - x_min, y_max - y_min
                    delta_w = w * self.exp_w_ratio
                    delta_h = h * self.exp_h_ratio

                    x_lower = max(0, int(x_min - delta_w))
                    y_lower = max(0, int(y_min - delta_h))

                    x_upper = min(width, int(x_max + delta_w))
                    y_upper = min(height, int(y_max + 2 * delta_h))

                    crop = img[y_lower:y_upper, x_lower:x_upper]
                    img_obj = smart_padding(crop)

                    obj = {
                        'image': img_obj,
                        'box': (x_min, y_min, x_max, y_max),
                        'center': ((x_lower + x_upper) / 2, (y_lower + y_upper) / 2),
                        'label': label,
                        'conf': conf
                    }
                    objects.append(obj)

            objects = filter_objects_in_plate(objects, plate)
            objects = remove_character_duplicate_boxes(objects, self.iou_char_thresh)

            batch_objects.append(objects)
            batch_plates.append(plate)

        return batch_objects, batch_plates
    
    def predict_batch(self, batch_inputs, batch_size=2):
        return [
            result["plate_number"] if result["detected"] else ""
            for result in self.recognize_batch(batch_inputs, batch_size=batch_size)
        ]

    def recognize_batch(self, batch_inputs, batch_size=2):
        if not isinstance(batch_inputs, list):
            batch_inputs = [batch_inputs]

        if all(isinstance(p, str) for p in batch_inputs):
            batch_imgs = [cv2.imread(path) for path in batch_inputs]
        else:
            batch_imgs = batch_inputs

        batch_objects, batch_plates = self.detect_batch(batch_imgs)

        digit_imgs, digit_refs = [], []
        letter_imgs, letter_refs = [], []

        for img_idx, objects in enumerate(batch_objects):
            plate = batch_plates[img_idx]
            if plate is None:
                continue

            sorted_objs = sort_objects(objects, plate)
            batch_objects[img_idx] = sorted_objs

            for obj_idx, obj in enumerate(sorted_objs):
                if obj["label"] == "digit":
                    digit_imgs.append(obj["image"])
                    digit_refs.append((img_idx, obj_idx))
                elif obj["label"] == "letter":
                    letter_imgs.append(obj["image"])
                    letter_refs.append((img_idx, obj_idx))

        digit_preds = []
        if digit_imgs:
            digit_preds = predict_digit_with_probabilities(
                digit_imgs,
                self.digit_model,
                batch_size=batch_size,
            )

        letter_preds = []
        if letter_imgs:
            letter_preds = predict_letter_with_probabilities(
                letter_imgs,
                self.letter_model,
                batch_size=batch_size,
            )

        digit_map = {ref: pred for ref, pred in zip(digit_refs, digit_preds)}
        letter_map = {ref: pred for ref, pred in zip(letter_refs, letter_preds)}

        results = []
        for img_idx, objects in enumerate(batch_objects):
            plate = batch_plates[img_idx]
            image = batch_imgs[img_idx]

            if plate is None:
                results.append(
                    {
                        "detected": False,
                        "plate_number": None,
                        "confidence": None,
                        "detector_confidence": None,
                        "ocr_confidence": None,
                        "plate_type": None,
                        "bbox": None,
                        "image_width": int(image.shape[1]),
                        "image_height": int(image.shape[0]),
                        "ocr_characters": [],
                        "selected_frame_image": image,
                    }
                )
                continue

            plate_chars = [""] * len(objects)
            ocr_characters = []
            character_probabilities = []

            for obj_idx, obj in enumerate(objects):
                prediction = None
                if obj["label"] == "digit":
                    prediction = digit_map.get((img_idx, obj_idx))
                elif obj["label"] == "letter":
                    prediction = letter_map.get((img_idx, obj_idx))

                if prediction is None:
                    continue

                plate_chars[obj_idx] = prediction["label"]
                character_probabilities.append(prediction["probability"])
                ocr_characters.append(
                    {
                        "character": prediction["label"],
                        "probability": float(prediction["probability"]),
                        "label_type": obj["label"],
                        "detection_confidence": float(obj["conf"]),
                        "box": tuple(int(value) for value in obj["box"]),
                    }
                )

            plate_number = "".join(plate_chars)
            detector_confidence = float(plate["conf"])
            ocr_confidence = self._aggregate_ocr_confidence(character_probabilities)
            final_confidence = self._combine_confidences(
                detector_confidence,
                ocr_confidence,
            )

            results.append(
                {
                    "detected": bool(plate_number and ocr_characters),
                    "plate_number": plate_number or None,
                    "confidence": final_confidence,
                    "detector_confidence": detector_confidence,
                    "ocr_confidence": ocr_confidence,
                    "plate_type": plate["label"],
                    "bbox": self._compute_plate_bbox(plate),
                    "image_width": int(image.shape[1]),
                    "image_height": int(image.shape[0]),
                    "ocr_characters": ocr_characters,
                    "selected_frame_image": image,
                }
            )

        return results
    
    def visualize_batch(
        self, 
        batch_inputs, *,
        batch_size=2,
        return_imgs=False,
        cell_w=15,
        cell_h=15,
        font_scale=0.35, 
        thickness=1, 
        plate_color=(255, 100, 0),
        char_color=(0, 255, 0),
        conf_color=(255, 255, 0),
        output_dir=None,
        verbose=False
    ):
        if output_dir is not None:
            os.makedirs(output_dir, exist_ok=True)

        file_names = []
        if isinstance(batch_inputs, list) and all(isinstance(p, str) for p in batch_inputs):
            batch_imgs = [cv2.imread(path) for path in batch_inputs]
            file_names = [os.path.basename(path) for path in batch_inputs]
        else:
            batch_imgs = batch_inputs
            for idx in range(len(batch_imgs)):
                time_str = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
                file_name = f"{time_str}_{idx}.png"
                file_names.append(file_name)
        
        batch_objects, batch_plates = self.detect_batch(batch_imgs)
        digit_imgs, digit_refs = [], []
        letter_imgs, letter_refs = [], []

        for img_idx, objects in enumerate(batch_objects):
            plate = batch_plates[img_idx]

            if plate is None:
                continue

            sorted_objs = sort_objects(objects, plate)
            batch_objects[img_idx] = sorted_objs
            for obj_idx, obj in enumerate(sorted_objs):
                if obj["label"] == "digit":
                    digit_imgs.append(obj["image"])
                    digit_refs.append((img_idx, obj_idx))
                elif obj["label"] == "letter":
                    letter_imgs.append(obj["image"])
                    letter_refs.append((img_idx, obj_idx))

        digit_preds = predict_digit(digit_imgs, self.digit_model, batch_size=batch_size) if digit_imgs else []
        letter_preds = predict_letter(letter_imgs, self.letter_model, batch_size=batch_size) if letter_imgs else []

        digit_map = {ref: pred for ref, pred in zip(digit_refs, digit_preds)}
        letter_map = {ref: pred for ref, pred in zip(letter_refs, letter_preds)}

        out_imgs = []
        for img_idx, (img, plate, objects) in enumerate(zip(batch_imgs, batch_plates, batch_objects)):
            image_vis = img.copy()

            if plate is None:
                out_imgs.append(image_vis)
                continue

            (x1, y1), (x2, y2) = plate["landmark"]
            height = plate['height']
            y_min = int(y1 - height / 2)
            y_max = int(y2 + height / 2)
            x_min = int(x1)
            x_max = int(x2)

            cv2.rectangle(image_vis, (x_min, y_min), (x_max, y_max), plate_color, 1)
            cv2.putText(
                image_vis, f"{obj['conf']:.2f}", 
                (int((x_min + x_max) / 2 - 5), int(y_max + 10)), 
                cv2.FONT_HERSHEY_SIMPLEX, font_scale, plate_color, thickness
            )

            start_x, start_y = 5, 5
            
            for obj_idx, obj in enumerate(objects):
                crop = obj["image"]
                crop_resized = cv2.resize(crop, (cell_w, cell_h))
                crop_resized = cv2.cvtColor(crop_resized, cv2.COLOR_GRAY2BGR)

                pred = "?"
                if obj["label"] == "digit" and (img_idx, obj_idx) in digit_map:
                    pred = str(digit_map[(img_idx, obj_idx)])
                elif obj["label"] == "letter" and (img_idx, obj_idx) in letter_map:
                    pred = str(letter_map[(img_idx, obj_idx)])

                col_x = start_x + obj_idx * (cell_w + 15)
                image_vis[start_y:start_y + cell_h, col_x:col_x + cell_w] = crop_resized

                cv2.putText(image_vis, pred, (int(col_x + cell_w / 4), start_y + cell_h + 12),
                            cv2.FONT_HERSHEY_SIMPLEX, font_scale, char_color, thickness)
                
                cv2.putText(image_vis, f"{obj['conf']:.2f}", (col_x, start_y + 2 * (cell_h + 5)),
                            cv2.FONT_HERSHEY_SIMPLEX, font_scale, conf_color, thickness)
                
            out_imgs.append(image_vis)

        if output_dir is not None:
            for out_img, file_name in zip(out_imgs, file_names):
                save_path = os.path.join(output_dir, file_name)
                if not cv2.imwrite(save_path, out_img):
                    print(f"Failed to save: {save_path}")
                else:
                    if verbose:
                        print(f"Image saved: {save_path}")

        if return_imgs:
            return out_imgs
        
    def visualize_video(
        self,
        video_path,
        output_path,
        batch_size=2,
        cell_w=40,
        cell_h=50,
        font_scale=1.2,
        thickness=2,
        plate_color=(0, 255, 255),
        char_color=(255, 255, 255),
        conf_color=(0, 255, 0),
        bg_color=(40, 40, 40),
        skip_frames=1,
        vote_frames=5
    ):
        from collections import Counter
        
        cap = cv2.VideoCapture(video_path)
        
        fps = int(cap.get(cv2.CAP_PROP_FPS))
        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, fps, (w, h))
        
        frame_idx = 0
        vote_buffer = []
        voted_results = None
        
        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                if frame_idx % skip_frames == 0:
                    try:
                        batch_objects, batch_plates = self.detect_batch([frame])
                        objects, plate = batch_objects[0], batch_plates[0]
                        
                        if plate is not None:
                            sorted_objs = sort_objects(objects, plate)
                            digit_imgs, digit_refs, letter_imgs, letter_refs = [], [], [], []
                            
                            for obj_idx, obj in enumerate(sorted_objs):
                                if obj["label"] == "digit":
                                    digit_imgs.append(obj["image"])
                                    digit_refs.append(obj_idx)
                                elif obj["label"] == "letter":
                                    letter_imgs.append(obj["image"])
                                    letter_refs.append(obj_idx)
                            
                            digit_preds = predict_digit(digit_imgs, self.digit_model, batch_size=batch_size) if digit_imgs else []
                            letter_preds = predict_letter(letter_imgs, self.letter_model, batch_size=batch_size) if letter_imgs else []
                            
                            digit_map = {ref: pred for ref, pred in zip(digit_refs, digit_preds)}
                            letter_map = {ref: pred for ref, pred in zip(letter_refs, letter_preds)}
                            
                            current_results = {}
                            for obj_idx, obj in enumerate(sorted_objs):
                                if obj["label"] == "digit" and obj_idx in digit_map:
                                    current_results[obj_idx] = str(digit_map[obj_idx])
                                elif obj["label"] == "letter" and obj_idx in letter_map:
                                    current_results[obj_idx] = str(letter_map[obj_idx])
                            
                            vote_buffer.append(current_results)
                            
                            if len(vote_buffer) >= vote_frames:
                                voted_results = {}
                                all_positions = set()
                                for results in vote_buffer:
                                    all_positions.update(results.keys())
                                
                                for pos in all_positions:
                                    votes = [results.get(pos, "?") for results in vote_buffer if pos in results]
                                    if votes:
                                        voted_results[pos] = Counter(votes).most_common(1)[0][0]
                                
                                vote_buffer.pop(0)
                            
                            if voted_results:
                                (x1, y1), (x2, y2) = plate["landmark"]
                                height = plate['height']
                                y_min, y_max = int(y1 - height / 2), int(y2 + height / 2)
                                x_min, x_max = int(x1), int(x2)
                                
                                cv2.rectangle(frame, (x_min, y_min), (x_max, y_max), plate_color, 3)
                                
                                conf_text = f"Conf: {plate['conf']:.2f}"
                                text_size = cv2.getTextSize(conf_text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)[0]
                                cv2.rectangle(frame, (x_min, y_max + 5), (x_min + text_size[0] + 10, y_max + 30), bg_color, -1)
                                cv2.putText(frame, conf_text, (x_min + 5, y_max + 23),
                                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, plate_color, 2)
                                
                                start_x, start_y = 15, 15
                                num_chars = len(sorted_objs)
                                panel_width = num_chars * (cell_w + 10) + 20
                                panel_height = cell_h + 80
                                
                                cv2.rectangle(frame, (start_x - 10, start_y - 10), 
                                            (start_x + panel_width, start_y + panel_height), bg_color, -1)
                                cv2.rectangle(frame, (start_x - 10, start_y - 10), 
                                            (start_x + panel_width, start_y + panel_height), plate_color, 2)
                                
                                for obj_idx, obj in enumerate(sorted_objs):
                                    crop_resized = cv2.resize(obj["image"], (cell_w, cell_h))
                                    crop_resized = cv2.cvtColor(crop_resized, cv2.COLOR_GRAY2BGR)
                                    
                                    pred = voted_results.get(obj_idx, "?")
                                    
                                    col_x = start_x + obj_idx * (cell_w + 10)
                                    frame[start_y:start_y + cell_h, col_x:col_x + cell_w] = crop_resized
                                    
                                    cv2.rectangle(frame, (col_x - 2, start_y - 2), 
                                                (col_x + cell_w + 2, start_y + cell_h + 2), (100, 100, 100), 1)
                                    
                                    text_size = cv2.getTextSize(pred, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)[0]
                                    text_x = col_x + (cell_w - text_size[0]) // 2
                                    text_y = start_y + cell_h + 30
                                    cv2.putText(frame, pred, (text_x, text_y),
                                                cv2.FONT_HERSHEY_SIMPLEX, font_scale, char_color, thickness)
                                    
                                    conf_str = f"{obj['conf']:.2f}"
                                    conf_size = cv2.getTextSize(conf_str, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)[0]
                                    conf_x = col_x + (cell_w - conf_size[0]) // 2
                                    conf_y = start_y + cell_h + 55
                                    cv2.putText(frame, conf_str, (conf_x, conf_y),
                                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, conf_color, 1)
                    except:
                        pass
                
                out.write(frame)
                frame_idx += 1
        finally:
            cap.release()
            out.release()
        
        return output_path
    
    def extract_plates_from_video(
        self,
        video_path,
        batch_size=2,
        skip_frames=1,
        vote_frames=5,
        similarity_threshold=0.85,
        min_confidence=0.75
    ):
        """
        Extract license plate numbers from video and return detection data.
        Uses fuzzy matching to eliminate duplicate/similar plate detections.
        
        Args:
            video_path: Path to video file
            batch_size: Batch size for model prediction
            skip_frames: Skip every N frames
            vote_frames: Number of frames to use for voting
            similarity_threshold: Threshold for considering plates as duplicates (0-1)
            min_confidence: Minimum confidence to save a detection
        
        Returns:
            List of dicts with: {plate_number, confidence, timestamp}
        """
        from difflib import SequenceMatcher
        
        def levenshtein_distance(s1, s2):
            """Calculate Levenshtein distance between two strings"""
            if len(s1) < len(s2):
                return levenshtein_distance(s2, s1)
            if len(s2) == 0:
                return len(s1)
            
            previous_row = range(len(s2) + 1)
            for i, c1 in enumerate(s1):
                current_row = [i + 1]
                for j, c2 in enumerate(s2):
                    insertions = previous_row[j + 1] + 1
                    deletions = current_row[j] + 1
                    substitutions = previous_row[j] + (c1 != c2)
                    current_row.append(min(insertions, deletions, substitutions))
                previous_row = current_row
            
            return previous_row[-1]
        
        def string_similarity(s1, s2):
            """Calculate similarity between two strings (0-1)"""
            if len(s1) == 0 or len(s2) == 0:
                return 0.0
            max_len = max(len(s1), len(s2))
            distance = levenshtein_distance(s1, s2)
            return 1.0 - (distance / max_len)
        
        def is_similar_to_any(plate, existing_plates, threshold):
            """Check if plate is similar to any existing plate"""
            for existing_plate in existing_plates:
                if string_similarity(plate, existing_plate) >= threshold:
                    return True
            return False
        
        cap = cv2.VideoCapture(video_path)
        fps = int(cap.get(cv2.CAP_PROP_FPS))
        
        frame_idx = 0
        vote_buffer = []
        voted_results = None
        detections = []
        detected_plates = []  # List to track detected plates with similarity matching
        
        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                if frame_idx % skip_frames == 0:
                    try:
                        batch_objects, batch_plates = self.detect_batch([frame])
                        objects, plate = batch_objects[0], batch_plates[0]
                        
                        if plate is not None:
                            sorted_objs = sort_objects(objects, plate)
                            digit_imgs, digit_refs = [], []
                            letter_imgs, letter_refs = [], []
                            
                            for obj_idx, obj in enumerate(sorted_objs):
                                if obj["label"] == "digit":
                                    digit_imgs.append(obj["image"])
                                    digit_refs.append(obj_idx)
                                elif obj["label"] == "letter":
                                    letter_imgs.append(obj["image"])
                                    letter_refs.append(obj_idx)
                            
                            digit_preds = predict_digit(digit_imgs, self.digit_model, batch_size=batch_size) if digit_imgs else []
                            letter_preds = predict_letter(letter_imgs, self.letter_model, batch_size=batch_size) if letter_imgs else []
                            
                            digit_map = {ref: pred for ref, pred in zip(digit_refs, digit_preds)}
                            letter_map = {ref: pred for ref, pred in zip(letter_refs, letter_preds)}
                            
                            current_results = {}
                            for obj_idx, obj in enumerate(sorted_objs):
                                if obj["label"] == "digit" and obj_idx in digit_map:
                                    current_results[obj_idx] = str(digit_map[obj_idx])
                                elif obj["label"] == "letter" and obj_idx in letter_map:
                                    current_results[obj_idx] = str(letter_map[obj_idx])
                            
                            vote_buffer.append(current_results)
                            
                            if len(vote_buffer) >= vote_frames:
                                voted_results = {}
                                all_positions = set()
                                for results in vote_buffer:
                                    all_positions.update(results.keys())
                                
                                for pos in all_positions:
                                    votes = [results.get(pos, "?") for results in vote_buffer if pos in results]
                                    if votes:
                                        voted_results[pos] = Counter(votes).most_common(1)[0][0]
                                
                                vote_buffer.pop(0)
                            
                            if voted_results:
                                plate_number = "".join([voted_results.get(i, "?") for i in range(len(sorted_objs))])
                                confidence = float(plate["conf"])
                                
                                # Filter: Must have valid characters, minimum confidence, and not be similar to existing
                                if ("?" not in plate_number and 
                                    confidence >= min_confidence and 
                                    not is_similar_to_any(plate_number, detected_plates, similarity_threshold)):
                                    
                                    detected_plates.append(plate_number)
                                    detection = {
                                        "plate_number": plate_number,
                                        "confidence": confidence,
                                        "timestamp": datetime.now()
                                    }
                                    detections.append(detection)
                    except:
                        pass
                
                frame_idx += 1
        finally:
            cap.release()
        
        return detections
