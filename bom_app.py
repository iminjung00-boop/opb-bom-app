import streamlit as st
import pdfplumber
import pandas as pd
import re
import os

# 1. 페이지 설정 및 버전 정의
APP_VERSION = "V 1.4.5 (CN)"
LAST_UPDATE = "2026.04.13"

st.set_page_config(page_title=f"SMC OPB BOM 系统 {APP_VERSION}", layout="wide")

def show_updates():
    st.info(f"""
    **🚀 {APP_VERSION} 语言支持更新 (Language Update)**
    * **界面中文化**: 所有的主要菜单和项目名称已转换为中文，便于在海外使用。
    * **材质提取优化**: 保持 기존 '* MATERIAL :' 格式，确保生产信息准确。
    * **核心逻辑维持**: 楼层信息、PCB选项、载重/人乘等提取逻辑保持不变。
    """)

if os.path.exists("logo.png"):
    st.image("logo.png", width=150)

st.title(f"SMC OPB 生产 BOM 集成系统 {APP_VERSION}")
show_updates()

uploaded_file = st.file_uploader("请选择要分析的 BOM PDF 文件", type="pdf")

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
    project = re.search(r"공사명\s*[:\s]+([^\n]+)", all_text).group(1).strip() if "공사명" in all_text else "未确认"
    unit = re.search(r"호기번호\s*[:\s]+([A-Z0-9]+)", all_text).group(1).strip() if "호기번호" in all_text else "未确认"

    st.header(f"📊 项目: {project} ({unit})")

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
        
        # (1) 층수 정보
        total_floors_display = "未确认"
        a2000_area = re.search(r"A2000.*?TOTAL\s*FLOOR(.*?)(?=FRONT\s*STOP\s*FLOOR|HX\s*1000|C2620|$)", all_text, re.DOTALL | re.IGNORECASE)
        if a2000_area:
            raw_floors = a2000_area.group(1).strip()
            total_floors_display = "TOTAL FLOOR " + re.sub(r'\s+', ' ', raw_floors).strip()

        # (2) 인승/용량 및 열림방향
        person_match = re.search(r"(\d+)\s*인승", all_text)
        capacity_match = re.search(r"(\d+)\s*kg", all_text)
        name_plate_info = f"{person_match.group(1)}人乘 / {capacity_match.group(1)}kg" if person_match and capacity_match else "未确认"
        open_dir_match = re.search(r"열림방향(?:\(MAIN\))?\s*[:\s]*([가-힣A-Z/]+)", all_text)
        open_direction = open_dir_match.group(1).strip() if open_dir_match else "未确认"

        # (3) MATERIAL 재질 정보 (요청 포맷 유지)
        material_info = "无数据"
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

        # (4) OPB 타입
        opb_spec = "无数据"
        target_row = df[df.astype(str).apply(lambda x: x.str.contains('E280A')).any(axis=1)]
        if not target_row.empty:
            row_content = " ".join(target_row.values.flatten().astype(str))
            spec_find = re.search(r"OPB\s*([SD]\s*\d\s*\d\s*\d\s*[A-Z]?)", row_content, re.IGNORECASE)
            if spec_find: opb_spec = re.sub(r'\s+', '', spec_find.group(1))

        # (5) PCB 옵션
        pcb_option = "无数据"
        pcb_row = df[df.astype(str).apply(lambda x: x.str.contains('E280A16')).any(axis=1)]
        if not pcb_row.empty:
            pcb_text = " ".join(pcb_row.values.flatten().astype(str)).replace('\n', '')
            pcb_match = re.search(r"(GT[\s,.]*MAIN.*?G/S)", pcb_text, re.IGNORECASE)
            if pcb_match: pcb_option = re.sub(r'\s+', ' ', pcb_match.group(1)).strip()

        # (6) 기준층 및 기타
        base_floor_match = re.search(r"기준층\s*[:\s]*([0-9A-Z]+)", all_text)
        base_floor = base_floor_match.group(1).strip() if base_floor_match else "未确认"
        indicator_match = re.search(r"INDICATOR\s*DATA\s*[:\s]*([^\n]+)", all_text, re.IGNORECASE)
        indicator_text = indicator_match.group(1).strip() if indicator_match else "无数据"

        # 4. 화면 출력 (중국어 변환)
        st.subheader("⚠️ 生产关键注意事项 (Key Notes)")
        c_w1, c_w2 = st.columns(2)
        with c_w1:
            parking_check = re.search(r"기준층\s*버튼\s*PARKING\s*SW\s*적용\s*\(([^)]+)\)", all_text)
            parking_val = parking_check.group(1) if parking_check else "未应用"
            if parking_val != "未应用": st.error(f"🅿️ **基准层 PARKING SW 应用: {parking_val}**")
        with c_w2:
            if "면취" in all_text: st.error("🔧 **DIS OPB 下部需进行倒角加工 (C0.5)**")
            if "비상통화장치" in all_text: st.error("🚨 **应用紧急通话装置项目**")

        st.divider()

        st.subheader("📋 核心制作参数摘要 (Specifications)")
        m_c1, m_c2, m_c3 = st.columns([2, 1, 1]) 
        with m_c1: 
            st.markdown(f"**🏢 总楼层信息 (TOTAL FLOOR)**")
            st.caption(total_floors_display) 
        with m_c2: st.metric("📍 基准层位置", base_floor)
        with m_c3: st.metric("🚪 开门方向", open_direction)

        st.info(f"👥 **载重/人乘:** {name_plate_info}")

        st.divider()

        st.subheader("🎛️ OPB 及 PCB 详细制作参数")
        box_match = re.search(r"BOX\s*[:\s]*([\d\s*xX,]{5,20})", all_text, re.IGNORECASE)
        sw_dwg = re.search(r"S/W\s*PANEL.*?DWG\s*NO\.?\s*[:\s]*([0-9A-Z]+)", all_text, re.IGNORECASE | re.DOTALL)
        
        r1_c1, r1_c2, r1_c3, r1_c4 = st.columns(4)
        with r1_c1: st.info(f"✨ **OPB 类型**\n\n{opb_spec}")
        with r1_c2: st.error(f"🎨 **表面材质规格**\n\n{material_info}") 
        with r1_c3: st.info(f"📏 **底盒尺寸 (BOX)**\n\n{box_match.group(1).strip() if box_match else '无数据'}")
        with r1_c4: st.info(f"📄 **图纸编号**\n\n{sw_dwg.group(1) if sw_dwg else '无数据'}")

        r2_c1, r2_c2, r2_c3, r2_c4 = st.columns(4)
        with r2_c1: st.info(f"📟 **显示器数据**\n\n{indicator_text}")
        with r2_c2: st.warning(f"🔋 **PCB 选项**\n\n{pcb_option}")
        with r2_c3: st.success(f"❄️ **空调 (Air-con):** {'✅ 应用' if '에어컨' in all_text else '❌ 未应用'}")
        with r2_c4: st.success(f"⏭️ **业主跳过 (Skip):** {'✅ 应用' if 'SKIP S/W' in all_text else '❌ 未应用'}")

        st.divider()

        st.subheader("🔘 主要材料投入明细 (核心)")
        target_mask = df.astype(str).apply(lambda x: x.str.contains('BUTTON|버튼|HIP|SJ21|PCB|BOARD|E280|E281|E282', case=False, na=False)).any(axis=1)
        st.table(df[target_mask])

        st.subheader("📦 完整材料清单 (Full BOM)")
        st.dataframe(df, use_container_width=True, hide_index=True)
