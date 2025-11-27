import os
import io
import time
import base64
import json
from datetime import datetime, timezone
from flask import Flask, jsonify, request, send_from_directory, redirect, url_for, render_template
import random 


from supabase import create_client, Client 

import numpy as np
import face_recognition
import cv2


SUPABASE_URL = os.environ.get('__supabase_url') if os.environ.get('__supabase_url') else 'https://sfruzhtdqyybjxqohoxf.supabase.co'
SUPABASE_KEY = os.environ.get('__supabase_key') if os.environ.get('__supabase_key') else 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InNmcnV6aHRkcXl5Ymp4cW9ob3hmIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1ODIxMTE4NiwiZXhwIjoyMDczNzg3MTg2fQ.e00_p4dp9hQj-E89BacqZNEbjkqw57hQFGsS50sa82E'
# ---------------------------------------------------------------------------------------------------------
ENCODE_FILE = os.path.join(os.path.dirname(__file__), "EncodeFile.npz")


supabase = None
try:
    
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("✅ Supabase Client Initialized.")
except Exception as e:
    print(f"❌ Error initializing Supabase client: {e}")

app = Flask(__name__, static_folder="../frontend", template_folder="../frontend")


known_face_encodings = []
studentIds = np.array([])

if os.path.exists(ENCODE_FILE):
    try:
        npzfile = np.load(ENCODE_FILE, allow_pickle=True)
        known_face_encodings = npzfile["encodings"]
       
        studentIds = npzfile["ids"]
        print(f"✅ Loaded {len(studentIds)} known faces.")
    except Exception as e:
        print(f"❌ Error loading EncodeFile.npz: {e}")
else:
    print(f"❌ EncodeFile.npz not found at {ENCODE_FILE}. Please run encoding script.")

# --- Liveness Challenges (Basic Example) ---
CHALLENGES = {
    "BLINK": "Blink your eyes repeatedly.",
    "HEAD_TURN_LEFT": "Slowly turn your head to the left.",
    "MOUTH_OPEN": "Open and close your mouth once.",
}
SPOOF_COUNT = 0 




def verify_liveness(frames, challenge):
    global SPOOF_COUNT
    
   
    if len(frames) < 5: 
        SPOOF_COUNT += 1
        
        return False, "Verification failed (Not enough frames captured). Please hold steady and ensure continuous visibility for a moment."

    
    face_count = 0
    
    frame_copies = [io.BytesIO(f.getvalue()) for f in frames] 

    for frame in frame_copies:
        
        img_array = np.frombuffer(frame.read(), np.uint8)
        img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

        if img is None:
            continue
            
        
        face_locations = face_recognition.face_locations(img)
        if face_locations:
            face_count += 1

   
    for f in frames:
        f.seek(0)
    

    if face_count < len(frames) * 0.9: 
        SPOOF_COUNT += 1
        
        return False, "Face inconsistency detected. This happens with static photos or low-quality video feed."

    

    return True, "Liveness verified (simulated)."


def find_match(frames):
    
    
    frame_copies = [io.BytesIO(f.getvalue()) for f in frames] 
    
    for frame in frame_copies:
        
        img_array = np.frombuffer(frame.read(), np.uint8)
        img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        
        if img is None:
            continue
            
        face_locations = face_recognition.face_locations(img)
        if not face_locations:
            continue

        
        face_encodings = face_recognition.face_encodings(img, face_locations)
        if not face_encodings:
            continue
            
        face_encoding = face_encodings[0]

       
        id_list = [str(i) for i in studentIds]
        
        matches = face_recognition.compare_faces(known_face_encodings, face_encoding, tolerance=0.5) 
        
        if True in matches:
            first_match_index = matches.index(True)
            match_id = id_list[first_match_index] 
            
            
            
            for f in frames:
                f.seek(0)
            
            return match_id
            
   
    for f in frames:
        f.seek(0)
        
    return None

# --- Flask Routes ---

@app.route("/")
def index():
    """Serves the main login page."""
    return send_from_directory(app.static_folder, "index.html")

@app.route("/attendance")
def attendance():
    """Serves the attendance portal page."""
    return send_from_directory(app.static_folder, "attendance.html")

# --- API Endpoints ---

@app.route("/api/login", methods=["POST"])
def api_login():
    """Handles student ID verification."""
    try:
        data = request.get_json()
        student_id = data.get("student_id")
        
        if not student_id:
            return jsonify({"status": "error", "message": "Student ID is required."}), 400

        
        if str(student_id) in [str(i) for i in studentIds]:
            return jsonify({"status": "success", "message": "Login successful."}), 200
        else:
            return jsonify({"status": "error", "message": "Invalid student ID. Please check your roll number."}), 401
    
    except Exception as e:
        print("❗ Login error:", e)
        return jsonify({"status": "error", "message": "Server error during login."}), 500

@app.route("/api/get_challenge", methods=["GET"])
def api_get_challenge():
    """Provides a basic liveness challenge instruction."""
    
    challenge_key = random.choice(list(CHALLENGES.keys()))
    return jsonify({
        "status": "success",
        "challenge": challenge_key,
        "instruction": CHALLENGES[challenge_key]
    }), 200

@app.route("/api/mark_attendance", methods=["POST"])
def api_mark_attendance():
    """Handles the attendance marking process."""
    if not supabase:
        return jsonify({"status": "error", "message": "Database not configured."}), 500
        
    try:
        student_id = request.form.get("student_id")
        challenge = request.form.get("challenge")
        
        if not student_id or not challenge:
            return jsonify({"status": "error", "message": "Missing student ID or challenge."}), 400

        
        frames = []
        for f in request.files:
             if f.startswith("frame_"):
                frames.append(io.BytesIO(request.files[f].read()))
        
       
        is_live, liveness_msg = verify_liveness(frames, challenge)
        if not is_live:
            
            return jsonify({"status": "spoof_detected", "message": f"Spoofing Detected! {liveness_msg}"}), 403
        
        
        matched_id = find_match(frames)
        
        if not matched_id or str(matched_id) != str(student_id):
            return jsonify({"status": "error", "message": "Face not recognized or ID mismatch."}), 401

       
        
       
        res = supabase.table("students").select("name, total_attendance, last_attendance_time").eq("id", student_id).execute()
        student_data = res.data[0] if res.data else None
        
        if not student_data:
            return jsonify({"status": "error", "message": "Student not registered in the database."}), 404

        current_time = datetime.now(timezone.utc)
        
       
        last_att_time_str = student_data.get("last_attendance_time")
        if last_att_time_str:
            
            last_attendance_date = datetime.fromisoformat(last_att_time_str.replace("Z", "+00:00")).date()
            if last_attendance_date == current_time.date():
                return jsonify({
                    "status": "already_marked",
                    "student_id": student_id,
                    "name": student_data["name"],
                    
                    "total_attendance": student_data["total_attendance"],
                    "time": last_att_time_str
                }), 200

       
        new_total = (student_data["total_attendance"] or 0) + 1
        
        current_time_iso = current_time.isoformat().replace("+00:00", "Z")
        
       
        update_res = supabase.table("students").update({
            "total_attendance": new_total,
            "last_attendance_time": current_time_iso,
        }).eq("id", student_id).execute()
        
        if update_res.data:
            return jsonify({
                "status": "success",
                "student_id": student_id,
                "name": student_data["name"],
                
                "total_attendance": new_total,
                "time": current_time_iso
            }), 200
        else:
            print("❗ Supabase Update Error:", update_res.error)
            return jsonify({"status": "error", "message": "Failed to update attendance record."}), 500

    except Exception as e:
        print("❗ Attendance marking error:", e)
        return jsonify({"status": "error", "message": f"An internal server error occurred: {e}"}), 500

@app.route("/api/student_details/<student_id>", methods=["GET"])
def get_student_details(student_id):
    """Fetches student details, including attendance and ranking."""
    if not supabase:
        return jsonify({"status": "error", "message": "Database not configured."}), 500
        
    try:
        
        if str(student_id) not in [str(i) for i in studentIds]:
            return jsonify({"status": "error", "message": "Student ID not found in face data. (Is EncodeFile.npz updated?)"}), 404

        
        res = supabase.table("students").select("id, name, total_attendance, last_attendance_time").eq("id", student_id).execute()
        student_data = res.data[0] if res.data else None
        if not student_data:
            return jsonify({"status": "error", "message": "Student record not found in database."}), 404

       
        all_students_res = supabase.table("students").select("total_attendance, id").order("total_attendance", desc=True).limit(1000).execute()
        all_students = all_students_res.data
        total_students = len(all_students)

       
        rank = "N/A"
        for i, student in enumerate(all_students):
            if str(student["id"]) == str(student_id):
                rank = i + 1
                break

     
        last_att_time_str = student_data.get("last_attendance_time")
        is_already_marked = False
        if last_att_time_str:
            
            last_attendance_date = datetime.fromisoformat(last_att_time_str.replace("Z", "+00:00")).date()
            if last_attendance_date == datetime.now(timezone.utc).date():
                is_already_marked = True

        return jsonify({
            "status": "success",
            "student_details": student_data,
            "rank": rank,
            "total_students": total_students,
            "already_marked_today": is_already_marked
        }), 200

    except Exception as e:
        print("❗ Error fetching student details:", e)
        return jsonify({"status": "error", "message": "Server error while fetching details."}), 500

if __name__ == '__main__':
    app.run(debug=True)
