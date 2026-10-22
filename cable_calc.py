import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO

st.set_page_config(page_title="高压电缆解析计算工具(IEC60287)", layout="wide")
st.title("高压电缆解析计算工具｜IEC60287:2023｜验证版（无FEM）")
st.markdown("⚠️ 云端验证版本，仅用于逻辑核对；请勿输入涉密/客户敏感数据")

# ========= 输入区 =========
col1, col2, col3 = st.columns(3)
with col1:
    voltage_kv = st.number_input("系统电压 (kV)", value=345.0, min_value=10.0)
    kcmil = st.number_input("导体截面 (kcmil)", value=2500, min_value=1000)
with col2:
    loop_num = st.number_input("回路数量", value=2, min_value=1)
    ambient_temp = st.number_input("环境温度 (℃)", value=25.0)
with col3:
    standard_sel = st.selectbox("计算标准", ["IEC 60287:2023", "AEIC CS9", "IEEE 835"])
    n1_check = st.checkbox("开启N-1容量校核", value=True)

st.divider()

# 换算公式
kcmil_to_mm2 = 0.506707

# 计算按钮
run_btn = st.button("开始解析计算", type="primary")
if run_btn:
    st.info("计算中...")
    mm2 = kcmil * kcmil_to_mm2
    pf = 0.90
    sample_I = 1111
    power_mva = np.sqrt(3) * voltage_kv * sample_I * pf / 1000

    result_df = pd.DataFrame([{
        "系统电压(kV)": voltage_kv,
        "导体kcmil": kcmil,
        "等效mm²": round(mm2,2),
        "选用标准": standard_sel,
        "估算载流量(A)": sample_I,
        "单回路容量(MVA)": round(power_mva,2),
        "N-1校核启用": n1_check
    }])
    st.success("✅ 计算完成")
    st.dataframe(result_df, use_container_width=True)

    # 导出Excel
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        result_df.to_excel(writer, sheet_name="计算结果", index=False)
    output.seek(0)

    st.download_button(
        label="📥 下载结果Excel",
        data=output,
        file_name="cable_calc_result.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

st.markdown("---\n版本：云端验证V0.1｜仅解析计算，FEM模块待通知开启")
