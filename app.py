import streamlit as st
import urllib.parse
import time
from datetime import datetime

st.set_page_config(page_title="Aziz Agency PRO", page_icon="🚀", layout="wide")

MY_WA = "923715221906"
BRAND = "Aziz Digital Marketing Agency"

st.markdown("""
<style>
.main-title{color:#FF4B4B;font-weight:800;font-size:2.4rem}
.card{background:#f9f9f9;padding:16px;border-radius:12px;border-left:5px solid #FF4B4B;margin-bottom:10px}
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.title(f"🚀 {BRAND}")
    st.write("Peshawar's AI Marketing Agent")
    st.divider()
    st.info(f"📞 WhatsApp: 0{MY_WA[2:]}\n\n📍 Peshawar, KPK\n\n⏰ Cloud Active")
    st.success("✅ Status: LIVE")
    st.caption(f"Date: {datetime.now().strftime('%d-%m-%Y')}")

st.markdown('<p class="main-title">🚀 Aziz AI Marketing Cloud Agent</p>', unsafe_allow_html=True)
st.write("Client ka business naam likhein, AI pura marketing plan bana dega.")
st.divider()

def get_insights(name):
    n = name.lower()
    if any(x in n for x in ["shawarma","burger","food","pizza","restaurant","cafe","hotel"]):
        return ["Food & Restaurant","18-35 Students & Families Peshawar","Facebook Reels, TikTok","Low Daily Orders"]
    elif any(x in n for x in ["boutique","fashion","cloth","dress","abaya","tailor","libas"]):
        return ["Fashion & Boutique","18-40 Females Peshawar Charsadda","Instagram, WhatsApp Status","Low Collection Reach"]
    elif any(x in n for x in ["mobile","tech","computer","laptop","electronics"]):
        return ["Tech & Mobile Shop","16-35 Students & Tech Lovers","Facebook, YouTube","Trust & Price Issue"]
    else:
        return ["Local Business","20-50 Local Peshawar Audience","Facebook & Google Maps","No Online Presence"]

col1, col2 = st.columns([2, 1])
with col1:
    business = st.text_input("🏢 Client Business Name:", placeholder="e.g. Peshawar Clothes Shop")
with col2:
    service = st.selectbox("📋 Service:", ["Complete 30-Day Plan","Facebook Content","WhatsApp Pitch"])

if st.button("✨ Generate PRO Report", use_container_width=True):
    if not business:
        st.error("⚠️ Pehle Business Name likho!")
    else:
        with st.spinner("🤖 AI Deep Research kar raha hai..."):
            time.sleep(1.4)
            niche, audience, platform, problem = get_insights(business)
        st.success(f"✅ Report Ready for: {business}")
        tab1, tab2, tab3 =
