import streamlit as st
import pdfplumber
import re
import os

# 1. 페이지 설정
st.set_page_config(page_title="SMC OPB생산 BOM통합 시스템 V 1.0", layout="wide")

st.title("SMC OPB생산 BOM통합 시스템 V 1.0")
st.write("PCB의 IND(인디케이터) 및 SD(표시 사양) 설정값을 집중 분석합니다.")

uploaded_file = st.file_uploader("BOM PDF 업로드", type="pdf")

if uploaded_file:
    with pdfplumber.open(uploaded_file) as pdf:
        all_text = ""
        for page in pdf.pages:
            all_text += (page.extract_text() or "") + "\n"

    # 공사 정보
    project = re.search(r"공사명\s*[:\s]+([^\n]+)", all_text).group(1).strip() if "공사명" in all_text else "미확인"
    st.header(f"📊 {project}")

    # ---------------------------------------------------------
    # 🧩 PCB 상세 설정 (IND/SD) - 요청하신 핵심 기능
    # ---------------------------------------------------------
    st.subheader("🧩 PCB 상세 설정 (IND / SD)")
    
    # IND:X SD:O 또는 IND:X.SD:X.G/S 등 패턴 추출
    # 문래힐스테이트 , 이앤씨벤처  등의 패턴 대응
    main_pcb_match = re.search(r"MAIN.*?OPB.*?(IN[D|V]:?[^,\n]+)", all_text, re.IGNORECASE)
    dis_pcb_match = re.search(r"DIS.*?OPB.*?(IN[D|V]:?[^,\n]+)", all_text, re.IGNORECASE)
    
    col1, col2 = st.columns(2)
    with col1:
        # 메인 OPB PCB 설정값 (예: IND:X SD:O) 
        main_val = main_pcb_match.group(1).strip() if main_pcb_match else "정보 없음"
        st.success(f"🖥️ **MAIN PCB 설정**\n\n{main_val}")
    with col2:
        # 장애자용 OPB PCB 설정값 
        dis_val = dis_pcb_match.group(1).strip() if dis_pcb_match else "미적용"
        st.success(f"♿ **장애자용 PCB 설정**\n\n{dis_val}")

    st.divider()

    # 기타 핵심 제작 규격
    st.subheader("📏 핵심 제작 규격")
    box_match = re.search(r"BOX\s*[:\s]*([\d\s*xX,]{5,20})", all_text, re.IGNORECASE)
    # 이앤씨 현장 규격(164 x 1704) 등 추출 [cite: 165, 189]
    box_val = box_match.group(1).strip() if box_match else "정보 없음"
    
    opb_spec = re.search(r"([SD]\d{3}[A-Z]?[,.]?\s*\d?DIGIT\.?[,.]?\s*G/S)", all_text, re.IGNORECASE)
    # 포에스프라자, 문래힐스테이트 사양 추출 [cite: 82]
    spec_val = opb_spec.group(1).strip() if opb_spec else "정보 없음"

    c1, c2 = st.columns(2)
    with c1:
        st.info(f"📏 **MAIN BOX size:** {box_val}")
    with c2:
        st.info(f"✨ **OPB 사양 코드:** {spec_val}")
        
