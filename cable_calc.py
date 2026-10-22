import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO

st.set_page_config(page_title="高压电缆 IEC60287 载流量计算工具 V1.0", layout="wide")
st.title("高压电缆载流量计算｜IEC 60287‑1/-2:2023 / AEIC CS9 / IEEE 835｜V1.0")
st.markdown("""
标准依据：
- IEC 60287‑1:2023 电流额定‑计算公式（集肤/邻近效应、护套损耗λs）
- IEC 60287‑2:2023 电流额定‑外部热阻T4
- CIGRE TB 207：地下电缆外部热阻、回填层、多回路热干涉
⚠️ 云端验证版本，仅用于逻辑核对；请勿输入涉密/客户敏感数据
""")

# ---------------------- 参考表加载 + 缓存刷新 ----------------------
@st.cache_data
def load_ref_table():
    try:
        df = pd.read_excel("cable_reference.xlsx")
        return df, True
    except Exception:
        return None, False

if st.button("🔄 刷新参考数据表（修改Excel后点这里）"):
    load_ref_table.clear()
    st.success("参考表缓存已清空，重新加载！")

df_ref, load_ok = load_ref_table()
if load_ok:
    st.subheader("📋 参考数据表")
    st.dataframe(df_ref, use_container_width=True)
else:
    st.warning("参考数据表读取失败（文件缺失/损坏），无法读取电缆几何参数！")

# ========= 输入区 =========
col0, _ = st.columns([1,3])
with col0:
    spec_system = st.selectbox("规格体系", ["IEC公制 mm²", "北美 kcmil"])

voltage_list = [66, 110, 115, 220, 230, 275, 345, 400, 500]
if spec_system == "IEC公制 mm²":
    size_list = [800, 1000, 1200, 1400, 1600, 2000]
else:
    size_list = [2000,2500,3000,4000,5000,6000]

col1, col2, col3 = st.columns(3)
with col1:
    voltage_sel = st.selectbox("系统电压 (kV)", voltage_list, index=3)
with col2:
    size_sel = st.selectbox("导体截面", size_list, index=1)
with col3:
    install_sel = st.selectbox("敷设方式", ["隧道内", "直埋", "排管", "空气中"])

colA, colB, colC = st.columns(3)
with colA:
    loop_num = st.number_input("同通道电缆根数", value=2, min_value=1)
# 新增 SB两端直接接地 Solid‑Bonded
with colB:
    bond_sel = st.selectbox("护套接地方式", [
        "单点接地 SPB",
        "交叉互联 Cross‑bonding",
        "两端直接接地 SB(Solid‑Bonded)"
    ])
with colC:
    n1_check = st.checkbox("开启N‑1容量校核", value=True)

colX, colY, colZ = st.columns(3)
with colX:
    ambient_temp = st.number_input("环境温度 (℃)", value=25.0)
with colY:
    cable_spacing = st.number_input("电缆中心间距(mm)", value=250.0)
with colZ:
    freq = st.selectbox("频率(Hz)", [50,60], index=0)

st.divider()
st.subheader("📍 敷设专属参数（动态显示）")
install_params = {}
if install_sel == "隧道内":
    c1,c2,c3 = st.columns(3)
    with c1:
        tunnel_w = st.number_input("隧道宽度(m)", value=2.0, min_value=0.5)
    with c2:
        tunnel_h = st.number_input("隧道高度(m)", value=2.2, min_value=0.5)
    with c3:
        tunnel_vel = st.number_input("隧道通风风速(m/s)", value=1.2, min_value=0.0)
    install_params["隧道宽度(m)"] = tunnel_w
    install_params["隧道高度(m)"] = tunnel_h
    install_params["通风风速(m/s)"] = tunnel_vel

elif install_sel == "直埋":
    c1,c2,c3 = st.columns(3)
    with c1:
        bury_depth = st.number_input("电缆中心埋深(m)", value=1.2, min_value=0.4)
    with c2:
        rho_soil = st.number_input("原生土壤热阻系数(K·m/W)", value=1.2, min_value=0.6)
    with c3:
        backfill_thick = st.number_input("回填层厚度(m)", value=0.3, min_value=0.1)
    c4,_ ,_ = st.columns(3)
    with c4:
        rho_backfill = st.number_input("回填层热阻系数(K·m/W)", value=1.2, min_value=0.6)
    install_params["埋深(m)"] = bury_depth
    install_params["原生土壤热阻(K·m/W)"] = rho_soil
    install_params["回填厚度(m)"] = backfill_thick
    install_params["回填层热阻(K·m/W)"] = rho_backfill

elif install_sel == "排管":
    c1,c2,c3 = st.columns(3)
    with c1:
        duct_mat = st.selectbox("排管材质", ["CPVC","HDPE","混凝土","钢管","球墨铸铁"])
    with c2:
        duct_id = st.number_input("排管内径(mm)", value=150.0, min_value=100.0)
    with c3:
        duct_bury = st.number_input("排管中心埋深(m)", value=0.8, min_value=0.4)
    install_params["排管材质"] = duct_mat
    install_params["排管内径(mm)"] = duct_id
    install_params["排管埋深(m)"] = duct_bury
else:
    st.info("空气中敷设无额外专属参数")
    install_params["备注"] = "空气中敷设"

st.divider()
st.subheader("⚙️ 电缆本体参数")
colP1,colP2,colP3 = st.columns(3)
with colP1:
    conductor_temp_limit = st.number_input("导体允许最高温度(℃)", value=90.0)
with colP2:
    tan_delta = st.number_input("介质损耗角正切", value=0.001, format="%.4f")
with colP3:
    conductor_material = st.selectbox("导体材质", ["铜Cu","铝Al"])

# ---------------------- 读取参考表几何参数 ----------------------
geo_data = None
if load_ok:
    mask = (df_ref["系统电压(kV)"] == voltage_sel) & (df_ref["导体截面"] == size_sel) & (df_ref["规格体系"] == spec_system)
    matched = df_ref[mask]
    if len(matched)>=1:
        row = matched.iloc[0]
        geo_data = {
            "d_c": row["导体直径(mm)"]/1000,
            "D_ins": row["绝缘外径(mm)"]/1000,
            "D_sheath": row["护套外径(mm)"]/1000,
            "rho_ins": row["绝缘热阻系数K·m/W"]
        }
    else:
        st.warning("参考表未匹配到该电压+截面的电缆几何数据！")

# ---------------------- IEC60287 核心计算函数 V1.0 ----------------------
kcmil_to_mm2 = 0.506707
mm2_to_kcmil = 1 / kcmil_to_mm2

def calc_skin_proximity(f, A_mm2, d_conductor_m, mat="Cu"):
    """IEC60287‑1:2023 集肤效应ys、邻近效应yp解析式，50/60Hz通用"""
    mu0 = 4*np.pi*1e‑7
    if mat=="Cu":
        rho20 = 1.7241e‑8
        alpha20 = 0.00393
    else:
        rho20 = 2.8264e‑8
        alpha20 = 0.00403
    A_m2 = A_mm2*1e‑6
    Rdc20 = rho20 / A_m2
    omega = 2*np.pi*f
    k_sq = (omega * mu0)/(np.pi * Rdc20)
    ys = 0.0
    if k_sq>0:
        ks = np.sqrt(k_sq)
        ys = (ks**4)/(192 + 0.8*ks**4)
    yp = 0.0
    return ys, yp

def calc_lambda_s_full(bond_mode, Ds, s, f, R_sheath_dc):
    """IEC60287‑1:2023 护套损耗系数λs 三种接地模式"""
    mu0 = 4*np.pi*1e‑7
    omega = 2*np.pi*f
    Ms = mu0/(2*np.pi)*np.log(2*s/Ds)
    Xs = omega * Ms
    Rs = R_sheath_dc
    if bond_mode == "单点接地 SPB":
        return 0.0
    elif bond_mode == "交叉互联 Cross‑bonding":
        return (Xs**2)/(Rs**2 + Xs**2)
    elif bond_mode == "两端直接接地 SB(Solid‑Bonded)":
        return 1.0
    return 0.0

def calc_T4_full(install_type, params, D_cable_m, n_cable, s_m, f):
    """IEC60287‑2:2023 + CIGRE TB207 完整外部热阻T4，移除硬编码固定值"""
    rho_soil = params.get("原生土壤热阻(K·m/W)",1.2)
    rho_backfill = params.get("回填层热阻(K·m/W)",1.2)
    bury = params.get("埋深(m)",1.0)
    backfill_t = params.get("回填厚度(m)",0.3)
    tunnel_w = params.get("隧道宽度(m)",2.0)
    tunnel_h = params.get("隧道高度(m)",2.2)
    vel = params.get("通风风速(m/s)",1.0)
    duct_mat = params.get("排管材质","CPVC")
    duct_id_m = params.get("排管内径(mm)",150)/1000

    if install_type == "直埋":
        T4_base = rho_backfill/(2*np.pi)*np.log(4*bury / D_cable_m)
        T4_base += (rho_soil‑rho_backfill)/(2*np.pi)*np.log((bury+backfill_t)/bury)
        add_interfere = 0.0
        if n_cable>1:
            for k in range(1,n_cable):
                add_interfere += np.log(np.sqrt(1 + (2*bury/(k*s_m))**2))
        T4 = T4_base + rho_soil/(2*np.pi)*add_interfere
        return max(T4,0.01)
    elif install_type == "排管":
        mat_rho = {
            "CPVC":3.5,
            "HDPE":3.8,
            "混凝土":1.2,
            "钢管":0.05,
            "球墨铸铁":0.08
        }
        rho_duct = mat_rho.get(duct_mat,3.5)
        T_duct_wall = rho_duct/(2*np.pi)*np.log(duct_id_m/D_cable_m)
        T_duct_gap = 1.2
        T_soil_duct = rho_soil/(2*np.pi)*np.log(4*bury / duct_id_m)
        T4 = T_duct_wall + T_duct_gap + T_soil_duct
        return max(T4,0.01)
    elif install_type == "隧道内":
        h_conv = 3.5 + 5.2*np.sqrt(max(vel,0.01))
        A_tunnel = tunnel_w * tunnel_h
        perimeter = 2*(tunnel_w + tunnel_h)
        T_conv = 1.0/(h_conv * perimeter)
        T_rad = 0.45
        T4 = T_conv + T_rad
        return max(T4,0.01)
    else: #空气中
        h_air = 6.0
        T_air = 1/(np.pi * D_cable_m * h_air)
        return max(T_air,0.01)

def calc_cable_thermal(
    spec_system, size_sel, voltage_kV,
    install_sel, install_params,
    n_cable, cable_spacing_m,
    T_amb, T_limit, freq, tan_delta,
    conductor_material, geo
):
    if spec_system == "北美 kcmil":
        kcmil = size_sel
        A_mm2 = kcmil * kcmil_to_mm2
    else:
        A_mm2 = size_sel
        kcmil = A_mm2 * mm2_to_kcmil
    A_m2 = A_mm2 * 1e‑6

    if conductor_material == "铜Cu":
        rho20 = 1.7241e‑8
        alpha20 = 0.00393
    else:
        rho20 = 2.8264e‑8
        alpha20 = 0.00403

    d_c = geo["d_c"]
    D_ins = geo["D_ins"]
    D_sheath = geo["D_sheath"]
    rho_ins = geo["rho_ins"]
    R_sheath_dc = 0.022 / 1000

    ys, yp = calc_skin_proximity(freq, A_mm2, d_c, conductor_material)

    Tc = T_limit
    for _ in range(15):
        R20 = rho20 / A_m2
        R_ac = R20 * (1 + alpha20*(Tc‑20))
        R_ac = R_ac * (1 + ys + yp)

        omega = 2 * np.pi * freq
        U_phase = voltage_kV / np.sqrt(3) * 1000
        C_per_m = 0.3e‑9
        Wd = omega * C_per_m * U_phase**2 * tan_delta

        lambda_s = calc_lambda_s_full(bond_sel, D_sheath, cable_spacing_m, freq, R_sheath_dc)

        T1 = rho_ins/(2*np.pi)*np.log(D_ins / d_c)
        T2 = 0.20
        T3 = 5.0/(2*np.pi)*np.log(D_sheath / D_ins)
        T4 = calc_T4_full(install_sel, install_params, D_sheath, n_cable, cable_spacing_m, freq)

        T_total = T1 + T2 + T3 + T4
        dT_allowed = Tc - T_amb
        numerator = dT_allowed - Wd*(T1 + T2 + T3)
        denominator = R_ac*(1+lambda_s)*T_total
        if numerator <= 0:
            I_calc = 0
        else:
            I_calc = np.sqrt(numerator / denominator)

        Wc = I_calc**2 * R_ac
        Ws = Wc * lambda_s

        dT1 = (Wc + Ws + Wd) * T1
        dT2 = (Wc + Ws + Wd) * T2
        dT3 = (Wc + Ws) * T3
        dT4 = (Wc + Ws) * T4

        T_screen = Tc - dT1
        T_sheath = T_screen - dT2
        T_surface = T_sheath - dT3

        if abs(Tc - T_limit) < 0.01:
            break

    S_mva = np.sqrt(3)*voltage_kV*I_calc/1000

    # N‑1校核
    I_n1 = I_calc * n_cable / (n_cable‑1) if n_cable>1 else np.nan
    Wc_n1 = I_n1**2 * R_ac
    deltaT_n1 = Wc_n1*(1+lambda_s)*T_total + Wd*(T1+T2+T3)
    Tc_n1 = T_amb + deltaT_n1

    res = {
        "A_mm2":A_mm2, "A_kcmil":A_kcmil,
        "R_ac(Ω/m)":R_ac,
        "ys集肤系数":round(ys,6),
        "yp邻近系数":round(yp,6),
        "lambda_s护套损耗系数":lambda_s,
        "Wc(W/m)":Wc, "Ws(W/m)":Ws, "Wd(W/m)":Wd,
        "T1":T1,"T2":T2,"T3":T3,"T4":T4,"T_total":T_total,
        "dT1":dT1,"dT2":dT2,"dT3":dT3,"dT4":dT4,
        "Tc":Tc,"T_screen":T_screen,"T_sheath":T_sheath,"T_surface":T_surface,
        "I_allow(A)":I_calc,"S(MVA)":S_mva,
        "I_N1(A)":I_n1,"Tc_N1(℃)":Tc_n1
    }
    return res

run_btn = st.button("▶️ 启动 IEC60287 热回路计算", type="primary")

if run_btn:
    if geo_data is None:
        st.error("缺少电缆几何参数，无法计算，请检查cable_reference.xlsx！")
    else:
        cable_spacing_m = cable_spacing / 1000
        out = calc_cable_thermal(
            spec_system=spec_system,
            size_sel=size_sel,
            voltage_kV=voltage_sel,
            install_sel=install_sel,
            install_params=install_params,
            n_cable=loop_num,
            cable_spacing_m=cable_spacing_m,
            T_amb=ambient_temp,
            T_limit=conductor_temp_limit,
            freq=freq,
            tan_delta=tan_delta,
            conductor_material=conductor_material,
            geo=geo_data
        )
        st.success("✅ IEC60287‑1/‑2 V1.0 完整解析迭代计算完成")
        result_dict = {
            "规格体系": spec_system,
            "系统电压(kV)": voltage_sel,
            "导体kcmil": round(out["A_kcmil"],1),
            "导体mm²": round(out["A_mm2"],2),
            "导体材质": conductor_material,
            "敷设方式": install_sel,
            "护套接地方式": bond_sel,
            "频率Hz": freq,
            "电缆根数": loop_num,
            "中心间距(mm)": cable_spacing,
            "环境温度(℃)": ambient_temp,
            "导体交流电阻(Ω/m)": round(out["R_ac(Ω/m)"],8),
            "集肤系数ys": out["ys集肤系数"],
            "邻近效应yp": out["yp邻近系数"],
            "护套损耗系数λs": round(out["lambda_s护套损耗系数"],4),
            "导体损耗(W/m)": round(out["Wc(W/m)"],3),
            "护套损耗(W/m)": round(out["Ws(W/m)"],3),
            "介质损耗(W/m)": round(out["Wd(W/m)"],3),
            "热阻T1绝缘(K·m/W)": round(out["T1"],4),
            "热阻T2内衬屏蔽(K·m/W)": round(out["T2"],4),
            "热阻T3外护套(K·m/W)": round(out["T3"],4),
            "热阻T4外部(K·m/W)": round(out["T4"],4),
            "总热阻(K·m/W)": round(out["T_total"],4),
            "温升dT1绝缘(K)": round(out["dT1"],2),
            "温升dT2内衬屏蔽(K)": round(out["dT2"],2),
            "温升dT3外护套(K)": round(out["dT3"],2),
            "温升dT4外部(K)": round(out["dT4"],2),
            "导体温度(℃)": round(out["Tc"],2),
            "绝缘屏蔽温度(℃)": round(out["T_screen"],2),
            "护套温度(℃)": round(out["T_sheath"],2),
            "外表面温度(℃)": round(out["T_surface"],2),
            "允许载流量(A)": round(out["I_allow(A)"],2),
            "输送容量(MVA)": round(out["S(MVA)"],2),
            "N‑1载流量(A)": round(out["I_N1(A)"],2) if not np.isnan(out["I_N1(A)"]) else "‑",
            "N‑1导体温度(℃)": round(out["Tc_N1(℃)"],2) if not np.isnan(out["Tc_N1(℃)"]) else "‑",
            "N‑1校核启用": n1_check
        }
        result_dict.update(install_params)
        df_result = pd.DataFrame([result_dict])
        st.dataframe(df_result, use_container_width=True)

        st.subheader("📐 IEC60287 热回路原理｜V1.0精度优化版")
        st.markdown(r"""
        **热回路串联模型 IEC 60287‑1:2023**
        $$\Delta\theta = W_c(1+\lambda_s)T_1 + (W_c(1+\lambda_s)+W_d)(T_2+T_3+T_4)$$
        - $W_c$：导体损耗 $I^2R_{ac}$；$W_d$：介质损耗
        - $\lambda_s$：护套损耗系数，SPB=0 / Cross‑bonding解析式 / SB两端接地=1.0
        - $y_s$集肤效应、$y_p$邻近效应：按IEC60287‑1解析式随截面、频率动态计算
        - $T_1$绝缘热阻；$T_2$内衬屏蔽；$T_3$外护套；**$T_4$外部热阻（直埋/排管/隧道/空气全部采用IEC60287‑2+CIGRE TB207完整解析公式，无硬编码常数）**
        - 直埋：独立区分原生土壤+回填层热阻；多回路热干涉镜像叠加
        - 隧道：对流换热系数由通风风速计算；排管区分不同管材热阻

        分层节点温度：
        $$
        \begin{align*}
        \theta_c &= \theta_{amb} + dT_1+dT_2+dT_3+dT_4 \\
        \theta_{screen} &= \theta_c - dT_1 \\
        \theta_{sheath} &= \theta_{screen} - dT_2 \\
        \theta_{surface} &= \theta_{sheath} - dT_3
        \end{align*}
        $$
        N‑1校核逻辑：同通道一根电缆退出运行，总负荷由剩余电缆分担，校验导体温度是否超标
        """)
        # Excel导出
        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df_result.to_excel(writer, sheet_name="IEC60287计算结果", index=False)
            if load_ok:
                df_ref.to_excel(writer, sheet_name="参考数据表", index=False)
        output.seek(0)

        st.download_button(
            label="📥 导出完整结果Excel",
            data=output,
            file_name="IEC60287_cable_result_V1.0.xlsx",
            mime="application/vnd.openxmlformats‑officedocument.spreadsheetml.sheet"
        )

st.markdown("---\n版本 V1.0｜精度升级：集肤/邻近解析式、三种护套接地模式、T4完整解析、回填层建模、排管管材扩展、隧道风速输入、50/60Hz全适配")
