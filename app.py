import streamlit as st
import urllib.parse
import time

st.set_page_config(page_title="Aziz Agency", page_icon="🚀", layout="wide")

MY_WA = "923715221906"
LOGO_FILE = "WhatsApp Image 2026-10-28 at 8.45.36 PM.jpeg"

with st.sidebar:
    st.image(LOGO_FILE, width=220)
    st.title("Aziz Digital Agency")
    st.info(f"📞 0{MY_WA[2:]}\n📍 Peshawar\nCloud LIVE")
    st.success("Status LIVE")

st.title("🚀 Aziz AI Marketing Cloud Agent")
st.divider()

def get_data(n):
    name = n.lower()
    if "food" in name or "shawarma" in name:
        return ["Food Business", "Foodies Peshawar", "FB Reels TikTok"]
    if "fashion" in name or "boutique" in name or "cloth" in name:
        return ["Fashion Boutique", "Females Peshawar", "Instagram WhatsApp"]
    return ["Local Business", "Peshawar Audience", "Facebook Google"]

business = st.text_input("Business Name:", placeholder="Peshawar Clothes Shop")

if st.button("Generate PRO Report"):
    if not business:
        st.error("Business Name likho!")
    else:
        with st.spinner("Research..."):
            time.sleep(1)
            niche, audience, platform = get_data(business)
        st.success(f"Report Ready for {business}")
        tab1, tab2 = st.tabs(["Research", "WhatsApp Pitch"])
        with tab1:
            st.info(f"Niche: {niche}\n\nAudience: {audience}\n\nPlatform: {platform}\n\nPackage: Rs 15000/Month")
        with tab2:
            pitch = f"Salam {business} Owner! Main Aziz Digital Agency se hun. Niche {niche}. Hum 30 din me growth denge."
            st.code(pitch)
            encoded = urllib.parse.quote(pitch)
            wa_link = f"https://wa.me/{MY_WA}?text={encoded}"
            st.link_button("Client ko WhatsApp Karo", wa_link)
            st.balloons()

st.divider()
st.caption(f"Powered by Aziz Digital Agency | {MY_WA} | Peshawar")
