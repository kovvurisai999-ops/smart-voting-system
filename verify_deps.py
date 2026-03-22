import cv2
import numpy as np
import face_utils

print("Testing face_utils with dummy frame...")
try:
    dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    is_blinking, score = face_utils.detect_blink(dummy_frame)
    print(f"Blink detection ran successfully. Result: {is_blinking}, Score: {score}")
    
    encoding = face_utils.get_face_encoding(dummy_frame)
    print("Face encoding attempt complete.")
    
    print("✅ All face_utils functions executed without crashing.")
except Exception as e:
    print(f"❌ Error in face_utils: {e}")
    import traceback
    traceback.print_exc()
