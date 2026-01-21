import streamlit as st
import pandas as pd
from molmass import Formula
from io import BytesIO

# ==========================================
# 0. 基础配置与科学常数
# ==========================================
st.set_page_config(
    page_title="HRMS 质谱离子供应站",
    page_icon="🔬",
    layout="wide" # 使用宽屏模式以便显示更多列
)

# 质谱常用加合离子质量偏差 (Delta Mass)
#以此为基础：Neutral Mass (M) -> Adduct Mass
ADDUCTS_LIB = {
    # --- 正离子模式 (Positive) ---
    "[M+H]+":       1.007276,
    "[M+Na]+":      22.989769,
    "[M+NH4]+":     18.034374,
    "[M+K]+":       38.963706,
    "[M+2H]2+":     1.007276 / 2, # (M + 2*1.007276) / 2 -> 实际上是 (M/2) + 1.007276 - 简单算法在下面单独处理
    "[2M+H]+":      "dimer_h",    # 特殊处理：2*M + 1.007276
    "[2M+Na]+":     "dimer_na",   # 特殊处理：2*M + 22.989769
    
    # --- 负离子模式 (Negative) ---
    "[M-H]-":       -1.007276,
    "[M+Cl]-":      34.968853,
    "[M+HCOO]-":    44.997655,    # 甲酸根加合 Formate
    "[M+CH3COO]-":  59.013305,    # 乙酸根加合 Acetate
}

# 默认选中的常用离子
DEFAULT_SELECTION = ["[M+H]+", "[M+Na]+", "[M-H]-"]

st.title("🔬 高分辨质谱 (HRMS) 质量计算器")
st.markdown("""
专为高分辨质谱设计。基于 **Monoisotopic Mass (单同位素质量)** 计算常见的加合离子 (Adducts)。
""")

tab1, tab2 = st.tabs(["📂 Excel 批量生成 (质谱表)", "🔍 单个化合物速查"])

# ==========================================
# 1. 核心计算函数
# ==========================================
def calculate_adducts(formula_str, selected_adducts):
    """
    输入：分子式，需要计算的加合离子列表
    输出：包含所有质量数的字典
    """
    try:
        f_str = str(formula_str).strip()
        if not f_str or f_str.lower() == 'nan':
            return {"状态": "空值"}
            
        f = Formula(f_str)
        mono_mass = f.isotope.mass # 核心：取单同位素质量
        
        result = {
            "Formula": f.formula,
            "Neutral Mass (M)": mono_mass,
            "状态": "成功"
        }
        
        # 遍历计算选中的加合离子
        for adduct_name in selected_adducts:
            delta = ADDUCTS_LIB.get(adduct_name)
            
            # 处理特殊类型的计算
            if adduct_name == "[2M+H]+":
                mass = (mono_mass * 2) + 1.007276
            elif adduct_name == "[2M+Na]+":
                mass = (mono_mass * 2) + 22.989769
            elif adduct_name == "[M+2H]2+":
                 # 双电荷：(M + 2*H) / 2
                mass = (mono_mass + 2 * 1.007276) / 2
            else:
                # 普通单电荷加减
                mass = mono_mass + delta
                
            result[adduct_name] = mass
            
        return result

    except Exception as e:
        return {"状态": "格式错误"}

# ==========================================
# 选项卡 1: Excel 批量处理
# ==========================================
with tab1:
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.info("👇 第一步：上传与设置")
        uploaded_file = st.file_uploader("上传 Excel", type=['xlsx'])
        
        # 多选框：让用户选择要计算哪些离子
        st.write("🔧 **选择要生成的加合离子列:**")
        selected_adducts = st.multiselect(
            "点击框内添加更多模式",
            options=list(ADDUCTS_LIB.keys()),
            default=DEFAULT_SELECTION
        )
    
    with col2:
        if uploaded_file:
            df = pd.read_excel(uploaded_file)
            st.write(f"📄 已加载 {len(df)} 行数据。请选择分子式所在的列：")
            
            target_col = st.selectbox("分子式列名:", df.columns.tolist())
            
            if st.button("🚀 开始计算质谱数据", type="primary"):
                with st.spinner('正在进行高精度计算...'):
                    # 运行计算
                    results = []
                    # 逐行处理
                    for idx, row in df.iterrows():
                        res = calculate_adducts(row[target_col], selected_adducts)
                        results.append(res)
                    
                    # 将结果转换为 DataFrame
                    results_df = pd.DataFrame(results)
                    
                    # 合并：原始数据 + 计算结果
                    final_df = pd.concat([df, results_df], axis=1)
                    
                    st.success("计算完成！")
                    
                    # 显示结果
                    st.dataframe(final_df.head())
                    
                    # 下载
                    output = BytesIO()
                    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                        final_df.to_excel(writer, index=False)
                        
                    st.download_button(
                        label="📥 下载包含质谱数据的 Excel",
                        data=output.getvalue(),
                        file_name="HRMS_Calculated_Results.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )

# ==========================================
# 选项卡 2: 单个查询 (速查工具)
# ==========================================
with tab2:
    st.markdown("快速查看某个化合物在正/负离子模式下的所有理论m/z值。")
    
    inp = st.text_input("输入分子式 (如 C18H36O2)", "C18H36O2")
    
    if inp:
        # 计算所有支持的离子
        all_adducts = list(ADDUCTS_LIB.keys())
        res = calculate_adducts(inp, all_adducts)
        
        if res.get("状态") == "成功":
            st.subheader(f"🔍 {res['Formula']} 理论 m/z 值")
            st.info(f"中性单同位素质量 (Neutral Monoisotopic Mass): **{res['Neutral Mass (M)']:.5f}**")
            
            c1, c2 = st.columns(2)
            
            with c1:
                st.write("🟢 **正离子模式 (Positive Mode)**")
                pos_data = {k: v for k, v in res.items() if "+" in k}
                # 格式化显示
                pos_df = pd.DataFrame(list(pos_data.items()), columns=["Ion Type", "m/z"])
                pos_df['m/z'] = pos_df['m/z'].apply(lambda x: f"{x:.5f}") # 保留5位小数
                st.table(pos_df)
                
            with c2:
                st.write("🔴 **负离子模式 (Negative Mode)**")
                neg_data = {k: v for k, v in res.items() if "-" in k}
                neg_df = pd.DataFrame(list(neg_data.items()), columns=["Ion Type", "m/z"])
                neg_df['m/z'] = neg_df['m/z'].apply(lambda x: f"{x:.5f}")
                st.table(neg_df)
        else:
            st.error("分子式解析失败，请检查拼写。")
