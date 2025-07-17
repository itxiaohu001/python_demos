# 使用ddddocr库（专为验证码优化的模型）
import ddddocr

ocr = ddddocr.DdddOcr(show_ad=False)
with open('E:/Downloads/num.png', 'rb') as f:
    image = f.read()
result = ocr.classification(image)
print(result)  # 输出识别结果