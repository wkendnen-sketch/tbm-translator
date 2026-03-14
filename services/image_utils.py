import os
import tempfile
from PIL import Image, ImageOps


def optimize_image(
    input_path: str,
    max_size: int = 1600,
    jpeg_quality: int = 82
) -> str:
    """
    업로드 이미지를 PPT용으로 최적화:
    - EXIF 회전 보정
    - 긴 변 기준 max_size로 축소
    - RGB 변환
    - JPEG 압축 저장
    """
    with Image.open(input_path) as img:
        img = ImageOps.exif_transpose(img)
        img = img.convert("RGB")

        width, height = img.size
        long_side = max(width, height)

        if long_side > max_size:
            scale = max_size / long_side
            new_size = (int(width * scale), int(height * scale))
            img = img.resize(new_size, Image.LANCZOS)

        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
        output_path = tmp.name
        tmp.close()

        img.save(
            output_path,
            format="JPEG",
            quality=jpeg_quality,
            optimize=True
        )

    return output_path


def get_image_size(image_path: str):
    with Image.open(image_path) as img:
        return img.size