import os
import tempfile
import traceback
from pathlib import Path

import streamlit as st

from services.translator import translate_batch
from services.ppt_editor import fill_template_ppt
from services.image_utils import optimize_image

st.set_page_config(page_title="PPT 자동 번역 생성기", layout="centered")

st.title("PPT 자동 번역 생성기")
st.caption("사진 업로드 + 한국어 입력 → 중국어/베트남어/미얀마어 번역 후 PPT 생성")

st.subheader("1. Gemini API 키")

default_api_key = " "

api_key = st.text_input(
    "Gemini API Key 입력",
    value=default_api_key,
    type="password",
)

st.subheader("2. 템플릿 확인")

template_path = "templates/sample_template.pptx"

if not os.path.exists(template_path):
    st.error("templates/sample_template.pptx 파일이 없습니다.")
    st.stop()

st.success("템플릿 정상 확인")

st.subheader("3. 사진 업로드")

uploaded_images = st.file_uploader(
    "사진 업로드",
    type=["jpg", "jpeg", "png"],
    accept_multiple_files=True
)

if uploaded_images:
    st.success(f"{len(uploaded_images)}장 업로드됨")

    st.subheader("4. 속도 설정")

    max_size = st.selectbox(
        "사진 해상도 최적화",
        options=[1200, 1600, 1920],
        index=1,
        format_func=lambda x: f"긴 변 {x}px"
    )

    jpeg_quality = st.selectbox(
        "사진 품질",
        options=[75, 82, 88],
        index=1,
        format_func=lambda x: f"JPEG 품질 {x}"
    )

    st.subheader("5. 사진별 한국어 문구 입력")

    ko_texts = []

    for idx, img_file in enumerate(uploaded_images, start=1):
        col1, col2 = st.columns([1, 2])

        with col1:
            st.image(img_file, caption=f"사진 {idx}", width=180)

        with col2:
            st.markdown(f"**{img_file.name}**")
            text = st.text_input(
                f"사진 {idx} 설명",
                key=f"text_{idx}",
                placeholder="예: 지정된 이동통로 통행",
                label_visibility="collapsed"
            )

        ko_texts.append(text)

    generate = st.button("PPT 생성", use_container_width=True)

    if generate:
        if not api_key:
            st.error("Gemini API 키가 필요합니다.")
            st.stop()

        empty_indexes = [i + 1 for i, txt in enumerate(ko_texts) if not txt.strip()]
        if empty_indexes:
            st.error(f"설명이 없는 사진 번호: {empty_indexes}")
            st.stop()

        try:
            with st.spinner("번역 및 PPT 생성 중..."):
                image_paths = []

                for img in uploaded_images:
                    suffix = Path(img.name).suffix.lower()
                    if not suffix:
                        suffix = ".jpg"

                    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                        tmp.write(img.read())
                        original_path = tmp.name

                    optimized_path = optimize_image(
                        input_path=original_path,
                        max_size=max_size,
                        jpeg_quality=jpeg_quality
                    )

                    image_paths.append(optimized_path)

                items = [{"ko": txt.strip()} for txt in ko_texts]

                translated_items = translate_batch(
                    items=items,
                    api_key=api_key
                )

                output_path = fill_template_ppt(
                    template_path=template_path,
                    image_paths=image_paths,
                    translated_items=translated_items
                )

            st.success("PPT 생성 완료")

            with open(output_path, "rb") as f:
                st.download_button(
                    label="PPT 다운로드",
                    data=f,
                    file_name="result.pptx",
                    mime="application/vnd.openxmlformats-officedocument.presentationml.presentation"
                )

            st.subheader("번역 결과 확인")
            for idx, item in enumerate(translated_items, start=1):
                with st.expander(f"사진 {idx} 번역 보기"):
                    st.write(f"한국어: {item['ko']}")
                    st.write(f"중국어: {item['zh']}")
                    st.write(f"베트남어: {item['vi']}")
                    st.write(f"미얀마어: {item['my']}")

        except Exception as e:
            st.error(f"오류 발생: {str(e)}")
            st.code(traceback.format_exc())

else:
    st.info("사진을 업로드하세요.")