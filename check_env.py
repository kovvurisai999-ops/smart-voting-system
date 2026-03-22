import sys
import os

def check_env():
    print("=============================================")
    print("    Smart Voting - Environment Check")
    print("=============================================")
    
    # 1. Check if running in a venv
    in_venv = (hasattr(sys, 'real_prefix') or 
               (sys.base_prefix != sys.prefix))
    
    if in_venv:
        print("✅ Running inside a virtual environment.")
    else:
        print("❌ NOT running in a virtual environment!")
        print("   Please use 'start_server.bat' or activate your venv first.")

    # 2. Check dependencies
    dependencies = [
        ('cv2', 'opencv-python'),
        ('flask', 'Flask'),
        ('numpy', 'numpy'),
        ('mediapipe', 'mediapipe')
    ]
    
    print("\nChecking dependencies:")
    all_ok = True
    for mod_name, pkg_name in dependencies:
        try:
            mod = __import__(mod_name)
            ver = getattr(mod, '__version__', 'unknown')
            print(f"  ✅ {pkg_name} is installed (version: {ver})")
        except ImportError:
            print(f"  ❌ {pkg_name} is MISSING!")
            all_ok = False

    # 3. Check models
    model_paths = [
        "models/face_detection_yunet.onnx",
        "models/face_recognition_sface.onnx",
        "models/face_landmarker.task"
    ]
    
    print("\nChecking local models:")
    for path in model_paths:
        if os.path.exists(path):
            print(f"  ✅ Found {path}")
        else:
            print(f"  ❌ MISSING {path}")
            all_ok = False

    print("\n" + "="*45)
    if all_ok:
        print("🎉 Environment looks good! You can run the app.")
    else:
        print("⚠️ Issues found. Please fix the red items above.")
    print("="*45)

if __name__ == "__main__":
    check_env()
