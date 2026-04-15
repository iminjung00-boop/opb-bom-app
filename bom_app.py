import streamlit as st
import pdfplumber
import pandas as pd
import re
import os

# 1. 페이지 설정 및 버전 정의
APP_VERSION = "V 1.4.8 (CN_Final)"
LAST_UPDATE = "2026.04.15"

st.set_page_config(page_title=f"SMC OPB BOM 系统 {APP_VERSION}", layout="wide")

# [중국어 번역 사전]
TRANSLATION_DICT = {
    "BUTTON": "按钮 (Button)", "버튼": "按钮 (Button)",
    "PC BOARD": "电路板 (PCB)", "BOARD": "电路板 (Board)",
    "CABLE": "电缆 (Cable)", "ASSY": "组件 (Assy)",
    "INDICATOR": "显示器 (Indicator)", "인디케이터": "显示器 (Indicator)",
    "PHONE": "电话/对讲 (Phone)", "비상통화": "紧急通话 (Emergency Call)",
    "STICKER": "贴纸 (Sticker)", "스티커": "贴纸 (Sticker)",
    "BOX": "底盒 (Box)", "COVER": "盖板 (Cover)",
    "SCREW": "螺丝 (Screw)", "PLATE": "面板 (Plate)",
    "HARNESS": "线束 (Harness)", "하네스": "线束 (Harness)",
    "스테인레스": "不锈钢 (Stainless)", "헤어라인": "发丝纹 (Hairline)",
    "미러": "镜面 (Mirror)", "장애인": "残疾人 (Disabled)",
    "점자": "盲文 (Braille)", "비상용": "消防员用 (Fireman)",
    "기준층": "基준层 (Main Floor)", "정지층": "停靠层 (Stop Floor)",
    "인승": "人乘 (Persons)", "용량": "载重 (Capacity)",
    "열림방향": "开门方向 (Open Dir)", "면취": "倒角 (Chamfer)",
    "적용": "应用 (Applied)", "미적용": "未应用 (Not Applied)"
}

def translate_content(text):
    if not isinstance(text, str): return text
    translated = text
    for ko, cn in TRANSLATION_DICT.items():
        pattern = re.compile(re.escape(ko), re.IGNORECASE)
        translated = pattern.sub(cn, translated)
    return translated

if os.path.exists("logo.png"):
    st.image("logo.png", width=150)

st.title(f"SMC OPB 生产 BOM 集成系统 {APP_VERSION}")
st.info("系统已修复语法错误，并保持深度汉化功能。")

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

    # 1. 기본 정보 추출
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

        for col in ['자재내역', 'SPEC', '자재번호']:
            if col in df.columns:
                df[col] = df[col].apply(translate_content)

        # 2. 데이터 정밀 추출
        total_floors_display = "未确认"
        a2000_area = re.search(r"A2000.*?TOTAL\s*FLOOR(.*?)(?=FRONT\s*STOP\s*FLOOR|HX\s*1000|C2620|$)", all_text, re.DOTALL | re.IGNORECASE)
        if a2000_area:
            raw_floors = a2000_area.group(1).strip()
            total_floors_display = "TOTAL FLOOR " + translate_content(re.sub(r'\s+', ' ', raw_floors).strip())

        person_match = re.search(r"(\d+)\s*인승", all_text)
        capacity_match = re.search(r"(\d+)\s*kg", all_text)
        name_plate_info = f"{person_match.group(1)}人乘 / {capacity_match.group(1)}kg" if person_match and capacity_match else "未确认"
        
        open_dir_match = re.search(r"열림방향(?:\(MAIN\))?\s*[:\s]*([가-힣A-Z/]+)", all_text)
        open_direction = translate_content(open_dir_match.group(1).strip()) if open_dir_match else "未确认"

        material_info = "无数据"
        lines = all_text.split('\n')
        for i, line in enumerate(lines):
            if "MATERIAL" in line.upper():
                context = line + (lines[i+1] if i+1 < len(lines) else "")
                mat_match = re.search(r"MATERIAL\s*[:\s]*([가-힣\s\-0-9A-Z\(\)]+)", context, re.IGNORECASE)
                if mat_match:
                    found_mat = mat_match.group(1).strip()
                    material_info = f"* MATERIAL : {translate_content(found_mat)}"
                    break

        st.subheader("📋 核心制作参数摘要 (Specifications)")
        m_c1, m_c2, m_c3 = st.columns([2, 1, 1]) 
        with m_c1: 
            st.markdown(f"**🏢 总楼层信息 (TOTAL FLOOR)**")
            st.caption(total_floors_display) 
        with m_c2: 
            base_floor_match = re.search(r"기준층\s*[:\s]*([0-9A-Z]+)", all_text)
            st.metric("📍 基准层位置", base_floor_match.group(1).strip() if base_floor_match else "未确认")
        with m_c3: st.metric("🚪 开门方向", open_direction)

        st.divider()

        st.subheader("🎛️ OPB 及 PCB 详细制作参数")
        r1_c1, r1_c2, r1_c3, r1_c4 = st.columns(4)
        with r1_c1:
            target_row = df[df.astype(str).apply(lambda x: x.str.contains('E280A')).any(axis=1)]
            opb_spec = "无数据"
            if not target_row.empty:
                spec_find = re.search(r"OPB\s*([SD]\s*\d\s*\d\s*\d\s*[A-Z]?)", str(target_row.values), re.IGNORECASE)
                if spec_find: opb_spec = re.sub(r'\s+', '', spec_find.group(1))
            st.info(f"✨ **OPB 类型**\n\n{opb_spec}")
        with r1_c2: st.error(f"🎨 **表面材质规格**\n\n{material_info}") 
        with r1_c3: 
            box_match = re.search(r"BOX\s*[:\s]*([\d\s*xX,]{5,20})", all_text, re.IGNORECASE)
            st.info(f"📏 **底盒尺寸 (BOX)**\n\n{box_match.group(1).strip() if box_match else '无数据'}")
        with r1_c4: 
            sw_dwg = re.search(r"S/W\s*PANEL.*?DWG\s*NO\.?\s*[:\s]*([0-9A-Z]+)", all_text, re.IGNORECASE | re.DOTALL)
            st.info(f"📄 **图纸编号**\n\n{sw_dwg.group(1) if sw_dwg else '无数据'}")

        st.divider()

        df_display = df.copy()
        df_display.columns = ["区块(Block)", "材料编号(No)", "材料明细(Description)", "规格(Spec)", "尺寸(Size)", "图纸编号(DWG No)"]

        st.subheader("🔘 主要材料投入明细 (核心)")
        target_mask = df.astype(str).apply(lambda x: x.str.contains('按钮|电路板|贴纸|组件|电缆|E280|E281|E282', case=False, na=False)).any(axis=1)
        st.table(df_display[target_mask])

        st.subheader("📦 完整材料清单 (Full BOM)")
        st.dataframe(df_display, use_container_width=True, hide_index=True)
