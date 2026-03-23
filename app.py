import os
import tempfile
import traceback
from pathlib import Path

import streamlit as st

from services.translator import translate_batch
from services.ppt_editor import fill_template_ppt
from services.image_utils import optimize_image


st.set_page_config(page_title="다국어 PPT 생성", layout="centered")

st.title("다국어 PPT 생성")
st.caption("사진과 문구를 넣으면 PPT를 만듭니다.")

try:
    api_key = st.secrets["GEMINI_API_KEY"]
except Exception:
    api_key = ""

template_path = "templates/sample_template.pptx"

if not os.path.exists(template_path):
    st.error("필수 파일이 없습니다.")
    st.stop()


# 이미지 최적화 고정값
FIXED_MAX_SIZE = 1600
FIXED_QUALITY = 88


def normalize_uploaded_files(files):
    normalized = []
    for idx, file in enumerate(files):
        normalized.append(
            {
                "id": f"{file.name}_{file.size}_{idx}",
                "name": file.name,
                "bytes": file.getvalue(),
            }
        )
    return normalized


if "uploaded_items" not in st.session_state:
    st.session_state.uploaded_items = []

if "text_map" not in st.session_state:
    st.session_state.text_map = {}


new_files = st.file_uploader(
    "사진 등록",
    type=["jpg", "jpeg", "png"],
    accept_multiple_files=True
)

if new_files:
    existing_ids = {item["id"] for item in st.session_state.uploaded_items}
    for item in normalize_uploaded_files(new_files):
        if item["id"] not in existing_ids:
            st.session_state.uploaded_items.append(item)

uploaded_items = st.session_state.uploaded_items


if uploaded_items:
    kept_items = []

    for idx, item in enumerate(uploaded_items, start=1):
        col1, col2, col3 = st.columns([1.2, 2.4, 1])

        with col1:
            st.image(item["bytes"], width=140)

        with col2:
            current_text = st.session_state.text_map.get(item["id"], "")
            new_text = st.text_input(
                f"{idx}번 문구",
                value=current_text,
                key=f"text_{item['id']}",
                placeholder="예: 지정된 이동통로 통행",
                label_visibility="collapsed",
            )
            st.session_state.text_map[item["id"]] = new_text
            st.markdown(f"<div style='font-size:12px; color:#666;'>{item['name']}</div>", unsafe_allow_html=True)

        with col3:
            if st.button(f"{idx}번 삭제", key=f"delete_{item['id']}", use_container_width=True):
                st.session_state.text_map.pop(item["id"], None)
            else:
                kept_items.append(item)

    st.session_state.uploaded_items = kept_items
    uploaded_items = kept_items

    if uploaded_items:
        generate = st.button("PPT 만들기", use_container_width=True)

        if generate:
            if not api_key:
                st.error("설정을 확인해 주세요.")
                st.stop()

            ko_texts = []
            empty_indexes = []

            for i, item in enumerate(uploaded_items, start=1):
                txt = st.session_state.text_map.get(item["id"], "").strip()
                if not txt:
                    empty_indexes.append(i)
                ko_texts.append(txt)

            if empty_indexes:
                st.error(f"문구가 비어 있는 사진: {empty_indexes}")
                st.stop()

            try:
                with st.spinner("만드는 중..."):
                    image_paths = []

                    for item in uploaded_items:
                        suffix = Path(item["name"]).suffix.lower()
                        if not suffix:
                            suffix = ".jpg"

                        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                            tmp.write(item["bytes"])
                            original_path = tmp.name

                        optimized_path = optimize_image(
                            input_path=original_path,
                            max_size=FIXED_MAX_SIZE,
                            jpeg_quality=FIXED_QUALITY
                        )

                        image_paths.append(optimized_path)

                    items = [{"ko": txt} for txt in ko_texts]

                    translated_items = translate_batch(
                        items=items,
                        api_key=api_key
                    )

                    output_path = fill_template_ppt(
                        template_path=template_path,
                        image_paths=image_paths,
                        translated_items=translated_items
                    )

                with open(output_path, "rb") as f:
                    st.download_button(
                        label="PPT 다운로드",
                        data=f,
                        file_name="result.pptx",
                        mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                        use_container_width=True
                    )

            except Exception as e:
                st.error(f"오류 발생: {str(e)}")
                st.code(traceback.format_exc())

    else:
        st.info("등록된 사진이 없습니다.")

else:
    st.info("사진을 등록하세요.")