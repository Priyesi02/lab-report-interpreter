import streamlit as st
from ui.styles import *

# =========================
# KPI CARD
# =========================
def kpi_card(title, value, icon="📊", color=PRIMARY):

    st.markdown(f"""
        <div style="
            background:{CARD};
            border:1px solid {BORDER};
            border-radius:{RADIUS_LG};
            padding:20px;
            box-shadow:{CARD_SHADOW};
        ">

            <div style="color:{TEXT_SECONDARY}; font-size:13px;">
                {icon} {title}
            </div>

            <div style="
                font-size:28px;
                font-weight:800;
                color:{color};
                margin-top:8px;
            ">
                {value}
            </div>

        </div>
    """, unsafe_allow_html=True)


# =========================
# TEST CARD
# =========================
def test_card(item):

    status = item.get("status", "NORMAL").upper()

    color_map = {
        "HIGH": DANGER,
        "LOW": WARNING,
        "CRITICAL": CRITICAL,
        "NORMAL": SUCCESS
    }

    color = color_map.get(status, SUCCESS)

    st.markdown(f"""
        <div style="
            background:{CARD};
            border:1px solid {BORDER};
            border-left:6px solid {color};
            border-radius:{RADIUS_LG};
            padding:18px;
            margin-bottom:12px;
            box-shadow:{CARD_SHADOW};
        ">

            <div style="display:flex; justify-content:space-between;">
                <div style="font-size:16px; font-weight:700; color:{TEXT};">
                    🧬 {item.get("test_name","Test")}
                </div>

                <div style="color:{color}; font-weight:700;">
                    {status}
                </div>
            </div>

            <div style="margin-top:10px; color:{TEXT_SECONDARY};">
                <b>Your Value:</b> {item.get("your_value","")}
            </div>

            <div style="color:{TEXT_SECONDARY};">
                <b>Normal Range:</b> {item.get("normal_range","")}
            </div>

            <div style="margin-top:10px; color:{TEXT}; font-size:14px;">
                {item.get("what_it_means","")}
            </div>

        </div>
    """, unsafe_allow_html=True)


# =========================
# DOCTOR CARD
# =========================
def doctor_card(specialist):

    st.markdown(f"""
        <div style="
            background:{CARD};
            border:1px solid {BORDER};
            border-radius:{RADIUS_XL};
            padding:22px;
            box-shadow:{CARD_SHADOW};
        ">

            <div style="font-size:18px; font-weight:800; margin-bottom:10px;">
                👨‍⚕️ Specialist Recommendation
            </div>

            <div><b>Doctor:</b> {specialist.get("primary_specialist","General Physician")}</div>

            <div style="color:{TEXT_SECONDARY}; margin-top:6px;">
                <b>Urgency:</b> {specialist.get("urgency","")}
            </div>

            <div style="margin-top:10px; color:{TEXT_SECONDARY};">
                {specialist.get("reason","")}
            </div>

        </div>
    """, unsafe_allow_html=True)