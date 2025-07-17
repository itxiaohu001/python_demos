import face_recognition
image = face_recognition.load_image_file("person.jpg")
face_locations = face_recognition.face_locations(image)  # 检测人脸
face_encodings = face_recognition.face_encodings(image, face_locations)  # 128维特征向量