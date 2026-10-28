import streamlit as st

st.set_page_config(page_title="Aziz Digital Marketing Agent", page_icon="🚀")
st.title("🚀 Aziz Digital Marketing Agent")
st.write("Free AI Agent for Client Research, Internet Research & Facebook Content")
st.divider()

business = st.text_input("Client ka Business Name likho:", placeholder="e.g. Peshawar Shawarma House")
research_type = st.selectbox("Kya kaam karna hai?", ["Client Research", "Facebook Content", "WhatsApp Pitch", "Full Pro Report (Sab Kuch)"])

if st.button("Research Shuru Karo ✨"):
    if business == "":
        st.warning("Pehle Business Name to likho Aziz Bhai!")
    else:
        name = business.lower()
        if any(x in name for x in ["shawarma","burger","food","pizza","restaurant"]):
            niche="Food / Restaurant"
            audience="18-35, Students, Food Lovers, University Road Peshawar"
            platform="Facebook, Instagram, TikTok, Foodpanda"
            competitors="Chashnagheer, Jalil & Sons, Peshawar Confectionary"
            strategy="Daily 1 Reel (Making), 2 Stories (Offer), Customer Reviews"
            posts=[f"🔥 {business} ka Special Zinger - Sirf Rs.350!", f"😋 Bhook lagi hai? {business} se 30 min me delivery!", f"📸 Best Shawarma in Peshawar - {business}"]
        elif any(x in name for x in ["cloth","fashion","boutique","garments","shoes"]):
            niche="Clothes / Fashion"
            audience="18-40, Ladies & Gents, Shaadi Season, Peshawar"
            platform="Facebook, Instagram, TikTok Shop"
            competitors="Khaadi, Bonanza, Local Garments"
            strategy="Daily 1 Outfit Photo, Live Weekly"
            posts=[f"👗 New Winter Collection - {business} par Discount!", f"✨ Shaadi Season Offer - {business}", f"🔥 Buy 2 Get 1 Free - {business}"]
        else:
            niche="General Business"
            audience="18-45, Local Peshawar"
            platform="Facebook & Instagram"
            competitors="Top 3 Local Pages"
            strategy="Daily 1 Post + 2 Stories"
            posts=[f"🚀 {business} - Behtareen Quality!", f"🔥 Special Offer - {business}", f"❤️ Customer Love - {business}"]

        st.success(f"{business} ke liye Report tayyar hai!")
        st.markdown(f"### Research Report for {business}")
        st.markdown(f"*Niche:* {niche}")
        st.write(f"*Target Audience:* {audience}")
        st.write(f"*Best Platform:* {platform}")
        st.write(f"*Competitors:* {competitors}")
        st.write(f"*Content Strategy:* {strategy}")

        if research_type in ["Facebook Content", "Full Pro Report (Sab Kuch)"]:
            st.divider()
            st.markdown("### 📱 Facebook Posts:")
            for p in posts:
                st.info(p)
        
        if research_type in ["WhatsApp Pitch", "Full Pro Report (Sab Kuch)"]:
            st.divider()
            st.markdown("### 💬 WhatsApp Pitch:")
            pitch = f"As-salamu Alaikum! {business} Owner\n\nMaine aap ke liye Free Research ki hai.\nTarget: {audience}\nPlatform: {platform}\n\nKya 5 min Free Call ho sakti hai? - Aziz"
            st.code(pitch)
