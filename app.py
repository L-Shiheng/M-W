import streamlit as st
import pandas as pd
import re
from io import BytesIO

# ==========================================
# 0. 科学常数配置 (NIST Monoisotopic Mass)
# ==========================================
ATOM_MASS = {
    'H': 1.0078250322, 'C': 12.0000000000, 'N': 14.0030740044, 
    'O': 15.9949146196, 'P': 30.9737619984, 'S': 31.9720711744,
    'F': 18.9984031627, 'Cl': 34.968852682, 'Br': 78.9183376, 
    'I': 126.904477
}

# 加合离子偏差值 (Adduct Delta Mass)
# 考虑了电子质量 (0.000548 Da)
ADDUCTS_DELTA = {
    # --- 正离子 ---
    "[M+H]+":       1.007276,     # Proton mass
    "[M+Na]+":      22.989221,    # Na - e
    "[M+NH4]+":     18.033826,    # NH4 - e
    "[M+K]+":       38.963158,    # K - e
    # --- 负离子 ---
    "[M-H]-":       -1.007276,    # Loss of Proton
    "[M+Cl]-":      34.969402,    # Cl + e
    "[M+HCOO]-":    44.998204,    # Formate + e
    "[M+CH3COO]-":  59.013854,    # Acetate + e
}

def parse_and_calculate_mass(formula_str):
    """
    强力解析函数：能处理空格、中文、常见错误
    """
    try:
        # 1. 清洗数据
        if pd.isna(formula_str): return None, "空值"
        clean_str = str(formula_str).strip()
        
        # 处理 "和" (取第一个)
        if "和" in clean_str:
            clean_str = clean_str.split("和")[0].strip()
            status = "混合物(取首个)"
        else:
            status = "成功"
            
        # 移除不可见字符 (如 \t)
        clean_str = re.sub(r'\s+', '', clean_str)

        # 2. 解析元素 (正则表达式)
        # 匹配: [大写字母][小写字母可选][数字可选]
        pattern = r"([A-Z][a-z]?)(\d*)"
        tokens = re.findall(pattern, clean_str)
        
        # 验证解析后的重组是否等于原字符串 (防止非法字符被忽略)
        reconstructed = "".join([t[0] + t[1] for t in tokens])
        if len(reconstructed) != len(clean_str):
            # 尝试处理括号情况 (简单版：不支持嵌套)
            # 稍微复杂一点，如果遇到括号，建议使用专门库。这里做简单fallback
            return None, "含有不支持字符(如括号/点)"

        # 3. 计算质量
        exact_mass = 0.0
        for element, count_str in tokens:
            count = int(count_str) if count_str else 1
            if element not in ATOM_MASS:
                return None, f"未知元素: {element}"
            exact_mass += ATOM_MASS[element] * count
            
        return exact_mass, status
        
    except Exception as e:
        return None, f"解析错误: {str(e)}"

# ==========================================
# Streamlit 界面
# ==========================================
st.set_page_config(page_title="HRMS 批量计算器", layout="wide")
st.title("🧪 强力型 HRMS 质量计算器")

uploaded_file = st.file_uploader("上传 CSV 或 Excel (支持无表头)", type=['csv', 'xlsx'])

if uploaded_file:
    # 尝试智能读取 (判断是否有表头)
    if uploaded_file.name.endswith('.csv'):
        # 预览前几行来决定是否有header
        df = pd.read_csv(uploaded_file, header=None)
    else:
        df = pd.read_excel(uploaded_file, header=None)
    
    st.write("📂 数据预览 (默认假设第一列是名称，第二列是分子式):")
    st.dataframe(df.head())
    
    col_idx = st.selectbox("请选择【分子式】所在的列号:", df.columns.tolist(), index=1 if len(df.columns)>1 else 0)
    
    if st.button("🚀 开始修复并计算"):
        results = []
        
        # 进度条
        progress_bar = st.progress(0)
        
        for i, row in df.iterrows():
            formula_raw = row[col_idx]
            mass, status = parse_and_calculate_mass(formula_raw)
            
            row_data = {
                "原始分子式": formula_raw,
                "Monoisotopic Mass": mass,
                "状态": status
            }
            
            # 计算加合离子
            if mass:
                for adduct, delta in ADDUCTS_DELTA.items():
                    row_data[adduct] = mass + delta
            
            results.append(row_data)
            progress_bar.progress((i + 1) / len(df))
            
        # 合并结果
        res_df = pd.DataFrame(results)
        final_df = pd.concat([df, res_df], axis=1)
        
        st.success("计算完成！")
        st.dataframe(final_df.head())
        
        # 下载
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            final_df.to_excel(writer, index=False)
            
        st.download_button("📥 下载最终结果", output.getvalue(), "HRMS_Results.xlsx")
