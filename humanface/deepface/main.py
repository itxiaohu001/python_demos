from deepface import DeepFace
result = DeepFace.verify(
    img1_path="E:/Downloads/yaoming1.jpg",
    img2_path="E:/Downloads/yaoming2.jpg",
    model_name="Facenet"  # 可选: VGG-Face, OpenFace等
)
print(f"是否同一人: {result['verified']}, 相似度: {result['distance']}")