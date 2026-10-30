"""Aziz AI Marketing Cloud Agent.

A Streamlit tool that turns a business name into a niche research summary,
a 30-day content plan, a package recommendation and a ready-to-send
WhatsApp pitch.
"""
from __future__ import annotations

import csv
import hmac
import io
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import date, datetime
from html import escape

import streamlit as st

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
AGENCY = "Aziz Digital Agency"
MY_WA = "923715221906"  # agency WhatsApp number (international format, no +)
DEFAULT_CITY = "Peshawar"
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
# AI agent. Gemini (free key) or Claude (paid key). Keys and password live in Streamlit Secrets, never in GitHub.
# ---------------------------------------------------------------------------
AI_MODEL_DEFAULT = "claude-sonnet-5-5"      # Claude model
GEMINI_MODEL_DEFAULT = "gemini-flash-latest"  # Gemini alias; auto-discovers a flash model if missing
AI_MAX_TOKENS = 1400
GEMINI_MAX_TOKENS = 3000  # Gemini counts its internal thinking inside this budget
GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta"
AI_DAILY_LIMIT_DEFAULT = 30  # total AI calls per day for the whole app (cost cap)

AI_SYSTEM = (
    "You are the marketing brain of Aziz Digital Agency, a digital marketing agency in Peshawar, Pakistan. "
    "You help the agency owner (Aziz) win and serve local clients. "
    "Always answer in simple Roman Urdu (Urdu written in English letters) with English marketing terms where natural. "
    "Be practical and specific to Pakistani local businesses: realistic budgets in Rs, WhatsApp-first sales, "
    "Facebook, Instagram, TikTok and Google Business Profile. Never promise guaranteed results. "
    "Keep answers well organised with short headings and bullet points."
)


def get_secret(name: str, default=None):
    try:
        return st.secrets.get(name, default)
    except Exception:  # no secrets file configured
        return default


@st.cache_resource
def _usage() -> dict:
    return {"day": date.today().isoformat(), "n": 0}


def ai_calls_left() -> int:
    u = _usage()
    today = date.today().isoformat()
    if u["day"] != today:
        u["day"], u["n"] = today, 0
    return max(0, int(get_secret("AI_DAILY_LIMIT", AI_DAILY_LIMIT_DEFAULT)) - u["n"])


def ai_unlocked() -> bool:
    """True when no password is configured, or the visitor entered the right one."""
    pw = get_secret("APP_PASSWORD")
    return not pw or st.session_state.get("ai_ok", False)


def _gemini_request(url: str, key: str, body: dict | None = None) -> dict:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method="POST" if body is not None else "GET",
                                 headers={"x-goog-api-key": key, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode())


def _gemini_find_model(key: str) -> str | None:
    """Ask Google which models this key can use and pick a normal text 'flash' model."""
    models = _gemini_request(f"{GEMINI_BASE}/models?pageSize=200", key).get("models", [])
    bad = ("image", "tts", "live", "embed", "audio", "robotics", "computer", "thinking", "vision", "aqa")
    names = [m["name"].split("/")[-1] for m in models
             if "generateContent" in m.get("supportedGenerationMethods", [])]
    flash = [n for n in names if "flash" in n and not any(b in n for b in bad)]
    stable = [n for n in flash if "preview" not in n and "exp" not in n and "lite" not in n]
    for group in (stable, flash):
        if group:
            return sorted(group)[-1]
    return None


def call_gemini(prompt: str, history: list[tuple[str, str]] | None, key: str) -> str:
    contents = []
    for q, a in (history or [])[-4:]:
        contents += [{"role": "user", "parts": [{"text": q}]}, {"role": "model", "parts": [{"text": a}]}]
    contents.append({"role": "user", "parts": [{"text": prompt}]})
    body = {"systemInstruction": {"parts": [{"text": AI_SYSTEM}]}, "contents": contents,
            "generationConfig": {"maxOutputTokens": GEMINI_MAX_TOKENS}}
    model = str(get_secret("GEMINI_MODEL", GEMINI_MODEL_DEFAULT))
    try:
        data = _gemini_request(f"{GEMINI_BASE}/models/{model}:generateContent", key, body)
    except urllib.error.HTTPError as err:
        if err.code != 404:
            raise
        alt = _gemini_find_model(key)  # configured model name does not exist: find one that does
        if not alt:
            raise
        data = _gemini_request(f"{GEMINI_BASE}/models/{alt}:generateContent", key, body)
    parts = (data.get("candidates") or [{}])[0].get("content", {}).get("parts", [])
    return "".join(p.get("text", "") for p in parts).strip()


def call_claude_api(prompt: str, history: list[tuple[str, str]] | None, key: str) -> str:
    import anthropic

    messages = []
    for q, a in (history or [])[-4:]:
        messages += [{"role": "user", "content": q}, {"role": "assistant", "content": a}]
    messages.append({"role": "user", "content": prompt})
    resp = anthropic.Anthropic(api_key=key).messages.create(
        model=str(get_secret("AI_MODEL", AI_MODEL_DEFAULT)), max_tokens=AI_MAX_TOKENS,
        system=AI_SYSTEM, messages=messages)
    return "".join(b.text for b in resp.content if getattr(b, "type", "") == "text").strip()


def ai_provider() -> str | None:
    if get_secret("GEMINI_API_KEY"):
        return "gemini"
    if get_secret("ANTHROPIC_API_KEY"):
        return "claude"
    return None


def call_ai(prompt: str, history: list[tuple[str, str]] | None = None) -> str:
    """Send one request to the configured AI. Returns text, or a friendly Roman Urdu error message."""
    provider = ai_provider()
    if not provider:
        return "AI key set nahi hai. Streamlit Secrets mein GEMINI_API_KEY daalein."
    if ai_calls_left() <= 0:
        return "Aaj ki AI limit poori ho gayi. Kal dobara try karein."
    try:
        if provider == "gemini":
            text = call_gemini(prompt, history, str(get_secret("GEMINI_API_KEY")))
        else:
            text = call_claude_api(prompt, history, str(get_secret("ANTHROPIC_API_KEY")))
        _usage()["n"] += 1
        return text or "AI ne khali jawab diya (shayad filter ho gaya), sawal badal kar dobara try karein."
    except urllib.error.HTTPError as exc:
        if exc.code in (400, 401, 403):
            return "API key galat ya band hai. Secrets mein key dobara check karein."
        if exc.code == 429:
            return "AI ki free limit abhi poori hai (rate limit). Thori der baad try karein."
        return f"AI se jawab nahi mila (HTTP {exc.code}). Thori der baad try karein."
    except ImportError:
        return "anthropic package install nahi hai. requirements.txt mein 'anthropic' likhein."
    except Exception as exc:  # network, billing, rate limit ...
        name = type(exc).__name__
        if "Authentication" in name:
            return "API key galat hai. Secrets mein key dobara check karein."
        if "RateLimit" in name:
            return "AI abhi masroof hai (rate limit). Thori der baad try karein."
        return f"AI se jawab nahi mila ({name}). Internet ya key check karein."


def strategy_prompt(r: Report) -> str:
    return (
        f"Business: {r.business} ({r.city}). Niche: {r.niche.name}. "
        f"Target audience: {r.niche.audience}. Platforms: {', '.join(r.niche.platforms)}. "
        f"Monthly package: {r.package.name} (Rs {r.package.price:,}).\n\n"
        "Is business ke liye yeh sab likho:\n"
        "1. 30 din ki marketing strategy (4 hafton ka focus)\n"
        "2. 5 ready-to-post captions (Roman Urdu + hashtags)\n"
        "3. 2 ad copy (Facebook/Instagram) with headline\n"
        "4. Pehle mahine ke 3 measurable goals\n"
        "5. Client ko pehle meeting mein poochne wale 5 sawal"
    )


def render_ai_tab(r: Report) -> None:
    if not ai_provider():
        st.info("AI agent abhi band hai. Streamlit Secrets mein GEMINI_API_KEY daalte hi yeh chal jayega.")
        return

    if not ai_unlocked():
        pw = st.text_input("AI password:", type="password", key="ai_pw")
        if pw:
            if hmac.compare_digest(pw.encode(), str(get_secret("APP_PASSWORD")).encode()):
                st.session_state["ai_ok"] = True
                st.rerun()
            else:
                st.error("Password galat hai.")
        return

    st.caption(f"Aaj ki baqi AI requests: {ai_calls_left()}")
    chat: list[tuple[str, str]] = st.session_state.setdefault("ai_chat", [])

    if st.button("🤖 Is business ki poori strategy likho", type="primary", key="ai_strategy"):
        with st.spinner("AI soch raha hai..."):
            answer = call_ai(strategy_prompt(r))
        chat.append((f"Strategy: {r.business}", answer))

    question = st.text_area("Kuch bhi poochein (captions, ad idea, client ko jawab...):", key="ai_q", height=90,
                            placeholder="Jaise: Is shop ke liye Eid sale ka caption likho")
    if st.button("Poochein", key="ai_ask"):
        if question.strip():
            ctx = f"Business: {r.business}, niche: {r.niche.name}, city: {r.city}.\n\n{question.strip()}"
            with st.spinner("AI soch raha hai..."):
                answer = call_ai(ctx, chat)
            chat.append((question.strip(), answer))
        else:
            st.warning("Pehle sawal likhein.")

    for q, a in reversed(chat[-6:]):
        with st.container(border=True):
            st.markdown(f"**{q}**")
            st.markdown(a)


# ---------------------------------------------------------------------------
# Visual design: 3D hero (Three.js), sidebar logo, theme CSS.
# These strings are static: no user input is ever injected into them.
# ---------------------------------------------------------------------------
HERO_HTML = """
<style>
  *{box-sizing:border-box}
  html,body{margin:0;height:100%;background:transparent;font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
  #wrap{position:relative;height:100%;border-radius:24px;overflow:hidden;cursor:none;
        background:
          radial-gradient(48% 85% at 76% 52%,rgba(255,106,60,.20) 0%,rgba(255,106,60,0) 70%),
          radial-gradient(60% 90% at 90% 0%,rgba(124,92,255,.34) 0%,rgba(124,92,255,0) 70%),
          linear-gradient(135deg,#0b0924 0%,#120e38 55%,#06050f 100%);
        box-shadow:inset 0 0 0 1px rgba(255,255,255,.08),0 24px 70px rgba(40,20,120,.40)}
  canvas{position:absolute;inset:0;width:100%;height:100%;display:block;touch-action:pan-y;opacity:0;transition:opacity 1s ease}
  canvas.on{opacity:1}
  .txt{position:absolute;left:38px;top:50%;transform:translateY(-50%);color:#fff;max-width:48%;z-index:2;pointer-events:none}
  .eyebrow{display:inline-flex;align-items:center;gap:8px;padding:6px 14px;border-radius:999px;font-size:13px;
        letter-spacing:.5px;color:#9dffd2;background:rgba(120,255,190,.10);border:1px solid rgba(125,255,191,.30);backdrop-filter:blur(8px)}
  .dot{width:7px;height:7px;border-radius:50%;background:#5dffb0;box-shadow:0 0 10px #5dffb0;animation:p 1.6s infinite}
  @keyframes p{50%{opacity:.35}}
  h1{margin:16px 0 10px;font-size:clamp(30px,4.6vw,58px);line-height:1.05;letter-spacing:-1px;font-weight:800;
        background:linear-gradient(90deg,#fff 0%,#d8d0ff 50%,#ffb08a 100%);-webkit-background-clip:text;background-clip:text;color:transparent}
  p{margin:0;color:#d6d2f5;font-size:clamp(14px,1.7vw,19px);line-height:1.5}
  .chips{display:flex;flex-wrap:wrap;gap:8px;margin-top:18px}
  .chip{padding:7px 15px;border-radius:999px;font-size:13px;color:#efeaff;background:rgba(255,255,255,.07);
        border:1px solid rgba(255,255,255,.14);backdrop-filter:blur(10px)}
  .hint{position:absolute;right:18px;bottom:12px;font-size:12px;color:rgba(230,225,255,.5);z-index:2;pointer-events:none}
  .cur{position:absolute;left:0;top:0;width:34px;height:34px;margin:-17px 0 0 -17px;border-radius:50%;z-index:3;pointer-events:none;
       border:1.5px solid rgba(255,255,255,.75);box-shadow:0 0 18px rgba(255,170,120,.55),inset 0 0 12px rgba(255,170,120,.25);
       opacity:0;transition:opacity .2s,width .15s,height .15s,margin .15s}
  .cur.show{opacity:1}
  .cur.down{width:22px;height:22px;margin:-11px 0 0 -11px;background:rgba(255,170,120,.25)}
  .cur i{position:absolute;left:50%;top:50%;width:5px;height:5px;margin:-2.5px 0 0 -2.5px;border-radius:50%;background:#fff}
  @media(max-width:640px){.txt{left:18px;right:18px;max-width:none;top:20px;transform:none}h1{margin:12px 0 6px}.chips,.hint{display:none}#wrap{cursor:auto}.cur{display:none}}
</style>
<div id="wrap">
  <canvas id="c"></canvas>
  <div class="txt">
    <span class="eyebrow"><span class="dot"></span>Cloud LIVE</span>
    <h1>Aziz Digital<br>Marketer Agent</h1>
    <p>Business ka naam likho. Research, 30-din ka plan aur WhatsApp pitch, ek minute mein.</p>
    <div class="chips"><span class="chip">11 Niches</span><span class="chip">30-Day Plan</span><span class="chip">AI Agent</span></div>
  </div>
  <div class="hint">Mouse hilao, drag karo, click karo</div>
  <div class="cur" id="cur"><i></i></div>
</div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
<script>
(function () {
  if (typeof THREE === 'undefined') { return; }            // CDN blocked: gradient banner only
  var wrap = document.getElementById('wrap'), canvas = document.getElementById('c'), cur = document.getElementById('cur'), renderer;
  try { renderer = new THREE.WebGLRenderer({ canvas: canvas, alpha: true, antialias: true, powerPreference: 'high-performance' }); }
  catch (e) { return; }                                    // no WebGL: gradient banner only

  var small = Math.min(window.screen.width || 1000, window.innerWidth) < 700;
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, small ? 1.5 : 2));
  renderer.outputEncoding = THREE.sRGBEncoding;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.0;

  var scene = new THREE.Scene();
  var FOV = 36, DIST = 9;
  var camera = new THREE.PerspectiveCamera(FOV, 1, 0.1, 100);
  camera.position.set(0, 0, DIST);

  // ---- Studio environment: softboxes that give the metal real reflections ---------------
  (function () {
    var env = new THREE.Scene();
    env.add(new THREE.Mesh(new THREE.SphereGeometry(30, 48, 24), new THREE.MeshBasicMaterial({ color: 0x100c2c, side: THREE.BackSide })));
    function panel(color, k, w, h, x, y, z) {
      var m = new THREE.Mesh(new THREE.PlaneGeometry(w, h),
        new THREE.MeshBasicMaterial({ color: new THREE.Color(color).multiplyScalar(k), side: THREE.DoubleSide }));
      m.position.set(x, y, z); m.lookAt(0, 0, 0); env.add(m);
    }
    panel(0xffffff, 7, 18, 5, 0, 16, 6);
    panel(0xffb27a, 6, 4, 14, 15, 0, 3);
    panel(0x7fb6ff, 5, 4, 14, -15, 2, 3);
    panel(0xffffff, 3.4, 30, 20, 0, 2, 22);
    panel(0xdfe6ff, 2.2, 6, 30, 0, 0, -20);
    panel(0x05040f, 1.0, 26, 3, 0, -3, 14);   // dark band for chrome contrast
    panel(0x9c7bff, 3, 16, 4, 0, -14, 6);
    panel(0xffffff, 3, 2, 10, -8, 0, -14);
    var pm = new THREE.PMREMGenerator(renderer);
    scene.environment = pm.fromScene(env, 0.015).texture;
    pm.dispose();
  })();

  scene.add(new THREE.AmbientLight(0x6a5cff, 0.2));
  var sun = new THREE.DirectionalLight(0xffffff, 1.1); sun.position.set(4, 6, 6); scene.add(sun);
  var cursorLight = new THREE.PointLight(0xffb98a, 4, 16, 1.8); cursorLight.position.set(0, 0, 3.4); scene.add(cursorLight);

  function glowTex(a, b) {
    var c = document.createElement('canvas'); c.width = c.height = 128;
    var g = c.getContext('2d'), gr = g.createRadialGradient(64, 64, 0, 64, 64, 64);
    gr.addColorStop(0, a); gr.addColorStop(0.4, b); gr.addColorStop(1, 'rgba(0,0,0,0)');
    g.fillStyle = gr; g.fillRect(0, 0, 128, 128); return new THREE.CanvasTexture(c);
  }

  var stage = new THREE.Group(); scene.add(stage);      // position / scale / float
  var tilt = new THREE.Group(); stage.add(tilt);        // follows the mouse
  var piece = new THREE.Group(); tilt.add(piece);       // spins when dragged

  // ---- Chrome letter "A" (extruded, bevelled) -------------------------------------------
  var A = new THREE.Shape();
  A.moveTo(-1.30, -1.55); A.lineTo(-0.30, 1.55); A.lineTo(0.30, 1.55); A.lineTo(1.30, -1.55);
  A.lineTo(0.64, -1.55); A.lineTo(0.42, -0.92); A.lineTo(-0.42, -0.92); A.lineTo(-0.64, -1.55); A.lineTo(-1.30, -1.55);
  var hole = new THREE.Path(); hole.moveTo(0, 0.72); hole.lineTo(0.24, -0.22); hole.lineTo(-0.24, -0.22); hole.lineTo(0, 0.72);
  A.holes.push(hole);
  var aGeo = new THREE.ExtrudeGeometry(A, { depth: 0.55, bevelEnabled: true, bevelThickness: 0.11, bevelSize: 0.1, bevelSegments: 8, curveSegments: 6 });
  aGeo.translate(0, 0, -0.275);
  var chrome = new THREE.MeshPhysicalMaterial({ color: 0xe9ecff, metalness: 1, roughness: 0.16, clearcoat: 1, clearcoatRoughness: 0.03, envMapIntensity: 2.2 });
  var letter = new THREE.Mesh(aGeo, chrome); piece.add(letter);

  // ---- Glowing growth arrow (a tube that "draws" itself) ----------------------------------
  var pts = [[-1.55, -1.05, 0.62], [-0.78, -0.45, 0.66], [-0.2, -0.95, 0.66], [0.55, -0.05, 0.66], [1.05, 0.38, 0.66], [1.75, 1.15, 0.62]]
    .map(function (p) { return new THREE.Vector3(p[0], p[1], p[2]); });
  var curve = new THREE.CatmullRomCurve3(pts, false, 'catmullrom', 0.3);
  var TSEG = 160, RSEG = 18;
  var tube = new THREE.Mesh(new THREE.TubeGeometry(curve, TSEG, 0.085, RSEG, false),
    new THREE.MeshStandardMaterial({ color: 0x1b6b4e, emissive: 0x38ffb2, emissiveIntensity: 0.9, metalness: 0.2, roughness: 0.3 }));
  piece.add(tube);
  var tubeIndexCount = tube.geometry.index.count;
  var head = new THREE.Mesh(new THREE.ConeGeometry(0.24, 0.5, 32),
    new THREE.MeshStandardMaterial({ color: 0x2a8a62, emissive: 0xb6ff7a, emissiveIntensity: 1.0, metalness: 0.2, roughness: 0.3 }));
  piece.add(head);
  var up = new THREE.Vector3(0, 1, 0), tmpT = new THREE.Vector3();
  function placeHead(u) {
    var p = curve.getPoint(u); curve.getTangent(Math.min(u, 0.999), tmpT);
    head.position.copy(p).addScaledVector(tmpT, 0.2); head.quaternion.setFromUnitVectors(up, tmpT);
  }
  var arrowGlow = new THREE.Sprite(new THREE.SpriteMaterial({ map: glowTex('rgba(120,255,190,.9)', 'rgba(60,255,170,.25)'),
    blending: THREE.AdditiveBlending, depthWrite: false, transparent: true, opacity: 0.0 }));
  arrowGlow.scale.set(1.8, 1.8, 1); piece.add(arrowGlow);

  // ---- Gold ring + orbiting spark + halo ------------------------------------------------------
  var goldMat = new THREE.MeshPhysicalMaterial({ color: 0xffb16b, metalness: 1, roughness: 0.16, clearcoat: 1, envMapIntensity: 1.8 });
  var ring = new THREE.Mesh(new THREE.TorusGeometry(2.55, 0.06, 36, 200), goldMat); ring.rotation.set(1.05, 0.25, 0.1); stage.add(ring);
  var ring2 = new THREE.Mesh(new THREE.TorusGeometry(2.35, 0.012, 12, 200), new THREE.MeshBasicMaterial({ color: 0xb7a8ff, transparent: true, opacity: 0.4 }));
  ring2.rotation.set(1.3, -0.5, 0.2); stage.add(ring2);
  var spark = new THREE.Mesh(new THREE.SphereGeometry(0.13, 32, 24), new THREE.MeshBasicMaterial({ color: 0xffe9b0 })); stage.add(spark);
  var sparkGlow = new THREE.Sprite(new THREE.SpriteMaterial({ map: glowTex('rgba(255,225,160,1)', 'rgba(255,150,80,.35)'),
    blending: THREE.AdditiveBlending, depthWrite: false, transparent: true })); sparkGlow.scale.set(1.1, 1.1, 1); stage.add(sparkGlow);
  var halo = new THREE.Sprite(new THREE.SpriteMaterial({ map: glowTex('rgba(150,120,255,.9)', 'rgba(110,70,255,.22)'),
    blending: THREE.AdditiveBlending, depthWrite: false, transparent: true, opacity: 0.55 })); halo.scale.set(9, 9, 1); halo.position.z = -1.5; stage.add(halo);

  // ---- Floating chrome beads --------------------------------------------------------------------
  var beads = [[0x4dffc9, 0.16, 0.0, 2.2], [0xff5fd2, 0.12, 2.1, 2.7], [0x7cc4ff, 0.14, 4.2, 3.1]].map(function (d) {
    var m = new THREE.Mesh(new THREE.SphereGeometry(d[1], 40, 28), new THREE.MeshPhysicalMaterial({ color: d[0], metalness: 0.9, roughness: 0.1, clearcoat: 1, envMapIntensity: 1.8 }));
    m.userData = { o: d[2], r: d[3] }; stage.add(m); return m;
  });

  // ---- Dust + stars -------------------------------------------------------------------------------
  var N = small ? 150 : 300, dp = new Float32Array(N * 3), seed = new Float32Array(N);
  for (var i = 0; i < N; i++) { dp[i * 3] = (Math.random() - 0.5) * 22; dp[i * 3 + 1] = (Math.random() - 0.5) * 11; dp[i * 3 + 2] = (Math.random() - 0.5) * 12 - 3; seed[i] = Math.random() * 6.28; }
  var dg = new THREE.BufferGeometry(); dg.setAttribute('position', new THREE.BufferAttribute(dp, 3));
  var dust = new THREE.Points(dg, new THREE.PointsMaterial({ map: glowTex('rgba(255,255,255,1)', 'rgba(190,180,255,.35)'), size: 0.17, transparent: true, opacity: 0.85, depthWrite: false, blending: THREE.AdditiveBlending }));
  scene.add(dust);

  // ---- Layout: always fully inside the banner --------------------------------------------------
  var visH = 1, visW = 1, wide = true, baseScale = 1, baseY = 0;
  function resize() {
    var w = wrap.clientWidth, h = wrap.clientHeight;
    renderer.setSize(w, h, false);
    camera.aspect = w / h; camera.updateProjectionMatrix();
    visH = 2 * Math.tan(THREE.MathUtils.degToRad(FOV / 2)) * DIST; visW = visH * camera.aspect; wide = w > 640;
    baseScale = wide ? Math.min(1.0, visH * 0.74 / 3.9) : Math.min(0.46, visH * 0.30 / 3.9);
    baseY = wide ? 0 : -visH * 0.25;
    stage.position.set(wide ? visW * 0.26 : visW * 0.18, baseY, 0);
  }
  window.addEventListener('resize', resize); resize();

  // ---- Interaction (mouse follows even outside the banner when the page allows) ---------------
  var nx = 0.4, ny = 0, mx = 0.4, my = 0, inside = false, dragging = false, lastX = 0, spin = 0, spinVel = 0, boost = 0, drawStart = 0;
  var host = window, fe = null;
  try { if (window.parent && window.parent !== window && window.parent.document) { host = window.parent; fe = window.frameElement; } } catch (e) { host = window; fe = null; }
  function point(e, fromHost) {
    var r = wrap.getBoundingClientRect(), ox = 0, oy = 0;
    if (fromHost && fe) { var f = fe.getBoundingClientRect(); ox = f.left; oy = f.top; }
    var x = e.clientX - ox - r.left, y = e.clientY - oy - r.top;
    inside = x >= 0 && y >= 0 && x <= r.width && y <= r.height;
    nx = Math.max(-1.5, Math.min(1.5, (x / r.width) * 2 - 1)); ny = Math.max(-1.5, Math.min(1.5, (y / r.height) * 2 - 1));
    cur.style.transform = 'translate(' + x + 'px,' + y + 'px)'; cur.classList.toggle('show', inside);
  }
  function onHostMove(e) { try { point(e, host !== window); } catch (err) {} }
  host.addEventListener('mousemove', onHostMove);
  window.addEventListener('touchmove', function (e) { if (e.touches && e.touches[0]) { point(e.touches[0], false); } }, { passive: true });
  wrap.addEventListener('mouseleave', function () { if (host === window) { inside = false; cur.classList.remove('show'); } });
  wrap.addEventListener('pointerdown', function (e) { dragging = true; lastX = e.clientX; cur.classList.add('down'); boost = 1; drawStart = -1; });
  window.addEventListener('pointerup', function () { dragging = false; cur.classList.remove('down'); });
  window.addEventListener('pointermove', function (e) { if (dragging) { spinVel = (e.clientX - lastX) * 0.012; lastX = e.clientX; } });
  window.addEventListener('pagehide', function () { try { host.removeEventListener('mousemove', onHostMove); } catch (e) {} });

  // ---- Loop -----------------------------------------------------------------------------------------------
  var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var visible = true, running = false, t0 = performance.now(), last = t0;
  if ('IntersectionObserver' in window) { new IntersectionObserver(function (en) { visible = en[0].isIntersecting; if (visible) { last = performance.now(); start(); } }).observe(wrap); }
  function ease(x) { return 1 - Math.pow(1 - x, 3); }
  var CYCLE = 6.5;                       // arrow draws, glows, then redraws

  function frame(now) {
    running = false;
    var dt = Math.min((now - last) / 1000, 0.05); last = now;
    var t = reduce ? 20 : (now - t0) / 1000, intro = ease(Math.min(t / 1.6, 1));
    if (drawStart === -1) { drawStart = t; }
    mx += (nx - mx) * 0.07; my += (ny - my) * 0.07; boost = Math.max(0, boost - dt * 1.3);

    // drag adds spin; after release it eases back so the A always settles facing the viewer
    if (!dragging) { spinVel *= 0.94; var home = Math.round(spin / 6.2832) * 6.2832; spin += (home - spin) * 0.03; }
    spin += spinVel;
    piece.rotation.y = spin + Math.sin(t * 0.55) * 0.42;
    tilt.rotation.x = THREE.MathUtils.lerp(tilt.rotation.x, my * 0.3, 0.08);
    tilt.rotation.y = THREE.MathUtils.lerp(tilt.rotation.y, (mx - 0.4) * 0.45, 0.08);
    stage.scale.setScalar(baseScale * (0.4 + 0.6 * intro));
    stage.position.y = baseY + Math.sin(t * 1.15) * 0.1 - (1 - intro) * 2;

    // arrow draw cycle
    var ct = ((t - (drawStart > 0 ? drawStart : 0)) % CYCLE + CYCLE) % CYCLE;
    var prog = reduce ? 1 : Math.min(ct / 2.2, 1), pe = ease(prog);
    tube.geometry.setDrawRange(0, Math.max(6, Math.floor(tubeIndexCount * pe / 3) * 3));
    head.visible = pe > 0.04; placeHead(Math.max(pe, 0.02));
    var flash = reduce ? 0.3 : (ct > 2.2 && ct < 3.4 ? Math.sin((ct - 2.2) / 1.2 * Math.PI) : 0);
    arrowGlow.position.copy(head.position); arrowGlow.material.opacity = 0.2 + flash * 0.7 + boost * 0.4;
    tube.material.emissiveIntensity = 0.8 + flash * 0.9 + boost * 0.7; head.material.emissiveIntensity = 0.9 + flash * 1.0 + boost * 0.7;

    // rings, spark, beads
    ring.rotation.z = t * 0.22; ring.rotation.x = 1.05 + Math.sin(t * 0.4) * 0.08; ring2.rotation.z = -t * 0.12;
    ring.scale.setScalar(intro); ring2.scale.setScalar(intro);
    var sa = t * 0.9; ring.updateMatrix();
    spark.position.set(Math.cos(sa) * 2.55, Math.sin(sa) * 2.55, 0).applyMatrix4(ring.matrix); sparkGlow.position.copy(spark.position);
    beads.forEach(function (b, i) { var a = t * (0.35 + i * 0.1) + b.userData.o, r = b.userData.r;
      b.position.set(Math.cos(a) * r, Math.sin(a * 1.3) * 1.2, Math.sin(a) * r * 0.45 - 0.5); b.scale.setScalar(intro); });
    halo.material.opacity = 0.45 + Math.sin(t * 1.4) * 0.08 + boost * 0.2;

    // cursor light moves the highlights over the metal
    cursorLight.position.set(mx * visW * 0.5, -my * visH * 0.5, 3.4);
    cursorLight.intensity = inside ? 4.8 : 2.4;

    var dpa = dg.attributes.position.array;
    for (var i = 0; i < N; i++) { dpa[i * 3 + 1] += Math.sin(t * 0.6 + seed[i]) * 0.0016; }
    dg.attributes.position.needsUpdate = true; dust.position.x = -mx * 0.4; dust.position.y = my * 0.25;

    camera.lookAt(0, 0, 0);
    renderer.render(scene, camera);
    if (!reduce && visible) { start(); }
  }
  function start() { if (!running) { running = true; requestAnimationFrame(frame); } }
  canvas.classList.add('on');
  start();
})();
</script>
"""

LOGO_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 600" width="100%" height="100%" role="img" aria-label="Aziz Digital Marketer Agent">
<title>Aziz Digital Marketer Agent</title><style>
/* animation 1: growth arrow draws itself, then holds */
.draw{stroke-dasharray:520;stroke-dashoffset:0;animation:draw 4.5s ease-in-out infinite}
.head{animation:head 4.5s ease-in-out infinite;transform-box:fill-box;transform-origin:center}
@keyframes draw{0%{stroke-dashoffset:520}38%,92%{stroke-dashoffset:0}100%{stroke-dashoffset:0;opacity:.0}}
@keyframes head{0%,34%{opacity:0;transform:scale(.4)}46%,92%{opacity:1;transform:scale(1)}100%{opacity:0}}
/* animation 2: light sweep across the name */
.shine{animation:shine 4.5s ease-in-out infinite}
@keyframes shine{0%,30%{transform:translateX(-500px)}75%,100%{transform:translateX(1700px)}}
/* animation 3: glowing ring pulse (the orbiting spark is SMIL below) */
.pulse{animation:pulse 3s ease-in-out infinite}
@keyframes pulse{50%{opacity:.35}}
@media (prefers-reduced-motion:reduce){*{animation:none!important}}
</style><defs>
<linearGradient id="ring" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#ffe29a"/><stop offset=".5" stop-color="#ff7a3c"/><stop offset="1" stop-color="#d81b4a"/></linearGradient>
<radialGradient id="disc" cx=".35" cy=".25" r=".95"><stop offset="0" stop-color="#3a2a8f"/><stop offset=".55" stop-color="#15103f"/><stop offset="1" stop-color="#07061a"/></radialGradient>
<linearGradient id="aG" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#ffffff"/><stop offset="1" stop-color="#b9acff"/></linearGradient>
<linearGradient id="arrow" x1="0" y1="1" x2="1" y2="0"><stop offset="0" stop-color="#4dffc9"/><stop offset="1" stop-color="#b6ff7a"/></linearGradient>
<linearGradient id="nameG" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#ffffff"/><stop offset=".6" stop-color="#d9d0ff"/><stop offset="1" stop-color="#ffb08a"/></linearGradient>
<linearGradient id="sweep" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset=".5" stop-color="#fff" stop-opacity=".85"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>
<filter id="glow" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="9" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
<filter id="glowS" filterUnits="userSpaceOnUse" x="-100" y="-100" width="800" height="800"><feGaussianBlur stdDeviation="7" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
<filter id="soft" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="22"/></filter>
</defs>
<g id="icon">
  <circle cx="300" cy="300" r="250" fill="#ff6a3c" opacity=".30" filter="url(#soft)"/>
  <circle cx="300" cy="300" r="238" fill="url(#disc)"/>
  <circle cx="300" cy="300" r="238" fill="none" stroke="url(#ring)" stroke-width="14" class="pulse"/>
  <circle cx="300" cy="300" r="214" fill="none" stroke="#ffffff" stroke-opacity=".10" stroke-width="2"/>
  <!-- letter A -->
  <path d="M170 438 L300 150 L430 438" fill="none" stroke="url(#aG)" stroke-width="46" stroke-linecap="round" stroke-linejoin="round"/>
  <path d="M170 438 L300 150" fill="none" stroke="#fff" stroke-opacity=".18" stroke-width="10" stroke-linecap="round"/>
  <!-- growth arrow as the crossbar -->
  <path class="draw" d="M205 392 L262 336 L312 366 L392 270" fill="none" stroke="url(#arrow)" stroke-width="20" stroke-linecap="round" stroke-linejoin="round" filter="url(#glow)"/>
  <path class="head" d="M410 246 L340 262 L388 306 Z" fill="#b6ff7a" filter="url(#glow)"/>
  <!-- spark -->
  <path d="M300 96 L307 118 L329 125 L307 132 L300 154 L293 132 L271 125 L293 118 Z" fill="#fff" opacity=".95" filter="url(#glowS)"/>
  <!-- orbiting spark -->
  <g><circle cx="300" cy="62" r="11" fill="#ffe29a" filter="url(#glowS)"/>
     <animateTransform attributeName="transform" type="rotate" from="0 300 300" to="360 300 300" dur="9s" repeatCount="indefinite"/></g>
</g>
</svg>"""

LOGO_PAGE = ("<body style='margin:0;background:transparent;display:flex;justify-content:center;align-items:center'>"
             "<div style='width:150px;height:150px'>" + LOGO_SVG + "</div></body>")

CUSTOM_CSS = """
<style>
:root{--line:rgba(255,255,255,.12);--card:rgba(255,255,255,.055);--mut:#a9a3d6}
.stApp{background:radial-gradient(70% 50% at 88% -10%,rgba(124,92,255,.30),transparent 60%),
       radial-gradient(50% 40% at 0% 100%,rgba(255,106,60,.13),transparent 60%),#07061a;color:#ece9ff}
header[data-testid="stHeader"]{background:transparent}
.block-container{padding-top:1.4rem;max-width:1180px}
[data-testid="stSidebar"]{background:linear-gradient(180deg,#0d0a2b 0%,#080718 100%);border-right:1px solid var(--line)}
[data-testid="stWidgetLabel"] p{color:#cfc8ff;font-weight:600}
div[data-baseweb="input"],div[data-baseweb="textarea"],div[data-baseweb="base-input"]{background:rgba(255,255,255,.06)!important;border-radius:12px!important}
div[data-baseweb="input"],div[data-baseweb="textarea"]{border:1px solid var(--line)!important}
input,textarea{color:#fff!important}
.stButton>button[kind="primary"]{background:linear-gradient(90deg,#7c5cff,#ff6a3c);border:0;color:#fff;font-weight:700;border-radius:14px;
  padding:.72rem 1.3rem;box-shadow:0 10px 30px rgba(124,92,255,.35);transition:transform .15s,box-shadow .15s}
.stButton>button[kind="primary"]:hover{transform:translateY(-2px);box-shadow:0 14px 36px rgba(255,106,60,.35);color:#fff}
.stButton>button[kind="secondary"],.stDownloadButton>button,[data-testid="stLinkButton"] a{background:rgba(255,255,255,.07);
  border:1px solid var(--line);border-radius:12px;color:#fff}
.stTabs [data-baseweb="tab-list"]{gap:8px;border-bottom:0;flex-wrap:wrap}
.stTabs [data-baseweb="tab"]{background:rgba(255,255,255,.06);border:1px solid var(--line);border-radius:999px;padding:8px 18px;height:auto}
.stTabs [aria-selected="true"]{background:linear-gradient(90deg,#7c5cff,#ff6a3c);border-color:transparent}
.stTabs [data-baseweb="tab-highlight"],.stTabs [data-baseweb="tab-border"]{display:none}
div[data-testid="stVerticalBlockBorderWrapper"]{background:var(--card);border:1px solid var(--line)!important;border-radius:20px;backdrop-filter:blur(10px)}
.sec{display:flex;align-items:center;gap:10px;margin:22px 0 10px;font-size:13px;letter-spacing:1px;text-transform:uppercase;color:var(--mut);font-weight:700}
.sec i{display:inline-grid;place-items:center;width:26px;height:26px;border-radius:50%;font-style:normal;color:#fff;
  background:linear-gradient(135deg,#7c5cff,#ff6a3c);font-size:13px}
.rep-head{margin:18px 0 6px}
.rep-head .eb{display:inline-block;padding:5px 12px;border-radius:999px;font-size:12px;color:#9dffd2;background:rgba(120,255,190,.1);
  border:1px solid rgba(125,255,191,.3)}
.rep-head h2{margin:10px 0 10px;font-size:clamp(26px,3.4vw,40px);letter-spacing:-.6px;
  background:linear-gradient(90deg,#fff,#d8d0ff 60%,#ffb08a);-webkit-background-clip:text;background-clip:text;color:transparent}
.kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:14px 0 6px}
.kpi{background:var(--card);border:1px solid var(--line);border-radius:18px;padding:16px 18px}
.kpi small{color:var(--mut);font-size:12px;letter-spacing:.7px;text-transform:uppercase}
.kpi b{display:block;margin-top:6px;font-size:21px;color:#fff}
.chips{display:flex;flex-wrap:wrap;gap:8px}
.chip{padding:7px 14px;border-radius:999px;background:rgba(124,92,255,.15);border:1px solid rgba(160,140,255,.38);color:#eae6ff;font-size:13px;
  animation:bob 6s ease-in-out infinite}
.chip.o{background:rgba(255,106,60,.14);border-color:rgba(255,150,110,.4)}
.chip.g{background:rgba(77,255,201,.12);border-color:rgba(77,255,201,.35)}
.chip:nth-child(2n){animation-delay:-2s}.chip:nth-child(3n){animation-delay:-4s}
@keyframes bob{50%{transform:translateY(-3px)}}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.info{background:var(--card);border:1px solid var(--line);border-radius:18px;padding:16px 18px}
.info h4{margin:0 0 10px;font-size:12px;color:var(--mut);text-transform:uppercase;letter-spacing:.9px}
.info p{margin:0;color:#ece9ff;line-height:1.5}
.weeks{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}
.week{background:var(--card);border:1px solid var(--line);border-radius:18px;padding:14px 16px}
.week h4{margin:0 0 6px;font-size:13px;color:#ffb08a;letter-spacing:.6px}
.day{display:flex;gap:10px;padding:8px 0;border-top:1px solid rgba(255,255,255,.07);font-size:13.5px;line-height:1.4}
.day span{color:#9d8cff;font-weight:700;min-width:30px}
.contact{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:14px 16px;font-size:14px;line-height:1.9}
.contact a{color:#9dffd2;text-decoration:none}
.foot{text-align:center;color:var(--mut);font-size:13px;padding:10px 0 18px}
@media(max-width:900px){.kpis{grid-template-columns:1fr 1fr}.weeks{grid-template-columns:1fr 1fr}}
@media(max-width:600px){.grid2,.weeks{grid-template-columns:1fr}}
@media(prefers-reduced-motion:reduce){.chip{animation:none}}
/* Keep text readable even when the visitor's browser is in light mode */
[data-testid="stSidebar"] p,[data-testid="stSidebar"] span,[data-testid="stSidebar"] label,[data-testid="stSidebar"] summary,
[data-testid="stSidebar"] h1,[data-testid="stSidebar"] h2,[data-testid="stSidebar"] h3,
.stMarkdown p,[data-testid="stCaptionContainer"],[data-testid="stRadio"] label p,[data-testid="stRadio"] label div,
[data-testid="stExpander"] summary p,[data-testid="stExpander"] summary span,[data-testid="stCheckbox"] p{color:#ece9ff}
.stTabs [data-baseweb="tab"] p,.stTabs [data-baseweb="tab"] div{color:#ece9ff}
.stTabs [aria-selected="true"] p,.stTabs [aria-selected="true"] div{color:#fff!important;font-weight:700}
div[data-baseweb="input"] input,div[data-baseweb="base-input"] input,div[data-baseweb="textarea"] textarea{background:transparent!important;color:#fff!important}
div[data-baseweb="input"] button{background:transparent!important;color:#fff!important}
div[data-baseweb="select"]>div{background:rgba(255,255,255,.06)!important;border:1px solid var(--line)!important;border-radius:12px!important;color:#fff!important}
div[data-baseweb="select"] *{color:#fff!important}
[data-testid="stExpander"] details{background:rgba(255,255,255,.04);border:1px solid var(--line);border-radius:14px}
[data-testid="stCode"],[data-testid="stCode"] pre,.stCodeBlock pre{background:rgba(255,255,255,.05)!important;color:#ece9ff!important;border-radius:14px}
[data-testid="stCode"] code,.stCodeBlock code{color:#ece9ff!important}
</style>
"""


# ---------------------------------------------------------------------------
# UI helpers
# ---------------------------------------------------------------------------
def chips(items, cls: str = "") -> str:
    """Bubble-style tags. Everything is HTML-escaped."""
    return '<div class="chips">' + "".join(f'<span class="chip {cls}">{escape(str(i))}</span>' for i in items) + "</div>"


def info_card(title: str, body_html: str) -> str:
    return f'<div class="info"><h4>{escape(title)}</h4>{body_html}</div>'


def section(num: int, text: str) -> None:
    st.markdown(f'<div class="sec"><i>{num}</i>{escape(text)}</div>', unsafe_allow_html=True)


def render_sidebar_header() -> None:
    with st.sidebar:
        if hasattr(st, "iframe"):
            st.iframe(LOGO_PAGE, height=160)
        else:
            import streamlit.components.v1 as components  # older Streamlit only

            components.html(LOGO_PAGE, height=160)
        st.markdown(f"### {AGENCY}")
        st.markdown(
            '<div class="contact">'
            f'📞 <a href="tel:0{MY_WA[2:]}">0{MY_WA[2:]}</a><br>'
            f"📍 {escape(DEFAULT_CITY)}<br>☁️ Cloud LIVE</div>",
            unsafe_allow_html=True,
        )
        st.markdown('<div class="sec">Packages</div>', unsafe_allow_html=True)
        for pkg in PACKAGES:
            with st.expander(f"{pkg.name} - Rs {pkg.price:,}"):
                st.markdown(chips(pkg.items, "g"), unsafe_allow_html=True)


def render_hero() -> None:
    """Show the 3D banner. st.iframe on current Streamlit, components.html on older versions."""
    if hasattr(st, "iframe"):
        st.iframe(HERO_HTML, height=360)
    else:
        import streamlit.components.v1 as components  # older Streamlit only

        components.html(HERO_HTML, height=360)


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
        st.markdown('<div class="sec">Pichli reports</div>', unsafe_allow_html=True)
        st.selectbox(
            "Reload a report",
            [r.label for r in history],
            index=None,
            placeholder="Select a report",
            key="history_pick",
            on_change=_load_history_pick,
            label_visibility="collapsed",
        )


def _slug(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_") or "report"


def render_report(r: Report) -> None:
    st.markdown(
        '<div class="rep-head"><span class="eb">Report ready</span>'
        f"<h2>{escape(r.business)}</h2>"
        + chips([r.niche.name, r.city], "o")
        + "</div>",
        unsafe_allow_html=True,
    )
    if not r.matched:
        st.warning("Niche pehchana nahi gaya, general plan diya gaya hai. Business name mein niche ka "
                   "lafz likho (jaise 'clothes', 'salon', 'clinic').")

    st.markdown(
        '<div class="kpis">'
        f'<div class="kpi"><small>Niche</small><b>{escape(r.niche.name)}</b></div>'
        f'<div class="kpi"><small>Package</small><b>{escape(r.package.name)}</b></div>'
        f'<div class="kpi"><small>Price / month</small><b>Rs {r.package.price:,}</b></div>'
        f'<div class="kpi"><small>Posts planned</small><b>{len(r.plan)}</b></div></div>',
        unsafe_allow_html=True,
    )

    tab_research, tab_plan, tab_pitch, tab_ai = st.tabs(
        ["Research", "30-Day Plan", "WhatsApp Pitch", "🤖 AI Agent"])

    with tab_research:
        st.markdown(
            '<div class="grid2">'
            + info_card("Audience", f"<p>{escape(r.niche.audience)}</p>")
            + info_card("Offer idea", f"<p>{escape(r.niche.hook)}</p>")
            + info_card("Platforms", chips(r.niche.platforms))
            + info_card("Ad budget split", f"<p>{escape(r.niche.ad_split)}</p>")
            + info_card("Hashtags", chips(r.niche.hashtags, "o"))
            + info_card("Package includes", chips(r.package.items, "g"))
            + "</div>",
            unsafe_allow_html=True,
        )

    with tab_plan:
        weeks: dict[str, list[tuple[str, str]]] = {}
        for label, idea in r.plan:
            wk, day = label.split(" - ")
            weeks.setdefault(wk, []).append((day, idea))
        cards = "".join(
            f'<div class="week"><h4>{escape(wk.upper())}</h4>'
            + "".join(f'<div class="day"><span>{escape(d)}</span>{escape(i)}</div>' for d, i in days)
            + "</div>"
            for wk, days in weeks.items()
        )
        st.markdown(f'<div class="weeks">{cards}</div>', unsafe_allow_html=True)
        st.download_button("Download plan (.csv)", plan_to_csv(r.plan),
                           file_name=f"{_slug(r.business)}_content_plan.csv", mime="text/csv")

    with tab_pitch:
        st.code(r.pitch, language=None)
        if r.client_wa:
            st.link_button("Client ko WhatsApp karo", build_whatsapp_link(r), type="primary")
        else:
            st.link_button("WhatsApp par kholo (aap ke number par)", build_whatsapp_link(r))
            st.caption("Client ka WhatsApp number upar daalo to yeh button seedha client ki chat kholega.")

    with tab_ai:
        render_ai_tab(r)


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------
def main() -> None:
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
    render_sidebar_header()
    render_hero()

    section(1, "Client ki details")
    with st.container(border=True):
        c1, c2, c3 = st.columns([2, 1, 1])
        business = c1.text_input("Business Name:", placeholder="Peshawar Clothes Shop", max_chars=60)
        city = c2.text_input("City:", value=DEFAULT_CITY, max_chars=40)
        budget = c3.number_input("Client monthly budget (Rs):", min_value=0, value=15000, step=5000)

        c4, c5 = st.columns([1, 1])
        client_raw = c4.text_input("Client WhatsApp number (optional):", placeholder="0333 1234567")
        lang = c5.radio("Pitch language:", ["Roman Urdu", "English"], horizontal=True)

        if budget < PACKAGES[0].price:
            st.caption(f"Note: sab se chota package Rs {PACKAGES[0].price:,} ka hai.")
        go = st.button("Generate PRO Report", type="primary", use_container_width=True)

    if go:
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
            st.toast("Report tayyar hai ✅")

    result = st.session_state.get("result")
    if result:
        section(2, "Aap ki report")
        render_report(result)

    render_sidebar_history()
    st.markdown(f'<div class="foot">Powered by {escape(AGENCY)} | 0{MY_WA[2:]} | {escape(DEFAULT_CITY)}</div>',
                unsafe_allow_html=True)


main()
