import cv2
import numpy as np
import os
import threading

_lock = threading.Lock()

# ─── OpenCV YuNet face detector + SFace recognizer (no Dlib, no MediaPipe legacy) ─

_MODEL_RECOG   = "models/face_recognition_sface.onnx"
_MODEL_DETECT  = "models/face_detection_yunet.onnx"

_RECOG_URL  = "https://github.com/opencv/opencv_zoo/raw/main/models/face_recognition_sface/face_recognition_sface_2021dec.onnx"
_DETECT_URL = "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx"

def _download(path, url):
    if not os.path.exists(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        print(f"Downloading {os.path.basename(path)} …")
        import urllib.request
        urllib.request.urlretrieve(url, path)
        print("Done.")

_download(_MODEL_RECOG,  _RECOG_URL)
_download(_MODEL_DETECT, _DETECT_URL)

_recognizer = cv2.FaceRecognizerSF.create(_MODEL_RECOG, "")
_yunet = cv2.FaceDetectorYN.create(
    _MODEL_DETECT, "", (320, 320),
    score_threshold=0.35, nms_threshold=0.3, top_k=1,
)

# ─── MediaPipe Tasks API for blink detection ─────────────────────────────────
import mediapipe as mp

# MediaPipe new Tasks API facelandmarker
_MP_MODEL_PATH = "models/face_landmarker.task"
_MP_MODEL_URL  = "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task"
_download(_MP_MODEL_PATH, _MP_MODEL_URL)

BaseOptions        = mp.tasks.BaseOptions
FaceLandmarker     = mp.tasks.vision.FaceLandmarker
FaceLandmarkerOpts = mp.tasks.vision.FaceLandmarkerOptions
VisionRunningMode  = mp.tasks.vision.RunningMode

_lm_opts = FaceLandmarkerOpts(
    base_options=BaseOptions(model_asset_path=_MP_MODEL_PATH),
    running_mode=VisionRunningMode.IMAGE,
    num_faces=1,
    output_face_blendshapes=True,
)
_landmarker = FaceLandmarker.create_from_options(_lm_opts)

# ─── Blink via blendshapes ────────────────────────────────────────────────────
_BLINK_THRESHOLD = 0.40   # blendshape score 0-1

def detect_blink(frame_bgr, threshold=_BLINK_THRESHOLD):
    """
    Returns (is_blinking: bool, score: float).
    Uses eyeBlinkLeft + eyeBlinkRight blendshapes from MediaPipe Tasks.
    """
    rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
    result = _landmarker.detect(mp_image)
    if not result.face_blendshapes:
        return False, 0.0
    shapes = {s.category_name: s.score for s in result.face_blendshapes[0]}
    left  = shapes.get("eyeBlinkLeft",  0.0)
    right = shapes.get("eyeBlinkRight", 0.0)
    avg   = (left + right) / 2.0
    return avg >= threshold, round(avg, 3)

def get_face_landmarks(frame_bgr):
    """
    Returns (landmarks, blendshapes) for visualization.
    landmarks: list of (x, y) coordinates.
    blendshapes: dict of score categories.
    """
    h, w = frame_bgr.shape[:2]
    rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
    result = _landmarker.detect(mp_image)
    
    if not result.face_landmarks:
        return None, None
        
    # Convert normalized landmarks to pixel coords
    raw_landmarks = result.face_landmarks[0]
    landmarks = [(int(pt.x * w), int(pt.y * h)) for pt in raw_landmarks]
    
    shapes = {}
    if result.face_blendshapes:
        shapes = {s.category_name: s.score for s in result.face_blendshapes[0]}
        
    return landmarks, shapes

# Key landmark indices (from MediaPipe face mesh)
LEFT_EYE  = [33, 133, 160, 158, 153, 144]
RIGHT_EYE = [362, 263, 387, 385, 380, 373]
MOUTH     = [61, 291, 13, 14, 78, 308]

# ─── YuNet face detection ─────────────────────────────────────────────────────
def _detect_face(frame_bgr):
    """Detect single face with YuNet, picking the largest one among top candidates."""
    if frame_bgr is None or frame_bgr.size == 0:
        return None
        
    h, w = frame_bgr.shape[:2]
    if h == 0 or w == 0:
        return None
    
    def pick_largest(faces_arr):
        if faces_arr is None or len(faces_arr) == 0:
            return None
        largest_face = max(faces_arr, key=lambda f: f[2] * f[3])
        return largest_face

    # 1. Try YuNet (fastest) - Wrapped in lock for thread safety
    with _lock:
        _yunet.setInputSize((w, h))
        _, faces = _yunet.detect(frame_bgr)
    
    face = pick_largest(faces)
    if face is not None:
        return face
        
    # 2. Try Image Enhancement + YuNet
    enhanced = cv2.convertScaleAbs(frame_bgr, alpha=1.2, beta=30)
    with _lock:
        _yunet.setInputSize((w, h))
        _, faces_e = _yunet.detect(enhanced)
    
    face = pick_largest(faces_e)
    if face is not None:
        return face
        
    # 3. Fallback to MediaPipe landmarks
    rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
    result = _landmarker.detect(mp_image)
    
    if result.face_landmarks:
        # If multiple faces are detected by MediaPipe, pick one (MediaPipe Tasks IMAGE mode returns list of normalized landmarks)
        pts = result.face_landmarks[0]
        xs = [p.x * w for p in pts]
        ys = [p.y * h for p in pts]
        x1, y1, x2, y2 = min(xs), min(ys), max(xs), max(ys)
        return np.array([x1, y1, x2-x1, y2-y1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1.0], dtype=np.float32)

    return None

def calculate_sharpness(image):
    """Returns the Laplacian variance as a measure of focus/sharpness."""
    if image is None or image.size == 0:
        return 0
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return cv2.Laplacian(gray, cv2.CV_64F).var()

def validate_frame_quality(frame_bgr):
    """
    Returns (is_valid: bool, visibility_score: float, lighting_score: float, message: str)
    """
    face = _detect_face(frame_bgr)
    if face is None:
        return False, 0.0, 0.0, "No face detected"
    
    # ── SHARPNESS CHECK ───────────────────────────────────────────────────────
    sharpness = calculate_sharpness(frame_bgr)
    if sharpness < 80.0: # Rejects blurry frames early
        return False, 0.0, 0.0, "Face too blurry - hold still"
    
    # Confidence from YuNet or fallback
    confidence = face[-1]
    
    # Lighting: Check average brightness in face area
    h, w = frame_bgr.shape[:2]
    x, y, fw, fh = map(int, face[:4])
    # Clip coordinates
    x1, y1 = max(0, x), max(0, y)
    x2, y2 = min(w, x+fw), min(h, y+fh)
    
    face_roi = frame_bgr[y1:y2, x1:x2]
    if face_roi.size == 0:
        return False, 0.0, 0.0, "Invalid face area"
        
    gray_roi = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY)
    avg_brightness = np.mean(gray_roi) / 255.0
    
    # visibility_score: use confidence
    # lighting_score: normal range is 0.2 to 0.85
    lighting_ok = 0.20 < avg_brightness < 0.85
    
    if confidence < 0.6: # 60% visibility threshold
        return False, confidence, avg_brightness, "Face not clearly visible (low confidence)"
    if not lighting_ok:
        return False, confidence, avg_brightness, "Poor lighting conditions"
        
    return True, confidence, avg_brightness, "Quality OK"

# ─── Optimized Processing ───────────────────────────────────────────────────

def get_face_features(frame_bgr):
    """
    Detects, aligns, and extracts features in ONE pass.
    Returns: {
        'face': raw_yunet_face,
        'encoding': np_array_128d,
        'aligned': aligned_face_roi
    } or None
    """
    face = _detect_face(frame_bgr)
    if face is None:
        return None
        
    with _lock:
        aligned = _recognizer.alignCrop(frame_bgr, face)
        
        # ── CONTRAST NORMALIZATION (CLAHE) ──────────────────────────────────
        # Improves recognition in varying light by equalizing histogram locally
        lab = cv2.cvtColor(aligned, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        l2 = clahe.apply(l)
        lab2 = cv2.merge((l2, a, b))
        aligned_norm = cv2.cvtColor(lab2, cv2.COLOR_LAB2BGR)
        
        feat = _recognizer.feature(aligned_norm)
        
    # Extract landmarks [x1, y1, x2, y2, x3, y3, x4, y4, x5, y5]
    # Order: [LE, RE, NT, LM, RM]
    lms = face[4:14].reshape(-1, 2).tolist()
    
    return {
        'face': face,
        'encoding': feat.flatten().astype(np.float32),
        'aligned': aligned_norm,
        'landmarks': lms
    }

def verify_face(features, stored_encoding, threshold=0.36):
    """
    features: result from get_face_features or None
    stored_encoding: numpy array
    """
    if features is None:
        return False, "No face detected"
        
    s = stored_encoding.reshape(1, -1).astype(np.float32)
    l = features['encoding'].reshape(1, -1)
    
    with _lock:
        score = _recognizer.match(s, l, cv2.FaceRecognizerSF_FR_COSINE)
    
    if score >= threshold:
        return True, f"Verified (score {score:.3f})"
    return False, f"Mismatch (score {score:.3f})"

def check_biometric_duplicate(features, voted_list, current_aadhar, threshold=0.36):
    """
    features: result from get_face_features or None
    voted_list: list of dicts {'aadhar': str, 'name': str, 'face_encoding': np_array}
    threshold: cosine similarity limit (0-1). 
               Use ~0.36 for voting verification.
               Use ~0.48+ for registration-time duplicate prevention.
    """
    if features is None or not voted_list:
        return None

    # Vectorized Comparison
    live_enc = features['encoding']
    
    # Filter out current voter
    targets = [v for v in voted_list if v['aadhar'] != current_aadhar]
    if not targets:
        return None

    # Collect all encodings into a single matrix
    encodings_matrix = np.array([v['face_encoding'] for v in targets], dtype=np.float32)
    
    # SFace uses Cosine similarity. For unit vectors, cosine similarity is the dot product.
    # Let's ensure they are normalized just in case
    def normalize(v):
        norm = np.linalg.norm(v, axis=-1, keepdims=True)
        return v / (norm + 1e-6)

    live_norm = normalize(live_enc)
    matrix_norm = normalize(encodings_matrix)
    
    # Compute all cosine similarities in one dot product
    scores = np.dot(matrix_norm, live_norm)
    
    # Find the best match
    best_idx = np.argmax(scores)
    best_score = scores[best_idx]
    
    # Threshold for fraud detection
    if best_score >= threshold:
        return {
            "aadhar": targets[best_idx].get('aadhar'),
            "voter_id": targets[best_idx].get('voter_id'),
            "name": targets[best_idx]['name'],
            "score": float(best_score)
        }
            
    return None

def get_face_encoding(frame_bgr):
    """Legacy wrapper for backward compatibility."""
    feats = get_face_features(frame_bgr)
    return feats['encoding'] if feats else None
