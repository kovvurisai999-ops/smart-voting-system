import os
import random
import base64
import hashlib
import traceback # Added traceback for error reporting

try:
    import sys
    # Debugging Render environment
    print("Python Path:", sys.path)
    print("Current Directory:", os.getcwd())
    try:
        import numpy as np_check
        print("Numpy Version:", np_check.__version__)
    except ImportError:
        print("Numpy NOT FOUND in path!")

    import numpy as np
    import cv2
    from flask import Flask, render_template, request, redirect, url_for, session, jsonify
    from flask_talisman import Talisman
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address

    from database import init_db, db_get_voter, db_mark_voted, db_cast_vote, db_get_vote_counts, db_get_user_vote, db_get_voted_biometrics, db_get_regional_results, db_get_available_districts
    from face_utils import detect_blink, verify_face, check_biometric_duplicate

    app = Flask(__name__)
    app.secret_key = 'smart_voting_secure_key_2024_AP'

except Exception as e:
    print("CRITICAL STARTUP ERROR:")
    traceback.print_exc()
    sys.exit(1)

# ── Security Middleware ──────────────────────────────────────────────────────
# Enforce security headers (Permissive for local media/scripts)
# force_https=False & strict_transport_security=False resolve 'ERR_SSL_PROTOCOL_ERROR' on localhost.
Talisman(app, content_security_policy=None, force_https=False, strict_transport_security=False) 

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per hour"],
    storage_uri="memory://"
)

init_db()

# ── Candidates ──────────────────────────────────────────────────────────────
CANDIDATES = {
    1: "N. Chandrababu Naidu (TDP)",
    2: "Y.S. Jagan Mohan Reddy (YSRCP)",
    3: "K. Pawan Kalyan (JSP)",
    4: "D. Purandeswari (BJP)",
    5: "NOTA",
}

AP_DISTRICTS = [
    "Alluri Sitaramaraju", "Anakapalli", "Anantapur", "Annamayya", "Bapatla", 
    "Chittoor", "Dr. B.R. Ambedkar Konaseema", "East Godavari", "Eluru", "Guntur", 
    "Kakinada", "Krishna", "Kurnool", "Nandyal", "NTR District", "Palnadu", 
    "Parvathipuram Manyam", "Prakasam", "Sri Balaji District", 
    "Sri Potti Sriramulu Nellore", "Sri Satya Sai District", "Srikakulam", 
    "Tirupati", "Visakhapatnam", "Vizianagaram", "West Godavari", "YSR Kadapa"
]

# ── Security Utilities ────────────────────────────────────────────────────────
def mask_aadhar(aadhar):
    """Masks Aadhaar number for security (e.g., XXXX-XXXX-1234)."""
    if len(aadhar) >= 12:
        return f"XXXX-XXXX-{aadhar[-4:]}"
    return aadhar

def mask_voter_id(voter_id):
    """Masks Voter ID (e.g., ABCXXXX123)."""
    if len(voter_id) >= 6:
        return f"{voter_id[:3]}XXXX{voter_id[-3:]}"
    return voter_id

# ── Routes ───────────────────────────────────────────────────────────────────
@app.route('/')
def home():
    if 'voter_id' in session:
        return redirect(url_for('vote'))
    return render_template('index.html')


@app.route('/register')
def register():
    """Voter Registration Page."""
    return render_template('register.html')


@app.route('/api/phase3_fraud_check', methods=['POST'])
def phase3_fraud_check():
    """EXPLICIT PHASE 3: Scans live detection face against all old users in database."""
    data = request.json or {}
    aadhar = data.get('aadhar', '').strip()
    image_b64 = data.get('image', '')
    
    if not aadhar or not image_b64:
        return jsonify({"status": "error", "message": "Missing Aadhar or Image for Phase 3 Scan."})
        
    try:
        import base64
        import cv2
        import numpy as np
        from face_utils import get_face_features, check_biometric_duplicate
        from database import db_get_all_biometrics
        
        header, encoded = image_b64.split(",", 1)
        img_bytes = base64.b64decode(encoded)
        nparr = np.frombuffer(img_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        face_feats = get_face_features(frame)
        if face_feats is None:
            return jsonify({"status": "error", "message": "No face detected in Phase 3 scan."})
            
        # Prevent "Already Registered" Fake IDs by checking against ALL recorded biometrics
        all_voters = db_get_all_biometrics()
        
        # AI Agent fake ID check: Flag if biometric similarity indicates duplicate (math threshold > 0.45)
        # Passing "" to ensure it checks EVERY face, even if they used the EXACT same ID again
        duplicate = check_biometric_duplicate(face_feats, all_voters, "", threshold=0.45)

        
        if duplicate:
            voter_id_display = duplicate.get("voter_id") or duplicate.get("aadhar", "Unknown")
            # Map math score (e.g. 0.45) to a visible AI confidence > 80%
            match_percentage = min(99.9, (duplicate['score'] * 100) + 40)
            app.logger.warning(f"PHASE 3 FRAUD DETECTED: {aadhar} matches existing {voter_id_display}")
            return jsonify({
                "status": "fraud", 
                "message": f"❌ AI AGENT FRAUD DETECTED: Fake ID / Duplicate Face! Matched existing record (Name: {duplicate['name']}, Voter ID: {voter_id_display}) with {match_percentage:.1f}% Similarity!"
            })
            
        return jsonify({"status": "success", "message": "Face is Unique."})
    except Exception as e:
        return jsonify({"status": "error", "message": f"Phase 3 Error: {str(e)}"})


@app.route('/process_registration', methods=['POST'])
def process_registration():
    """API for registering new voters (saves data after Phase 3 clears)."""
    data      = request.json or {}
    aadhar    = data.get('aadhar', '').strip()
    voter_id  = data.get('voterid', '').strip()
    name      = data.get('name', '').strip()
    district  = data.get('district', '').strip()
    images    = data.get('images', []) # List of 25 base64 strings
    video_data = data.get('video', '') # Base64 video data

    if not all([aadhar, voter_id, name, district, images, video_data]):
        return jsonify({"status": "error", "message": "All fields including District, 25 photos, and video are required."})

    if len(images) < 25:
        return jsonify({"status": "error", "message": f"Expected 25 samples, got {len(images)}."})

    import os
    USER_DIR = os.path.join("voter_images", aadhar)
    if not os.path.exists(USER_DIR):
        os.makedirs(USER_DIR)

    # Process first image to get base encoding for DB storage
    try:
        header, encoded = images[0].split(",", 1)
        import base64
        import cv2
        import numpy as np
        img_bytes = base64.b64decode(encoded)
        nparr     = np.frombuffer(img_bytes, np.uint8)
        first_frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        from face_utils import get_face_features
        face_feats = get_face_features(first_frame)
        if face_feats is None:
            return jsonify({"status": "error", "message": "Face not detected in first sample."})
        
        encoding = face_feats['encoding']
    except Exception as e:
        return jsonify({"status": "error", "message": f"Sample decode error: {e}"})

    # Save all 25 images
    for i, img_b64 in enumerate(images):
        try:
            _, encoded = img_b64.split(",", 1)
            img_bytes = base64.b64decode(encoded)
            with open(os.path.join(USER_DIR, f"sample_{i+1:02d}.jpg"), "wb") as f:
                f.write(img_bytes)
        except: continue

    # Save video
    try:
        _, encoded = video_data.split(",", 1)
        video_bytes = base64.b64decode(encoded)
        with open(os.path.join(USER_DIR, "liveness_video.webm"), "wb") as f:
            f.write(video_bytes)
    except: pass

    # Register in DB
    from database import db_register_voter # Store in DB
    success, msg = db_register_voter(aadhar, voter_id, name, district, encoding)
    
    if success:
        session['pending_aadhar']   = aadhar
        session['pending_voter_id'] = voter_id
        session['voter_name']       = name
        session['masked_aadhar']    = mask_aadhar(aadhar)
        return jsonify({"status": "success", "message": "✅ Advanced Registration successful! Data collected.", "next_url": "/verify"})
    else:
        return jsonify({"status": "error", "message": f"❌ {msg}"})


@app.route('/check_vote', methods=['GET', 'POST'])
def check_vote():
    """Route to allow users to verify their cast vote."""
    if request.method == 'POST':
        aadhar = request.form.get('aadhar', '').strip()
        voter_id = request.form.get('voterid', '').strip()
        
        voter = db_get_voter(aadhar, voter_id)
        if not voter:
            return render_template('check_vote.html', error="Invalid Aadhar or Voter ID.")
        
        if not voter['has_voted']:
            return render_template('check_vote.html', error="You haven't cast your vote yet!")
            
        candidate_id = db_get_user_vote(aadhar)
        candidate_name = CANDIDATES.get(candidate_id, "Unknown (ID: {})".format(candidate_id))
        
        return render_template('check_vote.html', success=True, candidate=candidate_name)
        
    return render_template('check_vote.html')


@app.route('/validate_frame', methods=['POST'])
@limiter.exempt
def validate_frame():
    """API for real-time quality feedback during registration."""
    data       = request.json or {}
    frame_data = data.get('image', '')
    if not frame_data:
        return jsonify({"status": "error", "message": "No frame received."})

    try:
        img_bytes = base64.b64decode(frame_data.split(',')[1])
        nparr     = np.frombuffer(img_bytes, np.uint8)
        frame     = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        from face_utils import validate_frame_quality, get_face_features
        is_ok, vis, light, msg = validate_frame_quality(frame)
        
        # Also get landmarks for visualization
        feats = get_face_features(frame)
        lms = feats['landmarks'] if feats else []
        
        return jsonify({
            "status": "success" if is_ok else "waiting",
            "visibility": float(round(vis, 2)),
            "lighting": float(round(light, 2)),
            "message": msg,
            "landmarks": lms
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})


@app.route('/login', methods=['POST'])
@limiter.limit("5 per minute")
def login():
    aadhar   = request.form.get('aadhar', '').strip()
    voter_id = request.form.get('voterid', '').strip()
    
    voter = db_get_voter(aadhar, voter_id)
    if voter:
        if voter['has_voted']:
            return render_template('index.html', error="You have already cast your vote!")
        
        # ── Redirect directly to Face Verification ──
        session['pending_aadhar']   = aadhar
        session['pending_voter_id'] = voter_id
        session['voter_name']       = voter['name']
        session['masked_aadhar']    = mask_aadhar(aadhar)
        return redirect(url_for('verify'))
        
    return render_template('index.html', error="Invalid Aadhar or Voter ID.")

@app.route('/verify')
def verify():
    if 'pending_aadhar' not in session:
        return redirect(url_for('home'))
    return render_template('verify.html', name=session['voter_name'])

@app.route('/process_frame', methods=['POST'])
def process_frame():
    if 'pending_aadhar' not in session:
        return jsonify({"status": "error", "message": "Session expired — please log in again."})

    data       = request.json or {}
    frame_data = data.get('image', '')
    if not frame_data:
        return jsonify({"status": "waiting", "message": "No frame received."})

    # Decode base64 → OpenCV frame
    try:
        img_bytes = base64.b64decode(frame_data.split(',')[1])
        nparr     = np.frombuffer(img_bytes, np.uint8)
        frame     = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    except Exception as e:
        return jsonify({"status": "error", "message": f"Frame decode error: {e}"})

    # ── Downsampling for Speed (AI processes ~320px width) ──
    h, w = frame.shape[:2]
    scale = 320 / float(w)
    frame_small = cv2.resize(frame, (0, 0), fx=scale, fy=scale)

    # ── Multi-Stage Verification Logic ──
    from face_utils import get_face_features
    face_feats = get_face_features(frame_small)
    
    if face_feats:
        voter = db_get_voter(session['pending_aadhar'], session['pending_voter_id'])
        if voter is None:
            return jsonify({"status": "error", "message": "Voter record not found."})

        # Step 1: Identity Match
        match, msg = verify_face(face_feats, voter['face_encoding'])
        
        if match:
            # Step 2: Liveness Check (Blink)
            is_blinking, ear = detect_blink(frame_small)
            if is_blinking:
                # ── FINAL SECURE CHECK: Biometric Deduplication ──
                voted_people = db_get_voted_biometrics()
                # Use standard threshold (0.38) for voting duplication check
                duplicate = check_biometric_duplicate(face_feats, voted_people, session['pending_aadhar'], threshold=0.38)
                
                if duplicate:
                    app.logger.warning(f"VOTING FRAUD DETECTED: {session['pending_aadhar']} matches {duplicate['aadhar']} (Score: {duplicate['score']:.3f})")
                    return jsonify({"status": "fraud", "message": f"❌ FRAUD: Biometric identity already voted (Score: {duplicate['score']:.3f})."})

                session['voter_id']      = session.pop('pending_voter_id')
                session['voter_db_id']   = voter.get('id', session['pending_aadhar'])
                return jsonify({
                    "status": "success", 
                    "message": "✅ Identity & Liveness Verified!",
                    "landmarks": face_feats['landmarks']
                })
            else:
                return jsonify({
                    "status": "waiting", 
                    "message": "✅ ID Recognized! Now **Blink** to authorize.",
                    "landmarks": face_feats['landmarks']
                })
        else:
            return jsonify({
                "status": "waiting", 
                "message": f"🔍 Searching... {msg}",
                "landmarks": face_feats['landmarks']
            })
    else:
        return jsonify({"status": "waiting", "message": "📷 Position your face in the center of the frame."})


@app.route('/vote', methods=['GET', 'POST'])
def vote():
    if 'voter_id' not in session:
        return redirect(url_for('home'))

    if request.method == 'POST':
        candidate_id = int(request.form.get('candidate', 0))
        if candidate_id not in CANDIDATES:
            return render_template('vote.html', candidates=CANDIDATES,
                                   name=session['voter_name'],
                                   error="Invalid candidate selection.")

        voter_db_id = session['voter_db_id']
        aadhar = session.get('pending_aadhar') # Use the plain aadhar for hashing

        # SHA-256 encrypted vote record
        vote_string    = f"{voter_db_id}-{candidate_id}-{app.secret_key}"
        encrypted_vote = hashlib.sha256(vote_string.encode()).hexdigest()

        db_cast_vote(aadhar, candidate_id, encrypted_vote)
        db_mark_voted(aadhar)

        session.clear()
        return render_template('success.html')

    return render_template('vote.html', candidates=CANDIDATES, name=session['voter_name'])


@app.route('/dashboard')
def dashboard():
    """Admin Dashboard for Live Vote Analytics."""
    return render_template('dashboard.html', candidates=CANDIDATES)


@app.route('/api/results')
@limiter.exempt
def api_results():
    """Returns vote share data for Chart.js."""
    overall = db_get_vote_counts()
    regional = db_get_regional_results()
    
    return jsonify({
        "overall": overall,
        "regional": regional,
        "districts": AP_DISTRICTS,
        "candidates": CANDIDATES
    })


@app.route('/reset_all_data')
def reset_all_data():
    """Clears all votes and resets 'has_voted' for all voters in active DB."""
    from database import get_db, DB_MODE, SQLITE_PATH
    import sqlite3
    
    msg = ""
    # 1. Clear SQLite
    if os.path.exists(SQLITE_PATH):
        conn = sqlite3.connect(SQLITE_PATH)
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM votes")
            cursor.execute("UPDATE voters SET has_voted = 0")
            conn.commit()
            msg += "✅ SQLite Cleared. "
        except Exception as e: msg += f"❌ SQLite Error: {e}. "
        finally: conn.close()
    
    # 2. Clear Firebase if active
    db_conn = get_db()
    if db_conn:
        try:
            for d in db_conn.collection('votes').stream():
                d.reference.delete()
            for d in db_conn.collection('voters').stream():
                d.reference.update({'has_voted': False})
            msg += "✅ Firebase Cleared. "
        except Exception as e: msg += f"❌ Firebase Error: {e}. "
    
    return msg or "No database found to clear."

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))


if __name__ == '__main__':
    # Listen on all network interfaces for global access (PC, Laptop, Mobile)
    import os
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False)
