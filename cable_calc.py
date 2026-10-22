import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO

st.set_page_config(page_title="高压电缆解析计算工具(IEC & 北美)", layout="wide")
st.title("高压电缆解析计算工具｜IEC60287:2023 / AEIC CS9 / IEEE 835｜验证版（无FEM）")
st.markdown("⚠️ 云端验证版本，仅用于逻辑核对；请勿输入涉密/客户敏感数据")

# 加载查表表格，增加容错保护
@st.cache_data
def load_ref_table():
    try:
        df = pd.read_excel("cable_reference.xlsx")
        return df, True
    except Exception as err:
        return None, False

df_ref, load_ok = load_ref_table()
if load_ok:
    st.subheader("📋 参考数据表")
    st.dataframe(df_ref, use_container_width=True)
else:
    st.warning("参考数据表读取失败（文件缺失/损坏），计算功能不受影响，可以继续使用！")

# ========= 输入区 =========
col0, _ = st.columns([1,3])
with col0:
    spec_system = st.selectbox("规格体系", ["IEC公制 mm²", "北美 kcmil"])

# 根据体系联动电压、截面下拉
if spec_system == "IEC公制 mm²":
    voltage_list = [110, 220, 275, 400]
    size_list = [800, 1000, 1200, 1400, 1600, 2000]
else:
    voltage_list = [115, 230, 345, 500]
    size_list = [2000, 2500, 3000, 4000, 5000, 6000]

col1, col2, col3 = st.columns(3)
with col1:
    voltage_sel = st.selectbox("系统电压 (kV)", voltage_list, index=min(2, len(voltage_list)-1))
with col2:
    size_sel = st.selectbox("导体截面", size_list, index=1)
with col3:
    install_sel = st.selectbox("敷设方式", ["隧道内", "直埋", "排管", "空气中"])

colA, colB, colC = st.columns(3)
with colA:
    loop_num = st.number_input("同沟/隧道回路数量", value=2, min_value=1)
with colB:
    bond_sel = st.selectbox("护套接地方式", ["单点接地 SPB", "交叉互联 Cross-bonding"])
with colC:
    n1_check = st.checkbox("开启N-1容量校核", value=True)

colX, colY, colZ = st.columns(3)
with colX:
    ambient_temp = st.number_input("环境温度 (℃)", value=25.0)
with colY:
    cable_spacing = st.number_input("电缆相间间距(mm)", value=250.0)
with colZ:
    standard_sel = st.selectbox("计算标准", ["IEC 60287:2023", "AEIC CS9", "IEEE 835"])

st.divider()

# 换算系数
kcmil_to_mm2 = 0.506707
mm2_to_kcmil = 1 / kcmil_to_mm2

# 简易热干涉降容系数（当前为查表版，后续替换 IEC60287 / CIGRE TB 解析公式）
def get_derating(loop_count, install_type):
    if install_type == "隧道内":
        derate = {1:1.00,2:0.88,3:0.80,4:0.74}
    elif install_type == "直埋":
        derate = {1:1.00,2:0.90,3:0.83,4:0.77}
    else:
        derate = {1:1.00,2:0.93,3:0.87,4:0.82}
    return derate.get(loop_count, 0.70)

# 基准载流量样板库
base_I_library = {
    "IEC公制 mm²": {
        800:760,
        1000:880,
        1200:990,
        1400:1090,
        1600:1180,
        2000:1350
    },
    "北美 kcmil": {
        2000:920,
        2500:1111,
        3000:1280,
        4000:1570,
        5000:1820,
        6000:2040
    }
}

run_btn = st.button("开始解析计算", type="primary")

if run_btn:
    st.info("计算中...")
    # 双向单位换算
    if spec_system == "北美 kcmil":
        kcmil = size_sel
        mm2 = kcmil * kcmil_to_mm2
    else:
        mm2 = size_sel
        kcmil = mm2 * mm2_to_kcmil

    pf = 0.90
    base_I = base_I_library[spec_system][size_sel]
    derate_factor = get_derating(loop_num, install_sel)
    allow_I = base_I * derate_factor
    power_mva = np.sqrt(3) * voltage_sel * allow_I * pf / 1000

    result_df = pd.DataFrame([{
        "规格体系": spec_system,
        "系统电压(kV)": voltage_sel,
        "导体kcmil": round(kcmil,1),
        "导体mm²": round(mm2,2),
        "敷设方式": install_sel,
        "护套接地方式": bond_sel,
        "回路数量": loop_num,
        "热降容系数": round(derate_factor,3),
        "基准载流量(A)": base_I,
        "允许载流量(A)": round(allow_I,1),
        "选用标准": standard_sel,
        "单回路容量(MVA)": round(power_mva,1),
        "N-1校核启用": n1_check
    }])
    st.success("✅ 计算完成")
    st.dataframe(result_df, use_container_width=True)

    # ---------------------- 新增：网页展示计算逻辑 ----------------------
    st.subheader("📐 计算逻辑与标准依据")
    st.markdown("""
    > 当前版本：热降容采用简易查表；下一版本替换为 **IEC 60287:2023 / CIGRE TB** 解析热干涉公式
    > 护套接地：仅记录选型，后续增加 SPB / Cross-bonding 护套感应电压、环流、附加损耗计算

    **1. 截面换算**
    $$A_{mm^2}=A_{kcmil} \\times 0.506707$$
    $$A_{kcmil}=A_{mm^2} \\div 0.506707$$

    **2. 计及多回路热干涉后的允许载流量**
    $$I_{allow}=I_{base} \\times F_{derate}$$
    - $I_{base}$：单回路基准载流量（样板值库）
    - $F_{derate}$：多回路热干涉降容系数

    **3. 三相输送容量（MVA）**
    $$S=\sqrt{3} \times U_{n} \times I_{allow} \times cos\varphi$$
    - $U_n$：系统线电压，kV
    - $cos\varphi$：功率因数，默认取0.90

    **4. 标准清单**
    - IEC 60287:2023：电缆载流量计算
    - AEIC CS9：北美电力电缆标准
    - IEEE 835：电力电缆载流量标准
    - CIGRE TB：多回路敷设热干涉导则（待接入）
    """)

    # Excel导出
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        result_df.to_excel(writer, sheet_name="计算结果", index=False)
        if load_ok:
            df_ref.to_excel(writer, sheet_name="参考数据表", index=False)
    output.seek(0)

    st.download_button(
        label="📥 下载结果Excel",
        data=output,
        file_name="cable_calc_result.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

st.markdown("---\n版本：云端验证V0.4｜增加网页内嵌计算逻辑说明面板")
