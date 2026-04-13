import streamlit as st
import pdfplumber
import pandas as pd
import re
import os

# 1. 페이지 설정 및 버전 정의
APP_VERSION = "V 1.4.3"
LAST_UPDATE = "2026.04.13"

st.set_page_config(page_title=f"SMC OPB BOM 시스템 {APP_VERSION}", layout="wide")

def show_updates():
    st.info(f"""
    **🚀 {APP_VERSION} 시스템 복구 및 재질 출력 최적화 ({LAST_UPDATE})**
    * **코드 에러 해결**: 불필요한 시스템 태그를 제거하여 NameError 및 실행 오류 완벽 차단
    * **이미지 맞춤형 재질 출력**: 요청하신 대로 '* MATERIAL : [재질명]' 형식으로 고정 출력
    * **데이터 무결성**: 층수(FRONT STOP 이전), PCB 옵션, 인승/용량 등 기존 로직 완벽 유지
    """)

if os.path.exists("logo.png"):
    st.image("logo.png", width=150)

st.title(f"SMC OPB생산 BOM통합 시스템 {APP_VERSION}")
show_updates()

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

    # 2. 기본 정보 추출
    project = re.search(r"공사명\s*[:\s]+([^\n]+)", all_text).group(1).strip() if "공사명" in all_text else "미확인"
    unit = re.search(r"호기번호\s*[:\s]+([A-Z0-9]+)", all_text).group(1).strip() if "호기번호" in all_text else "미확인"

    st.header(f"📊 {project} ({unit})")

    if all_tables:
        df_raw = pd.DataFrame(all_tables)
        header_idx = 0
        for i, row in df_raw.iterrows():
            if any(k in str(row.values) for k in ['BLOCK', '자재번호', '자재내역']):
                header_idx = i
                break
        
        df_raw.columns = df_raw.iloc[header_idx]
        df = df_raw.iloc[header_idx+1:].reset_index(drop=True).dropna(axis=1, how='all')
        df.columns = [str(c).replace('\n', ' ') for c in df.columns]

        if '협력사' in df.columns:
            df = df.drop(columns=['협력사'])

        # ---------------------------------------------------------
        # 3. 데이터 정밀 추출 로직
        # ---------------------------------------------------------
        
        # (1) A2000 층수 정보 (FRONT STOP FLOOR 이전까지)
        total_floors_display = "미확인"
        a2000_area = re.search(r"A2000.*?TOTAL\s*FLOOR(.*?)(?=FRONT\s*STOP\s*FLOOR|HX\s*1000|C2620|$)", all_text, re.DOTALL | re.IGNORECASE)
        if a2000_area:
            raw_floors = a2000_area.group(1).strip()
            total_floors_display = "TOTAL FLOOR " + re.sub(r'\s+', ' ', raw_floors).strip()

        # (2) 인승/용량 및 열림방향
        person_match = re.search(r"(\d+)\s*인승", all_text)
        capacity_match = re.search(r"(\d+)\s*kg", all_text)
        name_plate_info = f"{person_match.group(1)}인승 / {capacity_match.group(1)}kg" if person_match and capacity_match else "미확인"
        open_dir_match = re.search(r"열림방향(?:\(MAIN\))?\s*[:\s]*([가-힣A-Z/]+)", all_text)
        open_direction = open_dir_match.group(1).strip() if open_dir_match else "미확인"

        # (3) MATERIAL 재질 정보 추출
        material_info = "정보 없음"
        lines = all_text.split('\n')
        for i, line in enumerate(lines):
            if "MATERIAL" in line.upper():
                context = line + (lines[i+1] if i+1 < len(lines) else "")
                mat_match = re.search(r"MATERIAL\s*[:\s]*([가-힣\s\-0-9A-Z\(\)]+)", context, re.IGNORECASE)
                if mat_match:
                    found_mat = mat_match.group(1).strip()
                    if any(k in found_mat for k in ["스테인레스", "헤어라인", "미러", "SUS", "H/L", "S/L"]):
                        material_info = f"* MATERIAL : {found_mat}"
                        break

        # (4) OPB 타입 (E280A)
        opb_spec = "정보 없음"
        target_row = df[df.astype(str).apply(lambda x: x.str.contains('E280A')).any(axis=1)]
        if not target_row.empty:
            row_content = " ".join(target_row.values.flatten().astype(str))
            spec_find = re.search(r"OPB\s*([SD]\s*\d\s*\d\s*\d\s*[A-Z]?)", row_content, re.IGNORECASE)
            if spec_find: opb_spec = re.sub(r'\s+', '', spec_find.group(1))

        # (5) PCB 옵션 정보 (E280A16)
        pcb_option = "정보 없음"
        pcb_row = df[df.astype(str).apply(lambda x: x.str.contains('E280A16')).any(axis=1)]
        if not pcb_row.empty:
            pcb_text = " ".join(pcb_row.values.flatten().astype(str)).replace('\n', '')
            pcb_match = re.search(r"(GT[\s,.]*MAIN.*?G/S)", pcb_text, re.IGNORECASE)
            if pcb_match: pcb_option = re.sub(r'\s+', ' ', pcb_match.group(1)).strip()

        # (6) 기준층 및 인디케이터
        base_floor_match = re.search(r"기준층\s*[:\s]*([0-9A-Z]+)", all_text)
        base_floor = base_floor_match.group(1).strip() if base_floor_match else "미확인"
        indicator_match = re.search(r"INDICATOR\s*DATA\s*[:\s]*([^\n]+)", all_text, re.IGNORECASE)
        indicator_text = indicator_match.group(1).strip() if indicator_match else "정보 없음"
        aircon = "✅ 적용" if any(k in all_text for k in ["AIR-CON", "에어컨"]) else "❌ 미적용"
        skip_sw = "✅ 적용" if any(k in all_text for k in ["SKIP S/W", "오너스킵"]) else "❌ 미적용"

        # 4. 화면 출력
        st.subheader("⚠️ 생산 핵심 주의사항")
        c_w1, c_w2 = st.columns(2)
        with c_w1:
            parking_check = re.search(r"기준층\s*버튼\s*PARKING\s*SW\s*적용\s*\(([^)]+)\)", all_text)
            parking_val = parking_check.group(1) if parking_check else "미적용"
            if parking_val != "미적용": st.error(f"🅿️ **기준층 PARKING SW 적용: {parking_val}**")
        with c_w2:
            if "면취" in all_text: st.error("🔧 **DIS OPB 하부 면취가공 필수 (C0.5)**")
            if "비상통화장치" in all_text: st.error("🚨 **비상통화장치 적용 현장**")

        st.divider()

        st.subheader("📋 핵심 제작 사양 요약")
        m_c1, m_c2, m_c3 = st.columns([2, 1, 1]) 
        with m_c1: 
            st.markdown(f"**🏢 전체 층수 정보 (TOTAL FLOOR)**")
            st.caption(total_floors_display) 
        with m_c2: st.metric("📍 기준층 위치", base_floor)
        with m_c3: st.metric("🚪 열림방향", open_direction)

        st.info(f"👥 **인승/용량:** {name_plate_info}")

        st.divider()

        st.subheader("🎛️ OPB 및 PCB 상세 제작 사양")
        box_match = re.search(r"BOX\s*[:\s]*([\d\s*xX,]{5,20})", all_text, re.IGNORECASE)
        sw_dwg = re.search(r"S/W\s*PANEL.*?DWG\s*NO\.?\s*[:\s]*([0-9A-Z]+)", all_text, re.IGNORECASE | re.DOTALL)
        
        r1_c1, r1_c2, r1_c3, r1_c4 = st.columns(4)
        with r1_c1: st.info(f"✨ **OPB 타입**\n\n{opb_spec}")
        with r1_c2: st.error(f"🎨 **표판 재질 사양**\n\n{material_info}") 
        with r1_c3: st.info(f"📏 **BOX SIZE**\n\n{box_match.group(1).strip() if box_match else '정보 없음'}")
        with r1_c4: st.info(f"📄 **도면 번호**\n\n{sw_dwg.group(1) if sw_dwg else '정보 없음'}")

        r2_c1, r2_c2, r2_c3, r2_c4 = st.columns(4)
        with r2_c1: st.info(f"📟 **인디케이터**\n\n{indicator_text}")
        with r2_c2: st.warning(f"🔋 **PCB 옵션**\n\n{pcb_option}")
        with r2_c3: st.success(f"❄️ **에어컨:** {aircon}")
        with r2_c4: st.success(f"⏭️ **오너스킵:** {skip_sw}")

        st.divider()

        st.subheader("🔘 주요 자재 투입 명세 (핵심)")
        target_mask = df.astype(str).apply(lambda x: x.str.contains('BUTTON|버튼|HIP|SJ21|PCB|BOARD|E280|E281|E282', case=False, na=False)).any(axis=1)
        st.table(df[target_mask])

        st.subheader("📦 전체 자재 리스트")
        st.dataframe(df, use_container_width=True, hide_index=True)
