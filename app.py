import streamlit as st
import time

st.set_page_config(page_title="Aziz Digital Marketing Agent", page_icon="🚀")
st.title("🚀 Aziz Digital Marketing Agent")
st.write("*Auto Cloud Agent - So jao to soye, Utho to uthe!*")
st.divider()

# Input
business = st.text_input("Client ka Business Name likho:", placeholder="e.g. Peshawar Shawarma House")
research_type = st.selectbox("Kya kaam karna hai?", ["Client Research", "Facebook Content", "WhatsApp Pitch"])

if st.button("Research Shuru Karo 🚀"):
    if business == "":
        st.warning("Pehle Business Name to likho Aziz Bhai!")
    else:
        with st.spinner('Cloud Agent kaam kar raha hai...'):
            time.sleep(2)
        
        name = business.lower()
        
        # --- LOGIC FOR DUNU ---
        if any(x in name for x in ["shawarma","burger","food","pizza","restaurant", "cafe", "hotel"]):
            niche="Food / Restaurant"
            audience="18-35, Students, Food Lovers, University Road Peshawar"
            platform="Facebook, Instagram, TikTok, Foodpanda"
            content_idea = f"1. Spicy Shawarma Challenge Video\n2. Behind the scenes - {business} ki kitchen\n3. Customer Review Post"
        elif any(x in name for x in ["boutique","fashion","cloth","ladies","abaya","dress"]):
            niche="Fashion / Boutique"
            audience="18-40, Females, Peshawar, Charsadda"
            platform="Instagram, Facebook, WhatsApp Status"
            content_idea = f"1. New Collection Reel - {business}\n2. Price & Design Post\n3. Eid Offer Story"
        else:
            niche="General Business"
            audience="18-45, Local Peshawar Audience"
            platform="Facebook & Instagram"
            content_idea = f"1. Introduction Post for {business}\n2. Services List\n3. Contact Us Post"

        st.success(f"Research Report for {business} - READY!")
        
        col1, col2 = st.columns(2)
        with col1:
            st.info(f"*Niche:* {niche}\n\n*Audience:* {audience}\n\n*Best Platform:* {platform}")
        with col2:
            st.warning(f"*Content Plan:*\n{content_idea}")

        # --- WHATSAPP CLOUD FEATURE ---
        st.divider()
        st.subheader("📱 WhatsApp Cloud Agent")
        wa_message = f"Salam Sir! Apke business {business} ki research ho gayi. Niche: {niche}. Audience: {audience}. Best Platform: {platform}. Kya me pura 30 din ka plan bana dun? - Aziz Digital Marketing"
        
        # Ye link client ko direct WhatsApp pe le jayega
        wa_link = f"https://wa.me/?text={wa_message.replace(' ', '%20')}"
        st.write("Ye message copy karke client ko bhejo, ya neeche button dabao:")
        st.code(wa_message)
        st.link_button("WhatsApp Pe Bhejo 🚀", wa_link)

