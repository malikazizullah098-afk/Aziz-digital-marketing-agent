import streamlit as st

st.set_page_config(page_title="Aziz Digital Marketing Agent", page_icon="🚀")

st.title("🚀 Aziz Digital Marketing Agent")
st.write("Free AI Agent for Client Research, Internet Research & Facebook Content")

st.divider()

business = st.text_input("Client ka Business Name likho:", placeholder="e.g. Peshawar Shawarma House")

research_type = st.selectbox("Kya kaam karna hai?", 
    ["Client Research", "Internet Research", "Facebook Content Ideas", "Facebook Post Writer"])

if st.button("Research Shuru Karo ✨"):
    if business == "":
        st.warning("Pehle Business ka naam likho Aziz Bhai!")
    else:
        st.success(f"{business} ke liye {research_type} tayyar ho raha hai...")
        st.write("---")
        if research_type == "Facebook Content Ideas":
            st.write(f"### 📱 {business} ke liye 3 Viral Post Ideas:")
            st.write(f"1. *Behind the Scenes:* {business} ki daily routine ki video")
            st.write(f"2. *Offer Post:* Aaj {business} par 10% Discount!")
            st.write(f"3. *Customer Review:* Happy customer ki photo + review")
        elif research_type == "Facebook Post Writer":
            st.write(f"### ✍️ Ready Post for {business}:")
            st.write(f"🔥 Attention {business} Lovers! 🔥\n\nKya aap ne hamara naya product try kiya? \n\nAaj hi visit karen aur apna feedback den! \n\n#Peshawar #Marketing #Trending")
        else:
            st.write(f"### 🔍 Research Report for {business}:")
            st.write(f"- Target Audience: 18-35 age, Peshawar/KPK")
            st.write(f"- Best Platform: Facebook & Instagram")
            st.write(f"- Competitors: Top 3 pages in same niche")
            st.write(f"- Content Strategy: Daily 1 post + 2 stories")

st.divider()
st.caption("Made with ❤️ by Aziz - Digital Marketing Agent")
