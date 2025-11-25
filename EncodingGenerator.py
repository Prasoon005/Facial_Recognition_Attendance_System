import cv2
import face_recognition
import numpy as np
import os

# 👇 Images folder jaha tumhari student images rakhi hai
path = "Images"
images = []
studentIds = []

print("🔹 Loading student images...")

for file in os.listdir(path):
    if file.endswith(('.png', '.jpg', '.jpeg')):
        img = cv2.imread(os.path.join(path, file))
        images.append(img)
        studentIds.append(os.path.splitext(file)[0])  # filename as ID

encodeList = []

print("🔹 Encoding faces...")
for img, sid in zip(images, studentIds):
    rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    encodings = face_recognition.face_encodings(rgb_img)

    if len(encodings) > 0:
        encodeList.append(encodings[0])
        print(f"✅ Encoded {sid}")
    else:
        print(f"⚠️ No face found in {sid}'s image")

# Save encodings + IDs in npz file
np.savez("EncodeFile.npz", encodings=encodeList, ids=studentIds)
print("🎉 EncodeFile.npz generated successfully!")
