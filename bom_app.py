import streamlit as st
import pdfplumber
import pandas as pd
import re
import os
from googletrans import Translator # 자동 번역 라이브러리 추가

# 1. 페이지 설정
st.set_page_config(page_title="SMC OPB생산 BOM통합 시스템 V 1.0", layout="wide")

# 번역기 초기화
translator = Translator()

def translate_text(text):
    """중국어가 포함된 경우 한국어로 번역하여 병기"""
    if not text or pd.isna(text):
        return text
    # 한자(중국어) 패턴 감지
    if re.search(r'[\u4e00-\u9fff]', str(text)):
        try:
            translated = translator.translate(text, src='zh-cn', dest='ko')
            return f"{text} (번역: {translated.text})"
        except:
            return text
    return text

if os.path.exists("logo.png"):
    st.image("logo.png", width=150)

st.title("SMC OPB생산 BOM통합 시스템 V 1.0")
st.write("중국어 사양 자동 번역 및 핵심 제작 사양을 분석합니다.")

uploaded_file = st.file_uploader("분석할 BOM PDF 파일을 선택하세요", type="pdf")

if uploaded_file:
    with pdfplumber.open(uploaded_file) as pdf:
        all_text = ""
        all_tables = []
        for page in pdf.pages:
            all_text += (page.extract_text() or "") + "\n"
            table = page.extract_table()
            if table:
                all_tables.extend(table)

    # 2. 정보 추출 및 번역 적용 
    project = re.search(r"공사명\s*[:\s]+([^\n]+)", all_text).group(1).strip() if "공사명" in all_text else "미확인"
    unit = re.search(r"호기번호\s*[:\s]+([A-Z0-9]+)", all_text).group(1).strip() if "호기번호" in all_text else "미확인" [cite: 1]

    st.header(f"📊 {project} ({unit})")

    # 3. 🚨 생산 핵심 주의사항
    st.subheader("⚠️ 생산 핵심 주의사항")
    opb_3t = "3t 적용" in all_text or "3T 적용" in all_text
    emergency_light = "비상통화장치 동작 표시등 적용" in all_text [cite: 7]
    
    col_warn1, col_warn2 = st.columns(2)
    with col_warn1:
        if opb_3t: st.error("🚨 **비표준 사양: OPB 표판 두께 3t 적용**")
        if emergency_light: st.error("🚨 **비상통화장치 동작 표시등 적용 현장**")
    with col_warn2:
        if "면취" in all_text: st.error("🔧 **DIS OPB 하부 면취가공 필수 (C0.5)**") [cite: 7]

    st.divider()

    # 4. 🎛️ 제작 사양 (중국어 자동 번역 적용 섹션)
    st.subheader("🎛️ 상세 제작 사양 (중국어 자동 번역)")
    
    # 에서 가져온 중국어 포함 가능 사양들
    operation_zh = re.search(r"OPERATION\(控制方式\)\s*[:\s]*([^\n]+)", all_text)
    person_zh = re.search(r"PERSON\(人\)\s*[:\s]*([^\n]+)", all_text)
    model_zh = re.search(r"MODEL\(梯型\)\s*[:\s]*([^\n]+)", all_text)

    c1, c2, c3 = st.columns(3)
    with c1:
        val = operation_zh.group(0) if operation_zh else "정보 없음"
        st.info(f"⚙️ **제어방식**\n\n{translate_text(val)}")
    with c2:
        val = person_zh.group(0) if person_zh else "정보 없음"
        st.info(f"👥 **인승 사양**\n\n{translate_text(val)}")
    with c3:
        val = model_zh.group(0) if model_zh else "정보 없음"
        st.info(f"🏗️ **모델명**\n\n{translate_text(val)}")

    st.divider()

    # 5. 자재 리스트 분석 (표 내부 중국어 번역)
    if all_tables:
        df_raw = pd.DataFrame(all_tables)
        header_idx = 0
        for i, row in df_raw.iterrows():
            if any(k in str(row.values) for k in ['품명', 'NAME', '사양']):
                header_idx = i; break
        
        cols = list(df_raw.iloc[header_idx]); new_cols = []
        for i, val in enumerate(cols):
            val = str(val) if val else f"Unknown_{i}"
            if val in new_cols: new_cols.append(f"{val}_{i}")
            else: new_cols.append(val)
        df_raw.columns = new_cols
        df = df_raw.iloc[header_idx+1:].reset_index(drop=True).dropna(axis=1, how='all')

        # 자재내역 및 SPEC 컬럼 번역 적용
        for col in df.columns:
            if any(k in col for k in ['자재내역', 'SPEC', '사양']):
                df[col] = df[col].apply(translate_text)

        st.subheader("🔘 주요 자재 투입 명세 (번역 포함)")
        target_mask = df.astype(str).apply(lambda x: x.str.contains('BUTTON|버튼|HIP|SJ21|PCB|E280A|E281A', case=False, na=False)).any(axis=1)
        st.table(df[target_mask])

        st.subheader("📦 전체 자재 리스트")
        st.dataframe(df, use_container_width=True, hide_index=True)
