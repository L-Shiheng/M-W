import streamlit as st
import pandas as pd
from molmass import Formula
from io import BytesIO

# 设置页面配置
st.set_page_config(
    page_title="化合物质量批量计算器",
    page_icon="⚗️",
    layout="centered"
)

st.title("⚗️ 化合物质量计算平台")

# 创建两个选项卡
tab1, tab2 = st.tabs(["📂 Excel 批量处理", "🔍 单个查询"])

# ==========================================
# 选项卡 1: Excel 批量上传处理
# ==========================================
with tab1:
    st.header("Excel 批量计算")
    st.markdown("上传包含分子式的 Excel 文件，自动计算精确质量和平均分子量。")

    # 1. 文件上传器
    uploaded_file = st.file_uploader("上传 Excel 文件 (.xlsx)", type=['xlsx'])

    if uploaded_file is not None:
        try:
            # 读取 Excel
            df = pd.read_excel(uploaded_file)
            
            # 显示前几行预览
            st.write("📄 数据预览 (前5行):")
            st.dataframe(df.head())

            # 2. 选择包含分子式的列
            columns = df.columns.tolist()
            target_col = st.selectbox("请选择包含【分子式】的那一列:", columns)

            # 3. 开始计算按钮
            if st.button("🚀 开始计算", type="primary"):
                
                # 定义计算函数
                def calculate_mass(formula_str):
                    try:
                        # 清理数据 (转字符串，去空格)
                        f_str = str(formula_str).strip()
                        if not f_str or f_str.lower() == 'nan':
                            return None, None, "空值"
                        
                        f = Formula(f_str)
                        # 返回: 精确质量, 平均分子量, 状态
                        return f.isotope.mass, f.mass, "成功"
                    except Exception:
                        return None, None, "格式错误"

                # 显示进度条
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                # 处理数据 (为了显示进度，这里不用简单的 apply，而是手动循环，或者直接处理)
                # 使用 apply 实际上很快，对于几千行瞬间就能完成
                with st.spinner('正在疯狂计算中...'):
                    # 应用计算逻辑
                    result_series = df[target_col].apply(calculate_mass)
                    
                    # 将结果拆分到新列
                    df['精确质量 (Exact Mass)'] = result_series.apply(lambda x: x[0])
                    df['平均分子量 (Mol. Weight)'] = result_series.apply(lambda x: x[1])
                    df['状态'] = result_series.apply(lambda x: x[2])

                progress_bar.progress(100)
                st.success("✅ 计算完成！")

                # 4. 展示结果预览
                st.write("📊 结果预览:")
                st.dataframe(df.head())

                # 5. 生成下载链接
                # 将 DataFrame 写入内存中的 Excel 文件
                output = BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df.to_excel(writer, index=False)
                processed_data = output.getvalue()

                st.download_button(
                    label="📥 下载处理后的 Excel",
                    data=processed_data,
                    file_name="calculated_mass_results.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

        except Exception as e:
            st.error(f"无法读取文件，请确保上传的是有效的 Excel 文件。\n错误信息: {e}")

# ==========================================
# 选项卡 2: 单个查询 (保留原有功能)
# ==========================================
with tab2:
    st.header("单个分子式查询")
    formula_input = st.text_input(
        "输入分子式 (例如: C6H12O6)", 
        value="",
        placeholder="在此输入..."
    )

    if formula_input:
        try:
            f = Formula(formula_input)
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("精确质量 (Exact Mass)", f"{f.isotope.mass:.5f}")
            with col2:
                st.metric("平均分子量 (Mol. Weight)", f"{f.mass:.5f}")
            
            st.caption(f"解析结果: {f.formula}")
            
            # 简单的元素表
            comp_data = [{"元素": k.symbol, "数量": v} for k, v in f.composition().items()]
            st.table(pd.DataFrame(comp_data))

        except Exception as e:
            st.error(f"解析错误: {e}")
