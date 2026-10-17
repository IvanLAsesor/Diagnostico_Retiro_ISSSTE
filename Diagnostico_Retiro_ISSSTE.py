import streamlit as st
import calendar
import math
from datetime import date, timedelta
import re

# ============================================================
# CONFIGURACIÓN GENERAL
# ============================================================
st.set_page_config(
    page_title="Diagnóstico ISSSTE",
    page_icon="logo.png",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# ESTILOS Y PALETA
# ============================================================
NAVY = "#0A1A2F"
BLUE = "#1E4470"
GOLD = "#C9A961"
BG = "#F4F6F9"
TEXT = "#182538"

st.markdown(
    f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&family=Playfair+Display:wght@600;700&display=swap');
    html, body, [class*="css"] {{ font-family: 'DM Sans', sans-serif; }}
    .stApp {{ background: {BG}; color: {TEXT}; }}

    .stApp p, .stApp span, .stApp label, .stApp div, .stApp h1, .stApp h2, .stApp h3, .stApp h4 {{
        color: {TEXT} !important;
    }}
    div[data-testid="stWidgetLabel"] label p, div[data-testid="stWidgetLabel"] > div > p {{
        color: {NAVY} !important;
        font-weight: 600 !important;
    }}
    div[data-testid="stCaptionContainer"] p {{ color: #4A5568 !important; }}

    .main-header {{
        background: linear-gradient(125deg, #101d35 0%, #203d60 72%, #8d713d 100%);
        padding: 1.5rem 2rem;
        border-radius: 14px;
        margin-bottom: 1.5rem;
        border: 1px solid rgba(201, 168, 100, .4);
        box-shadow: 0 7px 20px rgba(16, 29, 53, .12);
    }}
    .main-header h1 {{
        color: #FFFFFF !important;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.5) !important;
        margin: 0;
        font-size: 2rem;
        font-weight: 700;
        font-family: 'Playfair Display', serif !important;
    }}
    .main-header p {{
        color: #E1E7EF !important;
        margin: .45rem 0 0 0;
        font-size: 1.05rem;
    }}

    .hero-result {{
        background: linear-gradient(120deg, {NAVY}, {BLUE});
        border-radius: 20px;
        padding: 28px 32px;
        border-bottom: 4px solid {GOLD};
        margin: 20px 0;
    }}
    .hero-result .kicker {{ color: {GOLD} !important; text-transform: uppercase; letter-spacing: 2px; font-size: .75rem; font-weight: 700; }}
    .hero-result .big-number {{ color: #FFFFFF !important; font-size: 3rem; font-weight: 700; font-family: 'Playfair Display', serif !important; margin: 0; }}
    .hero-result .sublabel {{ color: #D8E2F0 !important; font-size: 1rem; margin-top: 10px; }}

    .metric-soft {{
        background: #FFFFFF;
        border: 1px solid #E1E7EF;
        border-radius: 14px;
        padding: 18px 20px;
        border-top: 3px solid {GOLD};
    }}
    .metric-soft .label {{ color: #4A5568 !important; font-size: .78rem; font-weight: 700; text-transform: uppercase; }}
    .metric-soft .value {{ color: {NAVY} !important; font-size: 1.6rem; font-weight: 700; margin-top: 8px; }}
    .metric-soft .note {{ color: #4A5568 !important; font-size: .78rem; margin-top: 6px; }}

    .legal-note {{
        font-size: 0.8rem;
        color: #5A6B82 !important;
        margin-top: 8px;
        line-height: 1.4;
    }}

    .notice-soft {{
        background: #FFF8E6;
        border-left: 4px solid {GOLD};
        border-radius: 8px;
        padding: 14px 18px;
        margin: 12px 0;
        color: #5A4A1A !important;
    }}
    .notice-soft b {{ color: #5A4A1A !important; }}

    .info-soft {{
        background: #E8F0F8;
        border-left: 4px solid {BLUE};
        border-radius: 8px;
        padding: 14px 18px;
        margin: 12px 0;
        color: #1A2E4A !important;
    }}
    .info-soft b {{ color: #1A2E4A !important; }}

    div.stButton > button p {{ color: #FFFFFF !important; }}
    div.stButton > button {{
        background: {NAVY}; color: #FFFFFF !important; border: 1px solid {NAVY}; border-radius: 9px; min-height: 44px; font-weight: 600; width: 100%;
    }}
    div.stButton > button:hover {{ background: {BLUE}; border-color: {GOLD}; }}
    footer {{ visibility: hidden; }}
    </style>
    """,
    unsafe_allow_html=True,
)

# ============================================================
# PARAMETRÍA OFICIAL — ISSSTE RÉGIMEN 2007 (octubre 2026)
# ============================================================
TASA_APORTACION_OBLIGATORIA = 0.113
FACTOR_APORTACION_GOBIERNO = 3.25
LIMITE_AHORRO_SOLIDARIO_GOBIERNO = 0.065
TOPE_FPB_REFERENCIAL = 17885.85
PENSION_GARANTIZADA_2026 = 6922.97
CUOTA_SOCIAL_DIARIA_2026 = 7.15
VALOR_UMA_2026 = 115.50
RENDIMIENTO_PLAN_COMPLEMENTARIO = 0.11  # supuesto propio de planeación

# URV oficial 2026 (semana 12/10/2026) — depende de sexo y edad
URV_2026 = {
    ("Hombre", 65): 11.85973682640888,
    ("Hombre", 66): 11.625745826775857,
    ("Hombre", 67): 11.388381678429171,
    ("Mujer",  65): 13.054335387332456,
    ("Mujer",  66): 12.788108764533897,
    ("Mujer",  67): 12.514684590146164,
}
FECHA_VIGENCIA_URV = "12/10/2026"

# ============================================================
# UTILIDADES
# ============================================================
def money(value):
    return f"${value:,.2f}"

def safe_date(year, month, day):
    last_day = calendar.monthrange(int(year), int(month))[1]
    return date(int(year), int(month), min(int(day), last_day))

def add_years(fecha, years):
    return safe_date(fecha.year + years, fecha.month, fecha.day)

def months_between(start, end):
    if end <= start:
        return 0
    months = (end.year - start.year) * 12 + end.month - start.month
    if end.day < start.day:
        months -= 1
    return max(0, months)

def fv_annuity_consar(payment, factor, periods):
    if periods <= 0 or payment == 0:
        return 0.0
    if abs(factor - 1) < 1e-12:
        return payment * periods
    return payment * ((factor ** periods - 1) / (factor - 1))

def metric_soft(col, label, value, note):
    col.markdown(
        f'<div class="metric-soft"><div class="label">{label}</div>'
        f'<div class="value">{value}</div>'
        f'<div class="note">{note}</div></div>',
        unsafe_allow_html=True,
    )

# ============================================================
# FORMATEO DE FECHA INTERACTIVO
# ============================================================
if 'fecha_nac_str' not in st.session_state:
    st.session_state.fecha_nac_str = "01011975"

def format_fecha():
    val = re.sub(r'[^0-9]', '', st.session_state.fecha_nac_str)
    if len(val) > 4:
        st.session_state.fecha_nac_str = f"{val[:2]}/{val[2:4]}/{val[4:8]}"
    elif len(val) > 2:
        st.session_state.fecha_nac_str = f"{val[:2]}/{val[2:4]}"
    else:
        st.session_state.fecha_nac_str = val

# ============================================================
# MOTOR DE CÁLCULO CORREGIDO
# ============================================================
def calcular_diagnostico(
    nacimiento, corte, sexo, edad_retiro,
    sueldo_basico, saldo_rcv, saldo_voluntario,
    anios_cot, densidad, ahorro_pct,
    rendimiento_bruto_anual, comision_anual,
    bono_nominal=0.0, bono_ya_en_saldo=False,
    cuota_social_diaria=CUOTA_SOCIAL_DIARIA_2026,
):
    fecha_retiro = add_years(nacimiento, edad_retiro)
    n_meses = months_between(corte, fecha_retiro)

    # Factores mensuales oficiales CONSAR
    r_m = (1 + rendimiento_bruto_anual) ** (1 / 12) - 1
    c_m = comision_anual / 12
    factor_mensual = (1 + r_m) * (1 - c_m)

    # Aportaciones
    aportacion_obligatoria = sueldo_basico * TASA_APORTACION_OBLIGATORIA
    ahorro_trabajador = sueldo_basico * (ahorro_pct / 100)
    if ahorro_pct > 0:
        ahorro_gobierno = min(
            ahorro_trabajador * FACTOR_APORTACION_GOBIERNO,
            sueldo_basico * LIMITE_AHORRO_SOLIDARIO_GOBIERNO,
        )
    else:
        ahorro_gobierno = 0.0
    cuota_social_mensual = cuota_social_diaria * 30
    aportacion_mensual = (
        aportacion_obligatoria + ahorro_trabajador
        + ahorro_gobierno + cuota_social_mensual
    )

    # Capitalización
    saldo_inicial = saldo_rcv + saldo_voluntario
    saldo_inicial_cap = saldo_inicial * (factor_mensual ** n_meses)
    aportaciones_cap = fv_annuity_consar(
        aportacion_mensual * densidad, factor_mensual, n_meses
    )

    # Bono con fecha de redención corregida
    bono_cap = 0.0
    fecha_redencion = None
    k = 0
    if bono_nominal > 0 and not bono_ya_en_saldo:
        fecha_55 = add_years(nacimiento, 55)
        meses_faltantes_30 = max(0, math.ceil((30 - anios_cot) * 12))
        fecha_30_cot = corte + timedelta(days=round(meses_faltantes_30 * 365.2425 / 12))
        fecha_redencion_natural = min(fecha_55, fecha_30_cot)
        # Si el evento ya ocurrió, redención inmediata
        fecha_redencion = max(fecha_redencion_natural, corte)
        k = months_between(fecha_redencion, fecha_retiro)
        bono_cap = bono_nominal * (factor_mensual ** k)

    saldo_final = saldo_inicial_cap + aportaciones_cap + bono_cap

    # Pensión mensual (sin descuento de sobrevivencia)
    urv = URV_2026.get((sexo, edad_retiro))
    if urv is None:
        raise ValueError(f"URV no disponible para ({sexo}, {edad_retiro})")

    pension_calculada = saldo_final / (12 * urv) if urv else 0.0
    pension_base = max(pension_calculada, PENSION_GARANTIZADA_2026)

    # Complemento FPB (solo 65 años)
    complemento_fpb = 0.0
    if edad_retiro >= 65:
        if sueldo_basico >= TOPE_FPB_REFERENCIAL:
            complemento_fpb = max(0.0, TOPE_FPB_REFERENCIAL - pension_base)
        else:
            complemento_fpb = max(0.0, sueldo_basico - pension_base)

    pension_total = pension_base + complemento_fpb
    tasa_reemplazo = (pension_base / sueldo_basico * 100) if sueldo_basico > 0 else 0.0

    anios_futuros = (n_meses / 12) * densidad
    anios_totales = anios_cot + anios_futuros

    return {
        "n_meses": n_meses,
        "factor_mensual": factor_mensual,
        "r_m": r_m, "c_m": c_m,
        "aportacion_mensual": aportacion_mensual,
        "saldo_inicial_cap": saldo_inicial_cap,
        "aportaciones_cap": aportaciones_cap,
        "bono_cap": bono_cap,
        "fecha_redencion": fecha_redencion,
        "k_meses_bono": k,
        "saldo_final": saldo_final,
        "urv": urv,
        "pension_calculada": pension_calculada,
        "pension_base": pension_base,
        "complemento_fpb": complemento_fpb,
        "pension_total": pension_total,
        "tasa_reemplazo": tasa_reemplazo,
        "anios_totales": anios_totales,
        "cumple_25": anios_totales >= 25.0,
    }

# ============================================================
# ENCABEZADO PRINCIPAL
# ============================================================
col_logo, col_titulo = st.columns([1, 5], vertical_alignment="center")

with col_logo:
    try:
        st.image("logo.png", width=120)
    except Exception:
        st.markdown('<div style="font-size:3rem;text-align:center;">🛡️</div>', unsafe_allow_html=True)

with col_titulo:
    st.markdown("""
    <div class="main-header">
        <h1 style="color: #FFFFFF !important; text-shadow: 2px 2px 4px rgba(0,0,0,0.5); margin: 0; font-family: 'Playfair Display', serif;">
            Diagnóstico de Retiro Patrimonial ISSSTE
        </h1>
        <p style="color: #E1E7EF !important; margin: .45rem 0 0 0; font-size: 1.05rem;">
            Régimen de Cuentas Individuales (reforma 2007). Estimación basada en metodología CONSAR 2026.
        </p>
    </div>
    """, unsafe_allow_html=True)

# ============================================================
# AVISO DE PRIVACIDAD
# ============================================================
with st.expander("Consultar aviso de privacidad simplificado"):
    st.markdown("""
    **Responsable del tratamiento:** Iván Lenz, asesor patrimonial independiente.

    **Datos que se solicitan:** nombre, teléfono y datos generales laborales y financieros que captures voluntariamente.

    **Finalidad:** elaborar un diagnóstico estimado de retiro y, cuando corresponda, preparar un reporte PDF para entregártelo y dar seguimiento a la consulta que solicitaste.

    **Uso y resguardo:** los datos deben tratarse únicamente para estas finalidades y no deben compartirse con terceros ajenos al servicio sin una base legal aplicable o tu autorización. No introduzcas contraseñas, números completos de identificación ni información que no sea necesaria.

    **Derechos y contacto:** para solicitar acceso, rectificación, cancelación u oponerte al tratamiento, contacta al asesor que te compartió este formulario por el mismo medio.

    **Importante:** este texto es un aviso simplificado provisional; antes de publicar o distribuir ampliamente la aplicación, debe completarse con los datos de contacto, medios de ejercicio de derechos y demás elementos legales aplicables.
    """)

acepta_privacidad = st.checkbox(
    "He leído el aviso de privacidad y autorizo el uso de los datos que capture para elaborar mi diagnóstico.",
    value=False,
    help="El formulario no mostrará los campos de captura hasta que marques esta casilla."
)

# ============================================================
# FLUJO PRINCIPAL
# ============================================================
if acepta_privacidad:

    # ---------- PANEL LATERAL ----------
    with st.sidebar:
        st.markdown("## Parámetros del diagnóstico")
        corte = st.date_input("Fecha de corte", value=date.today())
        edad_retiro = st.selectbox("Edad de retiro", [65, 66, 67], index=0)
        rendimiento_bruto_anual = st.selectbox(
            "Rendimiento real anual", [0.04, 0.05], index=0,
            format_func=lambda v: f"{v:.0%}"
        )
        comision_anual = st.number_input(
            "Comisión anual AFORE (%)", min_value=0.0, max_value=2.0,
            value=0.57, step=0.01
        ) / 100
        densidad = st.slider("Densidad de cotización (%)", 50, 100, 80, 5) / 100

        st.markdown("---")
        st.markdown("### Parámetros actuariales")
        st.caption(f"URV aplicada: se selecciona por sexo y edad.")
        st.caption(f"Vigencia tabla: {FECHA_VIGENCIA_URV}")
        st.caption(f"Pensión Garantizada 2026: {money(PENSION_GARANTIZADA_2026)}")
        st.caption(f"Cuota social diaria: {money(CUOTA_SOCIAL_DIARIA_2026)}")

        st.markdown("---")
        st.markdown("### Ajustes avanzados (supuestos propios)")
        aplicar_tope_uma = st.checkbox(
            "Aplicar tope legal de 10 UMAs al sueldo",
            value=False,
            help="La metodología CONSAR no aplica este tope. Actívalo solo si deseas simular el límite legal de cotización."
        )

    # ---------- FORMULARIO ----------
    ca, cb = st.columns(2, gap="large")

    with ca:
        st.markdown("#### 01 · Perfil y cuenta individual")

        st.text_input(
            "Fecha de nacimiento (DD/MM/AAAA)",
            key="fecha_nac_str",
            on_change=format_fecha,
            max_chars=10,
            help="Escribe solo los números; el sistema coloca las diagonales automáticamente."
        )

        try:
            dia_nac, mes_nac, ano_nac = map(int, st.session_state.fecha_nac_str.split('/'))
            nacimiento = date(ano_nac, mes_nac, dia_nac)
        except Exception:
            nacimiento = date(1975, 1, 1)

        ano_afiliacion = st.number_input(
            "Año de afiliación al ISSSTE",
            min_value=1960, max_value=date.today().year,
            value=2000, step=1
        )
        anios_cot_aprox = max(0, date.today().year - ano_afiliacion)
        st.caption(f"Años cotizados aproximados: **{anios_cot_aprox} años**")

        edad_al_afiliarse = ano_afiliacion - nacimiento.year
        if edad_al_afiliarse < 15 or edad_al_afiliarse > 80:
            st.error(
                f"⚠️ Error en las fechas: tendrías **{edad_al_afiliarse} años** "
                f"al afiliarte. Revisa tu fecha de nacimiento o año de afiliación."
            )
            st.stop()

        sexo = st.selectbox("Sexo", ["Mujer", "Hombre"])

        sueldo_ingresado = st.number_input(
            "Sueldo básico mensual ($)", min_value=1.0,
            value=25000.0, step=500.0
        )
        st.caption(f"**Monto capturado: {money(sueldo_ingresado)}**")

        if aplicar_tope_uma:
            sbc_maximo = VALOR_UMA_2026 * 10 * 30.4
            sueldo_basico = min(sueldo_ingresado, sbc_maximo)
            if sueldo_ingresado > sbc_maximo:
                st.caption(f"⚠️ Sueldo topado a 10 UMAs: **{money(sueldo_basico)}**")
        else:
            sueldo_basico = sueldo_ingresado

        rcv = st.number_input(
            "Saldo actual en tu AFORE ($)", min_value=0.0,
            value=500000.0, step=10000.0
        )
        st.caption(f"**Monto capturado: {money(rcv)}**")

        voluntario = st.number_input(
            "Ahorro voluntario actual ($)", min_value=0.0,
            value=0.0, step=1000.0
        )

    with cb:
        st.markdown("#### 02 · Aportaciones y Bono")
        ahorro_pct = st.selectbox(
            "Ahorro Solidario del trabajador", [0, 1, 2], index=0,
            format_func=lambda v: f"{v}% del sueldo básico"
        )
        anios_cot = st.number_input(
            "Años cotizados al ISSSTE", min_value=0.0, max_value=50.0,
            value=float(anios_cot_aprox), step=0.5
        )

        bono_opcion = st.radio(
            "¿Cuenta con Bono de Pensión ISSSTE?",
            ["No / no confirmado", "Sí, con valor nominal confirmado"],
            index=0
        )
        bono = st.number_input(
            "Valor nominal del Bono ($)", min_value=0.0, value=0.0,
            step=10000.0,
            disabled=bono_opcion != "Sí, con valor nominal confirmado"
        )
        bono_ya_en_saldo = st.checkbox(
            "El Bono ya está reflejado en el saldo", value=False
        )

    st.markdown("---")
    st.markdown("#### 🎯 Tu pensión ideal")
    st.caption("Ingresa el monto mensual que te gustaría recibir al jubilarte.")
    pension_ideal = st.number_input(
        "Pensión mensual deseada (MXN)", min_value=0.0,
        value=float(round(sueldo_basico, -2)), step=500.0, format="%.2f"
    )
    st.caption(f"**Monto capturado: {money(pension_ideal)}**")

    # ---------- CÁLCULO ----------
    try:
        resultado = calcular_diagnostico(
            nacimiento=nacimiento,
            corte=corte,
            sexo=sexo,
            edad_retiro=edad_retiro,
            sueldo_basico=sueldo_basico,
            saldo_rcv=rcv,
            saldo_voluntario=voluntario,
            anios_cot=anios_cot,
            densidad=densidad,
            ahorro_pct=ahorro_pct,
            rendimiento_bruto_anual=rendimiento_bruto_anual,
            comision_anual=comision_anual,
            bono_nominal=bono if bono_opcion == "Sí, con valor nominal confirmado" else 0.0,
            bono_ya_en_saldo=bono_ya_en_saldo,
        )
    except ValueError as e:
        st.error(f"⚠️ {e}")
        st.stop()

    # ---------- RESULTADOS ----------
    st.markdown("---")
    st.markdown("## Tu diagnóstico de retiro")

    if not resultado["cumple_25"]:
        st.markdown(f"""
        <div class="notice-soft">
            <b>⚠️ Aún no cumples el requisito de 25 años cotizados</b><br><br>
            Con los datos capturados, alcanzarías <b>{resultado['anios_totales']:.1f} años</b> de cotización.
            La pensión por Cesantía en Edad Avanzada o Vejez del ISSSTE requiere al menos 25 años.
        </div>
        """, unsafe_allow_html=True)
        metric_soft(
            st, "Saldo acumulado al retiro",
            money(resultado["saldo_final"]),
            "Ahorros finales estimados en tu AFORE."
        )
    else:
        st.markdown(f"""
        <div class="hero-result">
            <div class="kicker">Tu pensión mensual estimada</div>
            <div class="big-number">{money(resultado['pension_total'])} MXN</div>
            <div class="sublabel">
                Proyección al jubilarte a los <b>{edad_retiro} años</b>
                · URV aplicada ({sexo}): <b>{resultado['urv']:.4f}</b>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div class="legal-note">
            * Resultado ilustrativo y estimado. No representa resolución oficial ni garantiza el monto de pensión.
            El cálculo definitivo lo realiza el ISSSTE con base en tus semanas y salario registrados.
        </div>
        """, unsafe_allow_html=True)

        c1, c2, c3 = st.columns(3, gap="medium")
        with c1:
            metric_soft(
                c1, "Saldo al retirarte",
                money(resultado["saldo_final"]),
                "Lo que tendrías en tu AFORE."
            )
        with c2:
            metric_soft(
                c2, "Tasa de reemplazo",
                f"{resultado['tasa_reemplazo']:.1f}%",
                "Porcentaje de tu sueldo actual."
            )
        with c3:
            if resultado["complemento_fpb"] > 0:
                metric_soft(
                    c3, "Apoyo del gobierno",
                    money(resultado["complemento_fpb"]),
                    "Complemento del FPB."
                )
            else:
                metric_soft(
                    c3, "Sin apoyo adicional", "—",
                    "Tu pensión ya cubre tu sueldo o supera el tope."
                )

        with st.expander("🔍 Ver cálculo paso a paso"):
            fr = resultado["fecha_redencion"]
            st.markdown(f"""
            **Factores oficiales CONSAR**
            - Meses al retiro: **{resultado['n_meses']}**
            - r mensual: **{resultado['r_m']:.8f}**
            - c mensual: **{resultado['c_m']:.8f}**
            - Factor mensual `(1+r_m)(1-c_m)`: **{resultado['factor_mensual']:.8f}**

            **Capitalización**
            - Aportación mensual total: **{money(resultado['aportacion_mensual'])}**
            - Saldo inicial capitalizado: **{money(resultado['saldo_inicial_cap'])}**
            - Aportaciones futuras capitalizadas: **{money(resultado['aportaciones_cap'])}**
            - Bono capitalizado: **{money(resultado['bono_cap'])}**
              - Fecha de redención: **{fr.strftime('%d/%m/%Y') if fr else '—'}**
              - Meses redención→retiro (k): **{resultado['k_meses_bono']}**
            - **Saldo final: {money(resultado['saldo_final'])}**

            **Pensión**
            - URV ({sexo}, {edad_retiro}): **{resultado['urv']:.6f}**
            - Pensión calculada: **{money(resultado['pension_calculada'])}**
            - Piso PG 2026: **{money(PENSION_GARANTIZADA_2026)}**
            - Pensión base: **{money(resultado['pension_base'])}**
            - Complemento FPB: **{money(resultado['complemento_fpb'])}**
            - **Pensión total: {money(resultado['pension_total'])}**
            """)

    # ---------- AHORRO COMPLEMENTARIO (proyección propia) ----------
    if resultado["cumple_25"] and pension_ideal > resultado["pension_total"]:
        brecha_mensual = pension_ideal - resultado["pension_total"]
        n_meses = resultado["n_meses"]

        st.markdown("---")
        st.markdown("## Complementa tu pensión con un plan de ahorro")
        st.markdown("""
        <div class="legal-note">
            <b>Nota:</b> esta sección es una <b>proyección propia de planeación patrimonial</b>,
            no forma parte de la metodología oficial CONSAR/PENSIONISSSTE. Los supuestos de
            rendimiento (11% anual) y esperanza de vida (15 años) son referenciales.
        </div>
        """, unsafe_allow_html=True)
        st.markdown(f"""
        <div class="info-soft">
            Tu pensión ideal es <b>{money(pension_ideal)}</b> y la estimada es <b>{money(resultado['pension_total'])}</b>.
            Faltan <b>{money(brecha_mensual)} al mes</b>.
        </div>
        """, unsafe_allow_html=True)

        ae_aprox = 15.0
        capital_necesario = brecha_mensual * 12 * ae_aprox
        tasa_mensual_plan = RENDIMIENTO_PLAN_COMPLEMENTARIO / 12

        if n_meses > 0:
            factor_acumulacion = ((1 + tasa_mensual_plan) ** n_meses - 1) / tasa_mensual_plan
        else:
            factor_acumulacion = 0.0

        aportacion_ideal = capital_necesario / factor_acumulacion if factor_acumulacion > 0 else 0.0
        tope_mensual = 5000.00

        if aportacion_ideal <= tope_mensual:
            st.markdown(f"""
            <div class="hero-result" style="background: linear-gradient(120deg, #1B3B5F, #2D5A8A);">
                <div class="kicker">Plan de ahorro complementario</div>
                <div class="big-number">{money(max(2000, aportacion_ideal))} / mes</div>
                <div class="sublabel">Aportando esta cantidad mensual (mínimo $2,000) alcanzarías tu meta.</div>
            </div>
            """, unsafe_allow_html=True)
            c1, c2 = st.columns(2, gap="medium")
            with c1:
                metric_soft(c1, "Aportación mensual",
                            money(max(2000, aportacion_ideal)),
                            "Domiciliada los primeros días del mes.")
            with c2:
                metric_soft(c2, "Anualidad extra", "$0.00",
                            "No necesitas aportaciones anuales extra.")
        else:
            aportacion_mensual_topada = tope_mensual
            vf_mensualidades = aportacion_mensual_topada * factor_acumulacion
            capital_faltante = max(0.0, capital_necesario - vf_mensualidades)

            if n_meses > 0:
                anios_restantes = n_meses / 12
                factor_anual = ((1 + RENDIMIENTO_PLAN_COMPLEMENTARIO) ** anios_restantes - 1) / RENDIMIENTO_PLAN_COMPLEMENTARIO
                anualidad_extra = capital_faltante / factor_anual if factor_anual > 0 else 0.0
            else:
                anualidad_extra = 0.0

            st.markdown(f"""
            <div class="hero-result" style="background: linear-gradient(120deg, #8B4513, #CD853F);">
                <div class="kicker">Plan mixto (Mensual + Anual)</div>
                <div class="big-number">{money(aportacion_mensual_topada)} / mes</div>
                <div class="sublabel">Máximo mensual permitido + aportación anual extra.</div>
            </div>
            """, unsafe_allow_html=True)
            st.markdown(f"""
            <div class="notice-soft">
                💡 <b>Estrategia de aguinaldo:</b> la mensualidad requerida supera los $5,000.
                Sugerimos aportar <b>{money(anualidad_extra)} una vez al año</b>
                (por ejemplo, en tu aguinaldo) para compensar.
            </div>
            """, unsafe_allow_html=True)
            c1, c2 = st.columns(2, gap="medium")
            with c1:
                metric_soft(c1, "Aportación mensual",
                            money(aportacion_mensual_topada),
                            "Tope máximo recomendado.")
            with c2:
                metric_soft(c2, "Anualidad extra requerida",
                            money(anualidad_extra),
                            "En el mes de aguinaldo.")

        st.markdown("---")
        st.markdown("### 📊 Tu pensión total estimada con plan complementario")
        pension_total_plan = resultado["pension_total"] + brecha_mensual
        st.markdown(f"""
        <div class="hero-result">
            <div class="kicker">Pensión total estimada</div>
            <div class="big-number">{money(pension_total_plan)} MXN</div>
            <div class="sublabel">
                ISSSTE: <b>{money(resultado['pension_total'])}</b>
                + Ahorro: <b>{money(brecha_mensual)}</b>
            </div>
        </div>
        """, unsafe_allow_html=True)

    elif resultado["cumple_25"] and pension_ideal <= resultado["pension_total"]:
        st.markdown("---")
        st.markdown("## ✅ Tu pensión ideal está cubierta")
        st.markdown(f"""
        <div class="info-soft">
            Con los datos capturados, tu pensión estimada (<b>{money(resultado['pension_total'])}</b>)
            ya iguala o supera tu meta (<b>{money(pension_ideal)}</b>).
            No necesitas ahorro complementario.
        </div>
        """, unsafe_allow_html=True)