from flask import Flask, request, jsonify
from PIL import Image
import io
import requests
from botocore.exceptions import NoCredentialsError
from flasgger import Swagger, swag_from
from flask_cors import CORS, cross_origin
import os

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024
swagger = Swagger(app)
CORS(app)  # 필요에 따라 전체 앱에 기본 설정 적용

@app.route('/upload', methods=['POST'])
@swag_from({
    'responses': {
        200: {
            'description': 'Image resized and uploaded successfully',
            'examples': {
                'application/json': {
                    'message': 'Image resized and uploaded successfully',
                    'response': 'S3 response'
                }
            }
        },
        400: {
            'description': 'Invalid input or error occurred'
        }
    },
    'parameters': [
        {
            'name': 'presignedUrl',
            'in': 'formData',
            'type': 'string',
            'required': True,
            'description': 'Presigned URL to upload the image'
        },
        {
            'name': 'file',
            'in': 'formData',
            'type': 'file',
            'required': True,
            'description': 'Image file to upload'
        }
    ]
})
def resize_upload_image():
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    try:
        # 필수 파라미터 체크
        if 'presignedUrl' not in request.form or 'file' not in request.files:
            return jsonify({'error': 'Missing presignedUrl or file parameter'}), 400

        presignedUrl = request.form['presignedUrl']
        file = request.files['file']

        # 파일 크기 체크
        if file.content_length > MAX_FILE_SIZE:
            return jsonify({'error': 'File size exceeds the 10MB limit'}), 400

        # 고정된 값 설정
        STATIC_QUALITY = 80  # 고정된 이미지 품질 (1-100)
        STATIC_WIDTH = 600   # 고정된 이미지 너비
    
        # 이미지 열기
        img = Image.open(file)
        original_width, original_height = img.size

        # 너비 설정 (고정된 값 사용)
        new_width = min(original_width, STATIC_WIDTH)

        # 높이 비율 유지하며 계산
        new_height = round(original_height * (new_width / float(original_width)))

        # 이미지 리사이즈
        resized_img = img.resize((new_width, new_height))

        # 파일 확장자 추출
        file_extension = os.path.splitext(file.filename)[1].lower()

        # Pillow에서 지원하는 포맷 추출
        format_map = {
            '.jpg': 'JPEG',
            '.jpeg': 'JPEG',
            '.png': 'PNG',
            '.gif': 'GIF',
            '.bmp': 'BMP',
            '.tiff': 'TIFF'
        }
        
        # MIME 타입에 맞는 포맷 설정
        img_format = format_map.get(file_extension, 'JPEG')  # 기본값은 JPEG

        # 이미지 저장을 위한 버퍼 생성
        img_io = io.BytesIO()
        resized_img.save(img_io, format=img_format, quality=STATIC_QUALITY)
        img_io.seek(0)

        # presigned URL로 이미지 업로드
        upload_response = requests.put(presignedUrl, data=img_io, headers={'Content-Type': f'image/{img_format.lower()}'})
        if upload_response.status_code not in [200, 201]:
            return jsonify({'error': 'Failed to upload image to presigned URL'}), 400

        return jsonify({
            'message': 'Image resized and uploaded successfully',
            'response': upload_response.text
        })
    except NoCredentialsError:
        return jsonify({'error': 'Credentials not available'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 400
    
@app.route('/healthcheck', methods=['GET'])
def health_check():
    return jsonify({'check': True}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=False)
