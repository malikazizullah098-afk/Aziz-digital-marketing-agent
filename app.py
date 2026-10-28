import os
import time
import urllib.parse
from datetime import date

import streamlit as st

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
st.set_page_config(page_title="Aziz Agency", page_icon="🚀", layout="wide")

MY_WA = "923715221906"
AGENCY = "Aziz Digital Agency"
LOGO_FILE = "WhatsApp Image 2026-10-28 at 8.45.36 PM.jpeg"

PACKAGES = {
    "Starter": {
        "price": 15000,
        "items": ["1 platform manage", "12 posts / month", "Basic page setup", "Monthly report"],
    },
    "Growth": {
        "price": 25000,
        "items": ["2 platforms manage", "20 posts + 4 reels", "Ads setup + management", "Weekly report"],
    },
    "Pro": {
        "price": 40000,
        "items": ["3 platforms manage", "30 posts + 8 reels", "Ads + WhatsApp lead funnel", "Weekly report + call"],
    },
}

# Each niche: keywords (English + Roman Urdu), and the research data.
NICHES = {
    "Food / Restaurant": {
        "keywords": ["food", "shawarma", "restaurant", "burger", "pizza", "cafe", "bakery",
                     "tikka", "karahi", "chai", "biryani", "fast food", "dhaba", "khana"],
        "audience": "Foodies, families, students and office workers (18-40)",
        "platforms": ["Facebook", "TikTok", "Instagram Reels"],
        "hook": "Free delivery ya combo deal pehle 50 customers ke liye",
        "content": [
            "Food making reel (close-up, sizzling shots)",
            "Menu + price post with WhatsApp order button",
            "Customer review / reaction video",
            "Behind the kitchen story",
            "Weekend combo offer post",
            "Poll: 'Aaj kya khaoge?'",
        ],
        "hashtags": ["#PeshawarFood", "#FoodiesPeshawar", "#PeshawarEats", "#KhyberPakhtunkhwa"],
        "ad_split": "70% Facebook/Instagram ads (radius 5-8 km), 30% TikTok",
    },
    "Fashion / Boutique": {
        "keywords": ["fashion", "boutique", "cloth", "clothes", "garment", "suit", "dress",
                     "lawn", "kapra", "kapray", "shoes", "jewellery", "jewelry", "abaya"],
        "audience": "Women and girls 18-40, wedding shoppers, Instagram users",
        "platforms": ["Instagram", "Facebook", "WhatsApp Catalog"],
        "hook": "New collection launch + free home delivery",
        "content": [
            "New arrival carousel (3-5 photos)",
            "Styling reel: 1 suit, 3 looks",
            "Customer try-on / unboxing video",
            "Price + size guide post",
            "Eid / wedding season collection",
            "Story: 'DM for price' with WhatsApp link",
        ],
        "hashtags": ["#PeshawarFashion", "#PeshawariBoutique", "#LawnCollection", "#PakistaniFashion"],
        "ad_split": "60% Instagram ads, 30% Facebook, 10% retargeting",
    },
    "Beauty / Salon": {
        "keywords": ["salon", "beauty", "parlour", "parlor", "makeup", "bridal", "hair",
                     "barber", "spa", "skin", "mehndi"],
        "audience": "Women 18-45, brides and their families; men for barber services",
        "platforms": ["Instagram", "Facebook", "WhatsApp"],
        "hook": "Free consultation + bridal package discount",
        "content": [
            "Before / after transformation reel",
            "Bridal makeup showcase",
            "Service price list post",
            "Tips: skin / hair care short video",
            "Client testimonial",
            "Booking announcement with WhatsApp link",
        ],
        "hashtags": ["#PeshawarSalon", "#BridalMakeup", "#PeshawarBeauty", "#MakeupArtist"],
        "ad_split": "60% Instagram, 40% Facebook (local area + lookalike)",
    },
    "Clinic / Medical": {
        "keywords": ["clinic", "doctor", "dental", "dentist", "hospital", "medical", "pharmacy",
                     "lab", "diagnostic", "skin clinic", "physio"],
        "audience": "Families, parents, elderly and patients searching locally",
        "platforms": ["Facebook", "Google Business Profile", "WhatsApp"],
        "hook": "Free first consultation / health camp announcement",
        "content": [
            "Health tip of the week (short video)",
            "Doctor introduction post",
            "Patient awareness infographic",
            "Clinic timings + location post",
            "Common myths vs facts",
            "Appointment booking via WhatsApp",
        ],
        "hashtags": ["#PeshawarDoctor", "#HealthTips", "#PeshawarClinic", "#KPKHealth"],
        "ad_split": "50% Google local ads, 50% Facebook (radius 10 km)",
    },
    "Education / Academy": {
        "keywords": ["academy", "school", "tuition", "coaching", "college", "institute",
                     "course", "training", "english", "quran", "madrassa", "university"],
        "audience": "Parents (28-50) and students (14-25)",
        "platforms": ["Facebook", "YouTube", "WhatsApp Groups"],
        "hook": "Free demo class + early admission discount",
        "content": [
            "Teacher introduction video",
            "Student results / success story",
            "Free tips video (exam preparation)",
            "Admission open post with fee structure",
            "Classroom tour reel",
            "Parent testimonial",
        ],
        "hashtags": ["#PeshawarAcademy", "#AdmissionOpen", "#PeshawarEducation", "#StudyTips"],
        "ad_split": "70% Facebook lead ads, 30% YouTube",
    },
    "Real Estate": {
        "keywords": ["property", "real estate", "estate", "plot", "house", "flat", "apartment",
                     "builder", "construction", "society", "makan", "zameen"],
        "audience": "Investors, overseas Pakistanis, families 28-55",
        "platforms": ["Facebook", "YouTube", "WhatsApp"],
        "hook": "Site visit booking + limited-time payment plan",
        "content": [
            "Property walkthrough video",
            "Drone / location shots",
            "Price + payment plan post",
            "Area development update",
            "Client handover story",
            "Investment tips short video",
        ],
        "hashtags": ["#PeshawarProperty", "#RealEstatePakistan", "#PlotsForSale", "#InvestInPeshawar"],
        "ad_split": "80% Facebook lead ads, 20% YouTube",
    },
    "Electronics / Mobile": {
        "keywords": ["mobile", "phone", "electronic", "laptop", "computer", "gadget",
                     "accessories", "camera", "repair", "tech"],
        "audience": "Students, young professionals, gamers (16-35)",
        "platforms": ["Facebook", "TikTok", "Instagram"],
        "hook": "Warranty + price match guarantee",
        "content": [
            "Product unboxing reel",
            "Price list / new stock post",
            "Comparison: product A vs B",
            "Customer pickup photo",
            "Tech tip short video",
            "Flash sale announcement",
        ],
        "hashtags": ["#PeshawarMobile", "#TechPakistan", "#MobileShop", "#NewArrival"],
        "ad_split": "60% Facebook, 40% TikTok",
    },
    "Gym / Fitness": {
        "keywords": ["gym", "fitness", "trainer", "workout", "bodybuilding", "yoga", "crossfit"],
        "audience": "Men and women 18-40 who want fitness results",
        "platforms": ["Instagram", "TikTok", "Facebook"],
        "hook": "Free 3-day trial + joining fee waiver",
        "content": [
            "Transformation before / after",
            "Workout of the day reel",
            "Trainer introduction",
            "Diet tip short video",
            "Member milestone post",
            "Membership offer post",
        ],
        "hashtags": ["#PeshawarGym", "#FitnessPakistan", "#GymMotivation", "#Transformation"],
        "ad_split": "60% Instagram, 40% TikTok",
    },
    "Auto / Workshop": {
        "keywords": ["car", "auto", "workshop", "garage", "tyre", "tire", "bike",
                     "motorcycle", "showroom", "mechanic", "detailing"],
        "audience": "Car and bike owners, buyers 22-50",
        "platforms": ["Facebook", "YouTube", "Google Business Profile"],
        "hook": "Free inspection + service discount coupon",
        "content": [
            "Car detailing before / after",
            "Service price list",
            "Customer car delivery photo",
            "Maintenance tip short video",
            "New stock / vehicle showcase",
            "Google review request post",
        ],
        "hashtags": ["#PeshawarCars", "#CarDetailing", "#AutoWorkshop", "#PakistanCars"],
        "ad_split": "50% Google local ads, 50% Facebook",
    },
    "Wedding / Events": {
        "keywords": ["wedding", "event", "marquee", "hall", "catering", "decor",
                     "photography", "photographer", "shadi", "barat"],
        "audience": "Families planning weddings, brides and grooms (22-40)",
        "platforms": ["Instagram", "Facebook", "YouTube"],
        "hook": "Early booking discount + free consultation",
        "content": [
            "Event highlight reel",
            "Decor / setup showcase",
            "Package price post",
            "Client testimonial video",
            "Behind the scenes",
            "Booking dates available post",
        ],
        "hashtags": ["#PeshawarWedding", "#WeddingPakistan", "#EventPlanner", "#ShadiSeason"],
        "ad_split": "60% Instagram, 40% Facebook",
    },
    "Grocery / General Store": {
        "keywords": ["grocery", "store", "mart", "supermarket", "kiryana", "kariyana",
                     "bakers", "dairy", "milk", "fruit", "sabzi"],
        "audience": "Households and nearby neighbourhoods",
        "platforms": ["Facebook", "WhatsApp Catalog", "Google Business Profile"],
        "hook": "Free home delivery above a minimum order",
        "content": [
            "Weekly offers post",
            "Fresh stock arrival photo",
            "Price list with WhatsApp order",
            "Monthly ration package",
            "Customer feedback",
            "Delivery service announcement",
        ],
        "hashtags": ["#PeshawarGrocery", "#HomeDelivery", "#FreshStock", "#PeshawarMart"],
        "ad_split": "80% Facebook (radius 3-5 km), 20% Google local",
    },
}

DEFAULT_NICHE = "Local Business"
DEFAULT_DATA = {
    "audience": "Local customers 18-50 in your city",
    "platforms": ["Facebook", "Google Business Profile", "WhatsApp"],
    "hook": "Special launch offer + free consultation",
    "content": [
        "Business introduction video",
        "Product / service showcase",
        "Customer testimonial",
        "Offer post with WhatsApp button",
        "Behind the scenes",
        "Educational tip related to your business",
    ],
    "hashtags": ["#LocalBusiness", "#Peshawar", "#SupportLocal", "#KhyberPakhtunkhwa"],
    "ad_split": "70% Facebook, 30% Google local ads",
}


# ---------------------------------------------------------------------------
# Logic
# ---------------------------------------------------------------------------
def detect_niche(business_name):
    """Match the business name against niche keywords. Returns (niche, data)."""
    name = business_name.lower()
    best, best_hits = None, 0
    for niche, data in NICHES.items():
        hits = sum(1 for kw in data["keywords"] if kw in name)
        if hits > best_hits:
            best, best_hits = niche, hits
    if best:
        return best, NICHES[best]
    return DEFAULT_NICHE, DEFAULT_DATA


def recommend_package(budget):
    """Pick the best package that fits the client's monthly budget."""
    chosen = "Starter"
    for pkg, info in PACKAGES.items():
        if budget >= info["price"]:
            chosen = pkg
    return chosen


def build_content_plan(data):
    """30-day plan: 4 weeks of posts cycling through content ideas."""
    ideas = data["content"]
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
    plan = []
    n = 0
    for week in range(1, 5):
        for d in days[: 5 if week < 4 else 4]:
            plan.append((f"Week {week} - {d}", ideas[n % len(ideas)]))
            n += 1
    return plan


def build_pitch(business, city, niche, data, package, lang):
    price = f"Rs {PACKAGES[package]['price']:,}"
    platforms = ", ".join(data["platforms"])
    if lang == "English":
        return (
            f"Hello {business} team!\n\n"
            f"This is Aziz from {AGENCY}, {city}. "
            f"We help {niche.lower()} businesses get more customers through {platforms}.\n\n"
            f"Offer for you: {data['hook']}.\n"
            f"Our {package} package is {price}/month and we focus on visible growth in 30 days.\n\n"
            f"Can we do a quick 5-minute call or WhatsApp chat?"
        )
    return (
        f"Assalam o Alaikum {business} Owner!\n\n"
        f"Main Aziz, {AGENCY} {city} se bol raha hun. "
        f"Hum {niche.lower()} businesses ko {platforms} ke zariye zyada customers dilwate hain.\n\n"
        f"Aap ke liye offer: {data['hook']}.\n"
        f"Hamara {package} package {price}/month hai aur hum 30 din mein growth dikhate hain.\n\n"
        f"Kya hum 5 minute ke liye baat kar sakte hain?"
    )


def build_report_text(business, city, niche, data, package, plan, pitch):
    lines = [
        f"{AGENCY} - Marketing Report",
        f"Business: {business}",
        f"City: {city}",
        f"Date: {date.today().isoformat()}",
        "",
        f"Niche: {niche}",
        f"Audience: {data['audience']}",
        f"Platforms: {', '.join(data['platforms'])}",
        f"Ad budget split: {data['ad_split']}",
        f"Hashtags: {' '.join(data['hashtags'])}",
        f"Recommended package: {package} (Rs {PACKAGES[package]['price']:,}/month)",
        "",
        "30-Day Content Plan",
        "-------------------",
    ]
    lines += [f"{day}: {idea}" for day, idea in plan]
    lines += ["", "WhatsApp Pitch", "--------------", pitch, "", f"Contact: 0{MY_WA[2:]}"]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    if os.path.exists(LOGO_FILE):
        st.image(LOGO_FILE, width=220)
    st.title(AGENCY)
    st.info(f"📞 0{MY_WA[2:]}\n\n📍 Peshawar\n\n☁️ Cloud LIVE")
    st.success("Status LIVE")
    st.subheader("Packages")
    for pkg, info in PACKAGES.items():
        with st.expander(f"{pkg} - Rs {info['price']:,}"):
            for item in info["items"]:
                st.write(f"• {item}")

# ---------------------------------------------------------------------------
# Main page
# ---------------------------------------------------------------------------
st.title("🚀 Aziz AI Marketing Cloud Agent")
st.caption("Business ka naam likho aur ek minute mein research, content plan aur WhatsApp pitch lo.")
st.divider()

col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    business = st.text_input("Business Name:", placeholder="Peshawar Clothes Shop")
with col2:
    city = st.text_input("City:", value="Peshawar")
with col3:
    budget = st.number_input("Client monthly budget (Rs):", min_value=0, value=15000, step=5000)

lang = st.radio("Pitch language:", ["Roman Urdu", "English"], horizontal=True)

if st.button("Generate PRO Report", type="primary"):
    if not business.strip():
        st.error("Business Name likho!")
    else:
        with st.spinner("Research..."):
            time.sleep(1)
            niche, data = detect_niche(business)
            package = recommend_package(budget)
            plan = build_content_plan(data)
            pitch = build_pitch(business.strip(), city.strip() or "Peshawar", niche, data, package, lang)
            report = build_report_text(business.strip(), city.strip() or "Peshawar",
                                       niche, data, package, plan, pitch)
        # Keep the result so it survives reruns (e.g. clicking Download).
        st.session_state["result"] = {
            "business": business.strip(), "niche": niche, "data": data,
            "package": package, "plan": plan, "pitch": pitch, "report": report,
            "matched": niche != DEFAULT_NICHE,
        }

result = st.session_state.get("result")
if result:
    st.success(f"Report Ready for {result['business']}")
    if not result["matched"]:
        st.warning("Niche pehchana nahi gaya, general plan diya gaya hai. "
                   "Business name mein niche ka lafz likho (jaise 'clothes', 'salon', 'clinic').")

    data = result["data"]
    tab1, tab2, tab3 = st.tabs(["Research", "30-Day Content Plan", "WhatsApp Pitch"])

    with tab1:
        c1, c2 = st.columns(2)
        with c1:
            st.metric("Niche", result["niche"])
            st.write(f"**Audience:** {data['audience']}")
            st.write(f"**Platforms:** {', '.join(data['platforms'])}")
            st.write(f"**Offer idea:** {data['hook']}")
        with c2:
            pkg = result["package"]
            st.metric("Recommended package", f"{pkg} - Rs {PACKAGES[pkg]['price']:,}/month")
            st.write(f"**Ad budget split:** {data['ad_split']}")
            st.write(f"**Hashtags:** {' '.join(data['hashtags'])}")

    with tab2:
        st.table({"Day": [d for d, _ in result["plan"]], "Content": [c for _, c in result["plan"]]})

    with tab3:
        st.code(result["pitch"], language=None)
        wa_link = f"https://wa.me/{MY_WA}?text={urllib.parse.quote(result['pitch'])}"
        st.link_button("WhatsApp par bhejo", wa_link)
        st.caption("Client ka number pata ho to wa.me/<number>?text=... link use karo, "
                   "yeh button aap ke apne number par message kholta hai.")

    st.download_button(
        "Download full report (.txt)",
        data=result["report"],
        file_name=f"{result['business'].replace(' ', '_')}_report.txt",
        mime="text/plain",
    )

st.divider()
st.caption(f"Powered by {AGENCY} | 0{MY_WA[2:]} | Peshawar")
