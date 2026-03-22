import cv2
import time
import os
import numpy as np
from database import init_db, db_register_voter
from face_utils import get_face_encoding, get_face_landmarks, LEFT_EYE, RIGHT_EYE, MOUTH

# Create directory for saving voter photos
IMAGE_DIR = "voter_images"
if not os.path.exists(IMAGE_DIR):
    os.makedirs(IMAGE_DIR)

def try_open_camera():
    """Try various camera backends and indices for best compatibility."""
    # List of combinations to try: (index, backend)
    # None = default backend
    tries = [
        (0, None),           # Default index 0
        (0, cv2.CAP_DSHOW),  # DirectShow index 0
        (1, None),           # Default index 1 (common for external cams)
        (0, cv2.CAP_MSMF),   # MS Media Foundation
    ]
    
    for idx, backend in tries:
        b_name = "Default" if backend is None else ("DSHOW" if backend == cv2.CAP_DSHOW else "MSMF")
        print(f"  Testing Camera {idx} with {b_name} backend...")
        try:
            if backend is not None:
                cap = cv2.VideoCapture(idx, backend)
            else:
                cap = cv2.VideoCapture(idx)
                
            if cap and cap.isOpened():
                # Test read
                ret, frame = cap.read()
                if ret and frame is not None:
                    print(f"  ✅ SUCCESS: Camera {idx} ({b_name}) is working!")
                    return cap
                cap.release()
        except Exception as e:
            print(f"  ❌ Error testing {idx}/{b_name}: {e}")
            
    return None

def register_from_photo(aadhar_no, voter_id, name):
    """Fallback: register using a photo file on disk."""
    print("\n📁 PHOTO FILE REGISTRATION")
    path = input("   Enter the full photo file path: ").strip().strip('"')

    if not os.path.exists(path):
        print(f"❌ File not found: {path}")
        return

    frame = cv2.imread(path)
    if frame is None:
        print("❌ Could not read image file.")
        return

    encoding = get_face_encoding(frame)
    if encoding is None:
        print("❌ No face detected in the photo.")
        return

    success, msg = db_register_voter(aadhar_no, voter_id, name, encoding)
    if success:
        # Save a copy to our voter_images folder
        img_path = os.path.join(IMAGE_DIR, f"{aadhar_no}.jpg")
        cv2.imwrite(img_path, frame)
        print(f"\n✅ REGISTRATION COMPLETE! Saved image to {img_path}")
    else:
        print(f"\n❌ Registration Failed: {msg}")

def register_mock_voter():
    print("=============================================")
    print("    Smart Voting - Voter Registration")
    print("=============================================")
    aadhar_no = input("Enter Aadhar Number (12 digits): ").strip()
    voter_id  = input("Enter Voter ID: ").strip()
    name      = input("Enter Full Name: ").strip()

    print("\n[INFO] Searching for usable camera...")
    cap = try_open_camera()

    if cap is None:
        print("\n⚠️ No working webcam found!")
        choice = input("Register using a PHOTO FILE instead? (y/n): ").strip().lower()
        if choice == 'y': register_from_photo(aadhar_no, voter_id, name)
        return

    face_encoding = None
    captured_frame = None
    
    print("\n" + "*"*45)
    print(" 📸 CAMERA ACTIVE")
    print(" 1. Look directly at the camera.")
    print(" 2. Press SPACE to capture your photo.")
    print(" 3. Press 'Q' to cancel.")
    print("*"*45 + "\n")

    while True:
        ret, frame = cap.read()
        if not ret or frame is None:
            continue

        display = frame.copy()
        
        # ── Landmark Visualization ──
        landmarks, shapes = get_face_landmarks(frame)
        if landmarks:
            # Draw eyes
            for idx in LEFT_EYE + RIGHT_EYE:
                cv2.circle(display, landmarks[idx], 2, (0, 255, 0), -1)
            # Draw mouth
            for idx in MOUTH:
                cv2.circle(display, landmarks[idx], 2, (0, 255, 255), -1)
                
            # Show Blink/EAR status
            left  = shapes.get("eyeBlinkLeft",  0.0)
            right = shapes.get("eyeBlinkRight", 0.0)
            avg   = (left + right) / 2.0
            color = (0, 255, 0) if avg > 0.4 else (200, 200, 200)
            cv2.putText(display, f"Liveness (Blink): {avg:.2f}", (10, 60),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        cv2.putText(display, "Press [SPACE] to Capture | [Q] to Quit",
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        cv2.imshow("Smart Voting - Registration", display)
        
        key = cv2.waitKey(1) & 0xFF
        if key == ord(' '):
            print("Processing capture...")
            encoding = get_face_encoding(frame)
            if encoding is None:
                print("❌ ERROR: No face detected. Please try again.")
                # Show error on screen briefly
                err_display = display.copy()
                cv2.putText(err_display, "NO FACE DETECTED!", (50, 200), 
                            cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 3)
                cv2.imshow("Smart Voting - Registration", err_display)
                cv2.waitKey(1000)
            else:
                face_encoding = encoding
                captured_frame = frame.copy()
                print("✅ Face captured successfully!")
                break
        elif key == ord('q'):
            print("Registration cancelled.")
            break

    cap.release()
    cv2.destroyAllWindows()

    if face_encoding is not None:
        success, msg = db_register_voter(aadhar_no, voter_id, name, face_encoding)
        if success:
            # SAVE THE PHYSICAL IMAGE FILE
            img_path = os.path.join(IMAGE_DIR, f"{aadhar_no}.jpg")
            cv2.imwrite(img_path, captured_frame)
            print("\n" + "="*45)
            print(f"✅ REGISTRATION SUCCESSFUL!")
            print(f"   Image Saved To: {img_path}")
            print("="*45)
        else:
            print(f"\n❌ Registration Failed: {msg}")

if __name__ == '__main__':
    init_db()
    register_mock_voter()
