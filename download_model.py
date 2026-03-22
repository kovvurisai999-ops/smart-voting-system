import urllib.request
import bz2
import os

url = "http://dlib.net/files/shape_predictor_68_face_landmarks.dat.bz2"
output_file = "models/shape_predictor_68_face_landmarks.dat"
compressed_file = output_file + ".bz2"

if not os.path.exists(output_file):
    print("Downloading shape predictor model...")
    urllib.request.urlretrieve(url, compressed_file)
    print("Download complete. Extracting...")
    
    with bz2.BZ2File(compressed_file, 'rb') as source, open(output_file, 'wb') as dest:
        dest.write(source.read())
        
    os.remove(compressed_file)
    print("Extraction complete.")
else:
    print("Model already exists.")
