import cv2
import os
import time

def test_camera():
    print("=============================================")
    print("    Camera Diagnostic Tool")
    print("=============================================")
    
    # Try different backends
    backends = [
        ("DSHOW", cv2.CAP_DSHOW),
        ("MSMF", cv2.CAP_MSMF),
        ("Default", None)
    ]
    
    found = False
    for b_name, b_val in backends:
        print(f"\nTesting Backend: {b_name}")
        for i in range(3): # Try indices 0, 1, 2
            print(f"  Trying Index {i}...")
            try:
                if b_val is not None:
                    cap = cv2.VideoCapture(i, b_val)
                else:
                    cap = cv2.VideoCapture(i)
                
                if cap is not None and cap.isOpened():
                    print(f"  ✅ Camera {i} opened! warming up...")
                    # Warmup
                    for _ in range(15):
                        cap.read()
                        time.sleep(0.05)
                        
                    ret, frame = cap.read()
                    if ret and frame is not None:
                        filename = f"diag_test_{b_name}_{i}.jpg"
                        cv2.imwrite(filename, frame)
                        print(f"  🎉 SUCCESS! Saved test image: {filename}")
                        cap.release()
                        found = True
                        break
                    else:
                        print(f"  ❌ Camera opened but returned empty frames.")
                    cap.release()
                else:
                    print(f"  ❌ Failed to open camera.")
            except Exception as e:
                print(f"  ❌ Error: {e}")
        if found: break

    if not found:
        print("\n" + "!"*45)
        print("❌ NO WORKING CAMERA DETECTED.")
        print("!"*45)
        print("\nPossible issues:")
        print("1. Camera is physically blocked or covered.")
        print("2. Another app is using the camera (Close Zoom, Teams, Chrome etc).")
        print("3. Driver issue or permissions (check Windows Privacy settings).")
    else:
        print("\n✅ Diagnostic complete. If you see a test image file in your folder, the camera works!")

if __name__ == "__main__":
    test_camera()
