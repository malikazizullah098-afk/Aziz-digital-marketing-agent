"""Aziz AI Marketing Cloud Agent.

A Streamlit tool that turns a business name into a niche research summary,
a 30-day content plan, a package recommendation and a ready-to-send
WhatsApp pitch.
"""
from __future__ import annotations

import csv
import io
import os
import re
import time
import urllib.parse
from dataclasses import dataclass
from datetime import datetime

import streamlit as st

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
AGENCY = "Aziz Digital Agency"
MY_WA = "923715221906"  # agency WhatsApp number (international format, no +)
DEFAULT_CITY = "Peshawar"
LOGO_FILE = "WhatsApp Image 2026-10-28 at 8.45.36 PM.jpeg"
MAX_HISTORY = 10

st.set_page_config(page_title="Aziz Agency", page_icon="🚀", layout="wide")


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Package:
    name: str
    price: int
    items: tuple[str, ...]


@dataclass(frozen=True)
class Niche:
    name: str
    keywords: tuple[str, ...]
    audience: str
    platforms: tuple[str, ...]
    hook: str
    content: tuple[str, ...]
    hashtags: tuple[str, ...]
    ad_split: str


@dataclass
class Report:
    business: str
    city: str
    niche: Niche
    matched: bool
    package: Package
    plan: list[tuple[str, str]]
    pitch: str
    client_wa: str | None
    created: str

    @property
    def label(self) -> str:
        return f"{self.created} - {self.business}"


PACKAGES: tuple[Package, ...] = (
    Package("Starter", 15000, ("1 platform manage", "12 posts / month", "Basic page setup", "Monthly report")),
    Package("Growth", 25000, ("2 platforms manage", "20 posts + 4 reels", "Ads setup + management", "Weekly report")),
    Package("Pro", 40000, ("3 platforms manage", "30 posts + 8 reels", "Ads + WhatsApp lead funnel", "Weekly report + call")),
)


def _niche(name, keywords, audience, platforms, hook, content, hashtags, ad_split) -> Niche:
    return Niche(name, tuple(keywords), audience, tuple(platforms), hook,
                 tuple(content), tuple(hashtags), ad_split)


NICHES: tuple[Niche, ...] = (
    _niche(
        "Food / Restaurant",
        ["food", "shawarma", "restaurant", "burger", "pizza", "cafe", "bakery", "tikka",
         "karahi", "chai", "biryani", "fast food", "dhaba", "khana"],
        "Foodies, families, students and office workers (18-40)",
        ["Facebook", "TikTok", "Instagram Reels"],
        "Free delivery ya combo deal pehle 50 customers ke liye",
        ["Food making reel (close-up, sizzling shots)", "Menu + price post with WhatsApp order button",
         "Customer review / reaction video", "Behind the kitchen story",
         "Weekend combo offer post", "Poll: 'Aaj kya khaoge?'"],
        ["#PeshawarFood", "#FoodiesPeshawar", "#PeshawarEats", "#KhyberPakhtunkhwa"],
        "70% Facebook/Instagram ads (radius 5-8 km), 30% TikTok",
    ),
    _niche(
        "Fashion / Boutique",
        ["fashion", "boutique", "cloth", "clothes", "garment", "suit", "dress", "lawn",
         "kapra", "kapray", "shoes", "jewellery", "jewelry", "abaya"],
        "Women and girls 18-40, wedding shoppers, Instagram users",
        ["Instagram", "Facebook", "WhatsApp Catalog"],
        "New collection launch + free home delivery",
        ["New arrival carousel (3-5 photos)", "Styling reel: 1 suit, 3 looks",
         "Customer try-on / unboxing video", "Price + size guide post",
         "Eid / wedding season collection", "Story: 'DM for price' with WhatsApp link"],
        ["#PeshawarFashion", "#PeshawariBoutique", "#LawnCollection", "#PakistaniFashion"],
        "60% Instagram ads, 30% Facebook, 10% retargeting",
    ),
    _niche(
        "Beauty / Salon",
        ["salon", "beauty", "parlour", "parlor", "makeup", "bridal", "hair", "barber",
         "spa", "skin", "mehndi"],
        "Women 18-45, brides and their families; men for barber services",
        ["Instagram", "Facebook", "WhatsApp"],
        "Free consultation + bridal package discount",
        ["Before / after transformation reel", "Bridal makeup showcase", "Service price list post",
         "Tips: skin / hair care short video", "Client testimonial",
         "Booking announcement with WhatsApp link"],
        ["#PeshawarSalon", "#BridalMakeup", "#PeshawarBeauty", "#MakeupArtist"],
        "60% Instagram, 40% Facebook (local area + lookalike)",
    ),
    _niche(
        "Clinic / Medical",
        ["clinic", "doctor", "dental", "dentist", "hospital", "medical", "pharmacy", "lab",
         "diagnostic", "physio"],
        "Families, parents, elderly and patients searching locally",
        ["Facebook", "Google Business Profile", "WhatsApp"],
        "Free first consultation / health camp announcement",
        ["Health tip of the week (short video)", "Doctor introduction post",
         "Patient awareness infographic", "Clinic timings + location post",
         "Common myths vs facts", "Appointment booking via WhatsApp"],
        ["#PeshawarDoctor", "#HealthTips", "#PeshawarClinic", "#KPKHealth"],
        "50% Google local ads, 50% Facebook (radius 10 km)",
    ),
    _niche(
        "Education / Academy",
        ["academy", "school", "tuition", "coaching", "college", "institute", "course",
         "training", "english", "quran", "madrassa", "university"],
        "Parents (28-50) and students (14-25)",
        ["Facebook", "YouTube", "WhatsApp Groups"],
        "Free demo class + early admission discount",
        ["Teacher introduction video", "Student results / success story",
         "Free tips video (exam preparation)", "Admission open post with fee structure",
         "Classroom tour reel", "Parent testimonial"],
        ["#PeshawarAcademy", "#AdmissionOpen", "#PeshawarEducation", "#StudyTips"],
        "70% Facebook lead ads, 30% YouTube",
    ),
    _niche(
        "Real Estate",
        ["property", "real estate", "estate", "plot", "house", "flat", "apartment", "builder",
         "construction", "society", "makan", "zameen"],
        "Investors, overseas Pakistanis, families 28-55",
        ["Facebook", "YouTube", "WhatsApp"],
        "Site visit booking + limited-time payment plan",
        ["Property walkthrough video", "Drone / location shots", "Price + payment plan post",
         "Area development update", "Client handover story", "Investment tips short video"],
        ["#PeshawarProperty", "#RealEstatePakistan", "#PlotsForSale", "#InvestInPeshawar"],
        "80% Facebook lead ads, 20% YouTube",
    ),
    _niche(
        "Electronics / Mobile",
        ["mobile", "phone", "electronic", "laptop", "computer", "gadget", "accessories",
         "camera", "repair", "tech"],
        "Students, young professionals, gamers (16-35)",
        ["Facebook", "TikTok", "Instagram"],
        "Warranty + price match guarantee",
        ["Product unboxing reel", "Price list / new stock post", "Comparison: product A vs B",
         "Customer pickup photo", "Tech tip short video", "Flash sale announcement"],
        ["#PeshawarMobile", "#TechPakistan", "#MobileShop", "#NewArrival"],
        "60% Facebook, 40% TikTok",
    ),
    _niche(
        "Gym / Fitness",
        ["gym", "fitness", "trainer", "workout", "bodybuilding", "yoga", "crossfit"],
        "Men and women 18-40 who want fitness results",
        ["Instagram", "TikTok", "Facebook"],
        "Free 3-day trial + joining fee waiver",
        ["Transformation before / after", "Workout of the day reel", "Trainer introduction",
         "Diet tip short video", "Member milestone post", "Membership offer post"],
        ["#PeshawarGym", "#FitnessPakistan", "#GymMotivation", "#Transformation"],
        "60% Instagram, 40% TikTok",
    ),
    _niche(
        "Auto / Workshop",
        ["car", "auto", "workshop", "garage", "tyre", "tire", "bike", "motorcycle",
         "showroom", "mechanic", "detailing"],
        "Car and bike owners, buyers 22-50",
        ["Facebook", "YouTube", "Google Business Profile"],
        "Free inspection + service discount coupon",
        ["Car detailing before / after", "Service price list", "Customer car delivery photo",
         "Maintenance tip short video", "New stock / vehicle showcase", "Google review request post"],
        ["#PeshawarCars", "#CarDetailing", "#AutoWorkshop", "#PakistanCars"],
        "50% Google local ads, 50% Facebook",
    ),
    _niche(
        "Wedding / Events",
        ["wedding", "event", "marquee", "hall", "catering", "decor", "photography",
         "photographer", "shadi", "barat"],
        "Families planning weddings, brides and grooms (22-40)",
        ["Instagram", "Facebook", "YouTube"],
        "Early booking discount + free consultation",
        ["Event highlight reel", "Decor / setup showcase", "Package price post",
         "Client testimonial video", "Behind the scenes", "Booking dates available post"],
        ["#PeshawarWedding", "#WeddingPakistan", "#EventPlanner", "#ShadiSeason"],
        "60% Instagram, 40% Facebook",
    ),
    _niche(
        "Grocery / General Store",
        ["grocery", "store", "mart", "supermarket", "kiryana", "kariyana", "dairy", "milk",
         "fruit", "sabzi"],
        "Households and nearby neighbourhoods",
        ["Facebook", "WhatsApp Catalog", "Google Business Profile"],
        "Free home delivery above a minimum order",
        ["Weekly offers post", "Fresh stock arrival photo", "Price list with WhatsApp order",
         "Monthly ration package", "Customer feedback", "Delivery service announcement"],
        ["#PeshawarGrocery", "#HomeDelivery", "#FreshStock", "#PeshawarMart"],
        "80% Facebook (radius 3-5 km), 20% Google local",
    ),
)

GENERAL_NICHE = _niche(
    "Local Business",
    [],
    "Local customers 18-50 in your city",
    ["Facebook", "Google Business Profile", "WhatsApp"],
    "Special launch offer + free consultation",
    ["Business introduction video", "Product / service showcase", "Customer testimonial",
     "Offer post with WhatsApp button", "Behind the scenes",
     "Educational tip related to your business"],
    ["#LocalBusiness", "#Peshawar", "#SupportLocal", "#KhyberPakhtunkhwa"],
    "70% Facebook, 30% Google local ads",
)


# ---------------------------------------------------------------------------
# Business logic (pure functions, no Streamlit calls)
# ---------------------------------------------------------------------------
def detect_niche(business_name: str) -> tuple[Niche, bool]:
    """Return the best matching niche and whether a real match was found."""
    name = business_name.lower()
    best, best_hits = GENERAL_NICHE, 0
    for niche in NICHES:
        hits = sum(1 for kw in niche.keywords if kw in name)
        if hits > best_hits:
            best, best_hits = niche, hits
    return best, best_hits > 0


def recommend_package(budget: int) -> Package:
    """Highest package the client's monthly budget can afford (Starter minimum)."""
    chosen = PACKAGES[0]
    for pkg in PACKAGES:
        if budget >= pkg.price:
            chosen = pkg
    return chosen


def build_content_plan(niche: Niche) -> list[tuple[str, str]]:
    """Four weeks of posts (Mon-Fri, last week Mon-Thu) cycling through ideas."""
    days = ["Mon", "Tue", "Wed", "Thu", "Fri"]
    plan: list[tuple[str, str]] = []
    n = 0
    for week in range(1, 5):
        for day in days[: 4 if week == 4 else 5]:
            plan.append((f"Week {week} - {day}", niche.content[n % len(niche.content)]))
            n += 1
    return plan


def normalize_pk_number(raw: str) -> str | None:
    """Convert a Pakistani mobile number to 92XXXXXXXXXX, or None if invalid."""
    digits = re.sub(r"\D", "", raw or "")
    if digits.startswith("0092"):
        digits = digits[2:]
    if digits.startswith("0"):
        digits = "92" + digits[1:]
    elif digits.startswith("3") and len(digits) == 10:
        digits = "92" + digits
    return digits if re.fullmatch(r"923\d{9}", digits) else None


def build_pitch(business: str, city: str, niche: Niche, package: Package, lang: str) -> str:
    price = f"Rs {package.price:,}"
    platforms = ", ".join(niche.platforms)
    if lang == "English":
        return (
            f"Hello {business} team!\n\n"
            f"This is Aziz from {AGENCY}, {city}. "
            f"We help {niche.name.lower()} businesses get more customers through {platforms}.\n\n"
            f"Offer for you: {niche.hook}.\n"
            f"Our {package.name} package is {price}/month and we focus on visible growth in 30 days.\n\n"
            f"Can we do a quick 5-minute call or WhatsApp chat?"
        )
    return (
        f"Assalam o Alaikum {business} Owner!\n\n"
        f"Main Aziz, {AGENCY} {city} se bol raha hun. "
        f"Hum {niche.name.lower()} businesses ko {platforms} ke zariye zyada customers dilwate hain.\n\n"
        f"Aap ke liye offer: {niche.hook}.\n"
        f"Hamara {package.name} package {price}/month hai aur hum 30 din mein growth dikhate hain.\n\n"
        f"Kya hum 5 minute ke liye baat kar sakte hain?"
    )


def build_whatsapp_link(report: Report) -> str:
    """Link to the client's chat when their number is known, otherwise to the agency number."""
    target = report.client_wa or MY_WA
    return f"https://wa.me/{target}?text={urllib.parse.quote(report.pitch)}"


def report_to_text(r: Report) -> str:
    lines = [
        f"{AGENCY} - Marketing Report",
        f"Business: {r.business}",
        f"City: {r.city}",
        f"Generated: {r.created}",
        "",
        f"Niche: {r.niche.name}",
        f"Audience: {r.niche.audience}",
        f"Platforms: {', '.join(r.niche.platforms)}",
        f"Ad budget split: {r.niche.ad_split}",
        f"Hashtags: {' '.join(r.niche.hashtags)}",
        f"Recommended package: {r.package.name} (Rs {r.package.price:,}/month)",
        "",
        "30-Day Content Plan",
        "-------------------",
        *[f"{day}: {idea}" for day, idea in r.plan],
        "",
        "WhatsApp Pitch",
        "--------------",
        r.pitch,
        "",
        f"Contact: 0{MY_WA[2:]}",
    ]
    return "\n".join(lines)


def plan_to_csv(plan: list[tuple[str, str]]) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["Day", "Content"])
    writer.writerows(plan)
    return buf.getvalue()


def create_report(business: str, city: str, budget: int, lang: str, client_raw: str) -> Report:
    niche, matched = detect_niche(business)
    package = recommend_package(budget)
    return Report(
        business=business,
        city=city,
        niche=niche,
        matched=matched,
        package=package,
        plan=build_content_plan(niche),
        pitch=build_pitch(business, city, niche, package, lang),
        client_wa=normalize_pk_number(client_raw) if client_raw.strip() else None,
        created=datetime.now().strftime("%d %b %H:%M:%S"),
    )


# ---------------------------------------------------------------------------
# 3D hero banner (Three.js). Static markup only: no user input is injected.
# ---------------------------------------------------------------------------
HERO_HTML = """
<style>
  html,body{margin:0;height:100%;background:transparent;font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
  #wrap{position:relative;height:100%;border-radius:18px;overflow:hidden;
        background:radial-gradient(120% 140% at 80% 0%,#2b1b6b 0%,#14103a 55%,#0b0a22 100%)}
  canvas{position:absolute;inset:0;width:100%;height:100%;display:block}
  .txt{position:absolute;left:32px;top:50%;transform:translateY(-50%);color:#fff;max-width:56%;z-index:2}
  .txt h1{margin:0 0 8px;font-size:clamp(20px,3.2vw,34px);line-height:1.15;letter-spacing:-.5px}
  .txt p{margin:0;color:#c9c6ee;font-size:clamp(12px,1.5vw,15px)}
  .pill{display:inline-block;margin-top:14px;padding:5px 12px;border-radius:999px;font-size:12px;
        background:rgba(120,255,190,.14);color:#7dffbf;border:1px solid rgba(125,255,191,.35)}
  @media(max-width:600px){.txt{max-width:88%;left:18px}}
</style>
<div id="wrap">
  <canvas id="c"></canvas>
  <div class="txt">
    <h1>🚀 Aziz AI Marketing Cloud Agent</h1>
    <p>Research, 30-day content plan aur WhatsApp pitch, ek minute mein.</p>
    <span class="pill">● Cloud LIVE</span>
  </div>
</div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
<script>
(function () {
  if (typeof THREE === 'undefined') { return; }           // CDN blocked: gradient banner only
  var wrap = document.getElementById('wrap');
  var canvas = document.getElementById('c');
  var renderer;
  try { renderer = new THREE.WebGLRenderer({ canvas: canvas, alpha: true, antialias: true }); }
  catch (e) { return; }                                   // no WebGL: gradient banner only
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));

  var scene = new THREE.Scene();
  var camera = new THREE.PerspectiveCamera(45, 1, 0.1, 100);
  camera.position.z = 7;

  scene.add(new THREE.AmbientLight(0x8877ff, 0.6));
  var key = new THREE.PointLight(0x66ffcc, 1.2, 40); key.position.set(5, 4, 6); scene.add(key);
  var rim = new THREE.PointLight(0xff66cc, 1.0, 40); rim.position.set(-5, -3, 4); scene.add(rim);

  var knot = new THREE.Mesh(
    new THREE.TorusKnotGeometry(1.15, 0.38, 180, 24),
    new THREE.MeshStandardMaterial({ color: 0x7c5cff, metalness: 0.6, roughness: 0.25 })
  );
  var wire = new THREE.Mesh(
    new THREE.TorusKnotGeometry(1.5, 0.05, 120, 8),
    new THREE.MeshBasicMaterial({ color: 0x66ffcc, wireframe: true, transparent: true, opacity: 0.35 })
  );
  var group = new THREE.Group(); group.add(knot); group.add(wire); scene.add(group);

  var COUNT = 260, pos = new Float32Array(COUNT * 3);
  for (var i = 0; i < COUNT * 3; i++) { pos[i] = (Math.random() - 0.5) * 16; }
  var geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  var stars = new THREE.Points(geo, new THREE.PointsMaterial({ color: 0xffffff, size: 0.045, transparent: true, opacity: 0.8 }));
  scene.add(stars);

  var mx = 0, my = 0;
  window.addEventListener('mousemove', function (e) {
    mx = (e.clientX / window.innerWidth - 0.5) * 2;
    my = (e.clientY / window.innerHeight - 0.5) * 2;
  });

  function resize() {
    var w = wrap.clientWidth, h = wrap.clientHeight;
    renderer.setSize(w, h, false);
    camera.aspect = w / h; camera.updateProjectionMatrix();
    group.position.x = w > 600 ? 2.6 : 0;                 // knot on the right for wide screens
    group.scale.setScalar(w > 600 ? 1 : 0.8);
  }
  window.addEventListener('resize', resize); resize();

  var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var t0 = performance.now();
  function frame(now) {
    var t = (now - t0) / 1000;
    knot.rotation.x = t * 0.45; knot.rotation.y = t * 0.6;
    wire.rotation.x = -t * 0.25; wire.rotation.z = t * 0.3;
    group.position.y = Math.sin(t * 1.1) * 0.12;
    stars.rotation.y = t * 0.03;
    camera.position.x += (mx * 0.6 - camera.position.x) * 0.04;
    camera.position.y += (-my * 0.4 - camera.position.y) * 0.04;
    camera.lookAt(0, 0, 0);
    renderer.render(scene, camera);
    if (!reduce) { requestAnimationFrame(frame); }
  }
  requestAnimationFrame(frame);
})();
</script>
"""

CUSTOM_CSS = """
<style>
  div[data-testid="stMetric"]{background:rgba(124,92,255,.08);border:1px solid rgba(124,92,255,.25);
      padding:12px 16px;border-radius:12px}
  .stButton>button[kind="primary"]{border-radius:10px;font-weight:600}
</style>
"""


# ---------------------------------------------------------------------------
# UI helpers
# ---------------------------------------------------------------------------
def render_sidebar_header() -> None:
    with st.sidebar:
        if os.path.exists(LOGO_FILE):
            st.image(LOGO_FILE, width=220)
        st.title(AGENCY)
        st.info(f"📞 0{MY_WA[2:]}\n\n📍 {DEFAULT_CITY}\n\n☁️ Cloud LIVE")
        st.subheader("Packages")
        for pkg in PACKAGES:
            with st.expander(f"{pkg.name} - Rs {pkg.price:,}"):
                for item in pkg.items:
                    st.write(f"• {item}")


def render_hero() -> None:
    """Show the 3D banner. st.iframe on current Streamlit, components.html on older versions."""
    if hasattr(st, "iframe"):
        st.iframe(HERO_HTML, height=250)
    else:
        import streamlit.components.v1 as components  # older Streamlit only

        components.html(HERO_HTML, height=250)


def _load_history_pick() -> None:
    pick = st.session_state.get("history_pick")
    for report in st.session_state.get("history", []):
        if report.label == pick:
            st.session_state["result"] = report
            break


def render_sidebar_history() -> None:
    history: list[Report] = st.session_state.get("history", [])
    if not history:
        return
    with st.sidebar:
        st.subheader("Pichli reports")
        st.selectbox(
            "Reload a report",
            [r.label for r in history],
            index=None,
            placeholder="Select a report",
            key="history_pick",
            on_change=_load_history_pick,
            label_visibility="collapsed",
        )


def render_report(r: Report) -> None:
    st.success(f"Report Ready for {r.business}")
    if not r.matched:
        st.warning("Niche pehchana nahi gaya, general plan diya gaya hai. Business name mein niche ka "
                   "lafz likho (jaise 'clothes', 'salon', 'clinic').")

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Niche", r.niche.name)
    k2.metric("Package", f"{r.package.name}")
    k3.metric("Price / month", f"Rs {r.package.price:,}")
    k4.metric("Posts planned", len(r.plan))

    tab_research, tab_plan, tab_pitch = st.tabs(["Research", "30-Day Content Plan", "WhatsApp Pitch"])

    with tab_research:
        left, right = st.columns(2)
        with left:
            st.write(f"**Audience:** {r.niche.audience}")
            st.write(f"**Platforms:** {', '.join(r.niche.platforms)}")
            st.write(f"**Offer idea:** {r.niche.hook}")
        with right:
            st.write(f"**Ad budget split:** {r.niche.ad_split}")
            st.write(f"**Hashtags:** {' '.join(r.niche.hashtags)}")
            st.write("**Package includes:** " + ", ".join(r.package.items))

    with tab_plan:
        st.table({"Day": [d for d, _ in r.plan], "Content": [c for _, c in r.plan]})
        st.download_button("Download plan (.csv)", plan_to_csv(r.plan),
                           file_name=f"{_slug(r.business)}_content_plan.csv", mime="text/csv")

    with tab_pitch:
        st.code(r.pitch, language=None)
        if r.client_wa:
            st.link_button("Client ko WhatsApp karo", build_whatsapp_link(r), type="primary")
        else:
            st.link_button("WhatsApp par kholo (aap ke number par)", build_whatsapp_link(r))
            st.caption("Client ka WhatsApp number upar daalo to yeh button seedha client ki chat kholega.")

    st.download_button("Download full report (.txt)", report_to_text(r),
                       file_name=f"{_slug(r.business)}_report.txt", mime="text/plain")


def _slug(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_") or "report"


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------
def main() -> None:
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
    render_sidebar_header()
    render_hero()

    c1, c2, c3 = st.columns([2, 1, 1])
    business = c1.text_input("Business Name:", placeholder="Peshawar Clothes Shop", max_chars=60)
    city = c2.text_input("City:", value=DEFAULT_CITY, max_chars=40)
    budget = c3.number_input("Client monthly budget (Rs):", min_value=0, value=15000, step=5000)

    c4, c5 = st.columns([1, 1])
    client_raw = c4.text_input("Client WhatsApp number (optional):", placeholder="0333 1234567")
    lang = c5.radio("Pitch language:", ["Roman Urdu", "English"], horizontal=True)

    if budget < PACKAGES[0].price:
        st.caption(f"Note: sab se chota package Rs {PACKAGES[0].price:,} ka hai.")

    if st.button("Generate PRO Report", type="primary"):
        name = business.strip()
        if not name:
            st.error("Business Name likho!")
        else:
            if client_raw.strip() and not normalize_pk_number(client_raw):
                st.warning("Client number sahi nahi lagta (format: 0333 1234567). "
                           "Isay chhor kar report banai gayi hai.")
            with st.spinner("Research..."):
                time.sleep(0.8)
                report = create_report(name, city.strip() or DEFAULT_CITY, int(budget), lang, client_raw)
            st.session_state["result"] = report
            history = st.session_state.setdefault("history", [])
            history.insert(0, report)
            del history[MAX_HISTORY:]
            st.balloons()

    result = st.session_state.get("result")
    if result:
        render_report(result)

    render_sidebar_history()
    st.divider()
    st.caption(f"Powered by {AGENCY} | 0{MY_WA[2:]} | {DEFAULT_CITY}")


main()
