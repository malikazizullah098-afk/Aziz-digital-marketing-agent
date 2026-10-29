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

import streamlit as st

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
AGENCY = "Aziz Digital Agency"
MY_WA = "923715221906"  # agency WhatsApp number (international format, no +)
DEFAULT_CITY = "Peshawar"
LOGO_FILE  = "aziz_logo_transparent.png"
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
# 3D hero banner (Three.js, PBR rocket with mouse interaction). Static markup only: no user input is injected.
# ---------------------------------------------------------------------------
HERO_HTML = """
<style>
  *{box-sizing:border-box}
  html,body{margin:0;height:100%;background:transparent;font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
  #wrap{position:relative;height:100%;border-radius:20px;overflow:hidden;cursor:none;
        background:
          radial-gradient(55% 90% at 76% 50%,rgba(255,90,60,.16) 0%,rgba(255,90,60,0) 70%),
          radial-gradient(60% 90% at 85% 10%,rgba(110,80,255,.30) 0%,rgba(110,80,255,0) 70%),
          linear-gradient(135deg,#0a0820 0%,#110d33 55%,#06050f 100%);
        box-shadow:inset 0 0 0 1px rgba(255,255,255,.07),0 20px 60px rgba(40,20,120,.35)}
  canvas{position:absolute;inset:0;width:100%;height:100%;display:block;touch-action:pan-y;opacity:0;transition:opacity 1s ease}
  canvas.on{opacity:1}
  .txt{position:absolute;left:34px;top:50%;transform:translateY(-50%);color:#fff;max-width:50%;z-index:2;pointer-events:none}
  .eyebrow{display:inline-flex;align-items:center;gap:8px;padding:6px 14px;border-radius:999px;font-size:14px;
        letter-spacing:.4px;color:#9dffd2;background:rgba(120,255,190,.10);border:1px solid rgba(125,255,191,.30);
        backdrop-filter:blur(8px)}
  .dot{width:7px;height:7px;border-radius:50%;background:#5dffb0;box-shadow:0 0 10px #5dffb0;animation:p 1.6s infinite}
  @keyframes p{50%{opacity:.35}}
  h1{margin:14px 0 10px;font-size:clamp(30px,4.8vw,56px);line-height:1.08;letter-spacing:-.8px;font-weight:800;
        background:linear-gradient(90deg,#fff 0%,#d8d0ff 50%,#ffb08a 100%);-webkit-background-clip:text;background-clip:text;color:transparent}
  p{margin:0;color:#d6d2f5;font-size:clamp(15px,1.9vw,20px);line-height:1.45}
  .chips{display:flex;flex-wrap:wrap;gap:8px;margin-top:16px}
  .chip{padding:7px 14px;border-radius:10px;font-size:14px;color:#efeaff;background:rgba(255,255,255,.06);
        border:1px solid rgba(255,255,255,.12);backdrop-filter:blur(10px)}
  .hint{position:absolute;right:16px;bottom:10px;font-size:12px;color:rgba(230,225,255,.55);z-index:2;pointer-events:none}
  .cur{position:absolute;left:0;top:0;width:34px;height:34px;margin:-17px 0 0 -17px;border-radius:50%;z-index:3;pointer-events:none;
       border:1.5px solid rgba(255,255,255,.75);box-shadow:0 0 18px rgba(255,170,120,.55),inset 0 0 12px rgba(255,170,120,.25);
       opacity:0;transition:opacity .2s,width .15s,height .15s,margin .15s}
  .cur.show{opacity:1}
  .cur.down{width:22px;height:22px;margin:-11px 0 0 -11px;background:rgba(255,170,120,.25)}
  .cur i{position:absolute;left:50%;top:50%;width:5px;height:5px;margin:-2.5px 0 0 -2.5px;border-radius:50%;background:#fff}
  @media(max-width:640px){.txt{left:18px;right:18px;max-width:none;top:18px;transform:none}h1{margin:10px 0 6px}.chips,.hint{display:none}#wrap{cursor:auto}.cur{display:none}}
</style>
<div id="wrap">
  <canvas id="c"></canvas>
  <div class="txt">
    <span class="eyebrow"><span class="dot"></span>Cloud LIVE</span>
    <h1>Aziz AI Marketing<br>Cloud Agent</h1>
    <p>Research, 30-day content plan aur WhatsApp pitch, ek minute mein.</p>
    <div class="chips"><span class="chip">11 Niches</span><span class="chip">30-Day Plan</span><span class="chip">WhatsApp Pitch</span></div>
  </div>
  <div class="hint">Mouse hilao, drag karo, click karo 🚀</div>
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
  renderer.toneMappingExposure = 0.98;

  var scene = new THREE.Scene();
  var FOV = 36, DIST = 8;
  var camera = new THREE.PerspectiveCamera(FOV, 1, 0.1, 100);
  camera.position.set(0, 0, DIST);

  // ---- Studio environment (real reflections on paint, chrome and glass) -----------
  (function () {
    var env = new THREE.Scene();
    env.add(new THREE.Mesh(new THREE.SphereGeometry(30, 48, 24), new THREE.MeshBasicMaterial({ color: 0x120e2e, side: THREE.BackSide })));
    function panel(color, k, w, h, x, y, z) {
      var m = new THREE.Mesh(new THREE.PlaneGeometry(w, h),
        new THREE.MeshBasicMaterial({ color: new THREE.Color(color).multiplyScalar(k), side: THREE.DoubleSide }));
      m.position.set(x, y, z); m.lookAt(0, 0, 0); env.add(m);
    }
    panel(0xffffff, 7, 16, 5, 0, 16, 6);        // big top softbox
    panel(0xffb27a, 6, 4, 14, 15, 0, 3);        // warm strip (right)
    panel(0x7fb6ff, 5, 4, 14, -15, 2, 3);       // cool strip (left)
    panel(0xffffff, 4, 8, 8, 0, 3, 18);         // front fill
    panel(0x9c7bff, 3, 16, 4, 0, -14, 6);       // violet floor bounce
    panel(0xffffff, 3, 2, 10, -8, 0, -14);      // rim strip behind
    var pm = new THREE.PMREMGenerator(renderer);
    scene.environment = pm.fromScene(env, 0.015).texture;
    pm.dispose();
  })();

  scene.add(new THREE.AmbientLight(0x6a5cff, 0.18));
  var sun = new THREE.DirectionalLight(0xffffff, 1.2); sun.position.set(4, 6, 6); scene.add(sun);
  var cursorLight = new THREE.PointLight(0xffb98a, 4, 14, 1.8); cursorLight.position.set(0, 0, 3); scene.add(cursorLight);

  function glowTex(a, b) {
    var c = document.createElement('canvas'); c.width = c.height = 128;
    var g = c.getContext('2d'), gr = g.createRadialGradient(64, 64, 0, 64, 64, 64);
    gr.addColorStop(0, a); gr.addColorStop(0.4, b); gr.addColorStop(1, 'rgba(0,0,0,0)');
    g.fillStyle = gr; g.fillRect(0, 0, 128, 128); return new THREE.CanvasTexture(c);
  }

  // ---- Rocket (procedural, PBR) -----------------------------------------------------
  var stage = new THREE.Group(); scene.add(stage);           // position / scale / float
  var tilt = new THREE.Group(); stage.add(tilt);             // follows mouse
  var rocket = new THREE.Group(); tilt.add(rocket);          // spins on its axis

  function lathe(pts, seg) {
    var curve = new THREE.SplineCurve(pts.map(function (p) { return new THREE.Vector2(p[0], p[1]); }));
    return new THREE.LatheGeometry(curve.getPoints(90), seg || 96);
  }
  var bodyMat = new THREE.MeshPhysicalMaterial({ color: 0xf4f4f8, metalness: 0.25, roughness: 0.16, clearcoat: 1, clearcoatRoughness: 0.04, envMapIntensity: 1.2 });
  var redMat  = new THREE.MeshPhysicalMaterial({ color: 0x8a0414, metalness: 0.05, roughness: 0.34, clearcoat: 0.8, clearcoatRoughness: 0.1, envMapIntensity: 0.55 });
  var chrome  = new THREE.MeshPhysicalMaterial({ color: 0xffffff, metalness: 1, roughness: 0.07, clearcoat: 1, envMapIntensity: 1.8 });
  var darkMet = new THREE.MeshPhysicalMaterial({ color: 0x22232b, metalness: 1, roughness: 0.32, envMapIntensity: 1.2 });

  rocket.add(new THREE.Mesh(lathe([[0.30, -1.30], [0.40, -1.10], [0.54, -0.75], [0.60, -0.25], [0.60, 0.55], [0.57, 0.92]], 96), bodyMat));
  rocket.add(new THREE.Mesh(lathe([[0.57, 0.90], [0.50, 1.20], [0.36, 1.52], [0.17, 1.82], [0.0, 2.02]], 96), redMat));
  var band = new THREE.Mesh(new THREE.TorusGeometry(0.585, 0.028, 24, 120), redMat); band.rotation.x = Math.PI / 2; band.position.y = 0.88; rocket.add(band);
  var band2 = band.clone(); band2.position.y = -0.62; band2.scale.set(0.95, 0.95, 1); rocket.add(band2);

  var nozzle = new THREE.Mesh(new THREE.CylinderGeometry(0.34, 0.46, 0.34, 64, 1, true), darkMet); nozzle.position.y = -1.42; rocket.add(nozzle);
  var nozzleRim = new THREE.Mesh(new THREE.TorusGeometry(0.34, 0.03, 20, 80), chrome); nozzleRim.rotation.x = Math.PI / 2; nozzleRim.position.y = -1.59; rocket.add(nozzleRim);

  // porthole window
  var winRing = new THREE.Mesh(new THREE.TorusGeometry(0.235, 0.05, 28, 90), chrome); winRing.position.set(0, 0.28, 0.585); rocket.add(winRing);
  var glass = new THREE.Mesh(new THREE.SphereGeometry(0.235, 48, 24), new THREE.MeshPhysicalMaterial({ color: 0x07162e, metalness: 0.1, roughness: 0.02, clearcoat: 1, envMapIntensity: 2.2 }));
  glass.scale.z = 0.35; glass.position.set(0, 0.28, 0.58); rocket.add(glass);

  // fins
  var fs = new THREE.Shape(); fs.moveTo(0, 0.55); fs.lineTo(0.62, -0.38); fs.lineTo(0.62, -0.98); fs.lineTo(0, -0.62); fs.lineTo(0, 0.55);
  var finGeo = new THREE.ExtrudeGeometry(fs, { depth: 0.07, bevelEnabled: true, bevelThickness: 0.025, bevelSize: 0.025, bevelSegments: 4, curveSegments: 10 });
  finGeo.translate(0, 0, -0.035);
  for (var k = 0; k < 3; k++) {
    var pivot = new THREE.Group(); pivot.rotation.y = k * (Math.PI * 2 / 3);
    var fin = new THREE.Mesh(finGeo, redMat); fin.position.set(0.52, -0.38, 0); pivot.add(fin); rocket.add(pivot);
  }

  // flame (additive cones) + glow
  function flameCone(r, h, color, op) {
    var g = new THREE.ConeGeometry(r, h, 40, 1, true); g.rotateX(Math.PI); g.translate(0, -h / 2, 0);
    return new THREE.Mesh(g, new THREE.MeshBasicMaterial({ color: color, transparent: true, opacity: op, blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.DoubleSide }));
  }
  var flameOuter = flameCone(0.34, 1.9, 0xff5a1f, 0.55), flameMid = flameCone(0.24, 1.5, 0xffa21f, 0.7), flameCore = flameCone(0.13, 1.0, 0xfff2c4, 0.95);
  [flameOuter, flameMid, flameCore].forEach(function (f) { f.position.y = -1.58; rocket.add(f); });
  var flameGlow = new THREE.Sprite(new THREE.SpriteMaterial({ map: glowTex('rgba(255,190,120,1)', 'rgba(255,90,30,.35)'), blending: THREE.AdditiveBlending, depthWrite: false, transparent: true, opacity: 0.9 }));
  flameGlow.scale.set(3.6, 3.6, 1); flameGlow.position.y = -1.9; rocket.add(flameGlow);
  var flameLight = new THREE.PointLight(0xff7a2a, 3, 9, 1.8); flameLight.position.y = -2.0; rocket.add(flameLight);

  // orbit ring + small planets
  var orbit = new THREE.Mesh(new THREE.TorusGeometry(2.2, 0.012, 12, 200), new THREE.MeshBasicMaterial({ color: 0xbfb2ff, transparent: true, opacity: 0.35 }));
  orbit.rotation.set(1.25, 0.15, 0.25); stage.add(orbit);
  var planets = [[0xffc46b, 0.16, 0.0], [0x4dffc9, 0.12, 2.1], [0xff5fd2, 0.14, 4.2]].map(function (d) {
    var m = new THREE.Mesh(new THREE.SphereGeometry(d[1], 40, 28), new THREE.MeshPhysicalMaterial({ color: d[0], metalness: 0.9, roughness: 0.12, clearcoat: 1, envMapIntensity: 1.8 }));
    m.userData.o = d[2]; stage.add(m); return m;
  });

  // ---- Exhaust particles (world space) ---------------------------------------------------
  var M = small ? 90 : 170, ep = new Float32Array(M * 3), ec = new Float32Array(M * 3), ev = [], el = new Float32Array(M);
  for (var i = 0; i < M; i++) { ev.push(new THREE.Vector3()); el[i] = 0; ep[i * 3 + 1] = -999; }
  var eg = new THREE.BufferGeometry();
  eg.setAttribute('position', new THREE.BufferAttribute(ep, 3)); eg.setAttribute('color', new THREE.BufferAttribute(ec, 3));
  var exhaust = new THREE.Points(eg, new THREE.PointsMaterial({ map: glowTex('rgba(255,255,255,1)', 'rgba(255,200,150,.5)'), size: 0.34, vertexColors: true,
    transparent: true, depthWrite: false, blending: THREE.AdditiveBlending }));
  exhaust.frustumCulled = false; scene.add(exhaust);
  var spawnAcc = 0, nz = new THREE.Vector3(), dn = new THREE.Vector3(), q = new THREE.Quaternion();

  // ---- Stars ------------------------------------------------------------------------------------
  var SN = small ? 160 : 320, sp = new Float32Array(SN * 3);
  for (var s = 0; s < SN; s++) { sp[s * 3] = (Math.random() - 0.5) * 30; sp[s * 3 + 1] = (Math.random() - 0.5) * 14; sp[s * 3 + 2] = -3 - Math.random() * 12; }
  var sg = new THREE.BufferGeometry(); sg.setAttribute('position', new THREE.BufferAttribute(sp, 3));
  var stars = new THREE.Points(sg, new THREE.PointsMaterial({ map: glowTex('rgba(255,255,255,1)', 'rgba(190,180,255,.35)'), size: 0.16, transparent: true, opacity: 0.9, depthWrite: false, blending: THREE.AdditiveBlending }));
  scene.add(stars);

  // ---- Layout (always fully inside the banner) -------------------------------------------------
  var visH = 1, visW = 1, wide = true, baseScale = 1;
  function resize() {
    var w = wrap.clientWidth, h = wrap.clientHeight;
    renderer.setSize(w, h, false);
    camera.aspect = w / h; camera.updateProjectionMatrix();
    visH = 2 * Math.tan(THREE.MathUtils.degToRad(FOV / 2)) * DIST; visW = visH * camera.aspect; wide = w > 640;
    baseScale = wide ? Math.min(1.0, visH * 0.74 / 4.1) : Math.min(0.62, visH * 0.40 / 4.1);
    stage.position.set(wide ? visW * 0.265 : visW * 0.2, wide ? 0 : -visH * 0.2, 0);
  }
  window.addEventListener('resize', resize); resize();

  // ---- Interaction: mouse follow (also outside the banner when the page allows), drag, click -------
  var nx = 0.4, ny = 0, mx = 0.4, my = 0, inside = false, dragging = false, lastX = 0, spin = 0, spinVel = 0, boost = 0;
  var host = window, fe = null;
  try { if (window.parent && window.parent !== window && window.parent.document) { host = window.parent; fe = window.frameElement; } } catch (e) { host = window; fe = null; }

  function point(e, fromHost) {
    var r = wrap.getBoundingClientRect(), ox = 0, oy = 0;
    if (fromHost && fe) { var f = fe.getBoundingClientRect(); ox = f.left; oy = f.top; }
    var x = e.clientX - ox - r.left, y = e.clientY - oy - r.top;
    inside = x >= 0 && y >= 0 && x <= r.width && y <= r.height;
    nx = Math.max(-1.5, Math.min(1.5, (x / r.width) * 2 - 1)); ny = Math.max(-1.5, Math.min(1.5, (y / r.height) * 2 - 1));
    cur.style.transform = 'translate(' + x + 'px,' + y + 'px)';
    cur.classList.toggle('show', inside);
  }
  function onHostMove(e) { try { point(e, host !== window); } catch (err) {} }
  function onTouch(e) { if (e.touches && e.touches[0]) { point(e.touches[0], false); } }
  host.addEventListener('mousemove', onHostMove);
  window.addEventListener('touchmove', onTouch, { passive: true });
  wrap.addEventListener('mouseleave', function () { if (host === window) { inside = false; cur.classList.remove('show'); } });
  wrap.addEventListener('pointerdown', function (e) { dragging = true; lastX = e.clientX; cur.classList.add('down'); boost = 1; });
  window.addEventListener('pointerup', function () { dragging = false; cur.classList.remove('down'); });
  window.addEventListener('pointermove', function (e) { if (dragging) { spinVel = (e.clientX - lastX) * 0.012; lastX = e.clientX; } });
  window.addEventListener('pagehide', function () { try { host.removeEventListener('mousemove', onHostMove); } catch (e) {} });

  // ---- Loop --------------------------------------------------------------------------------------
  var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var visible = true, running = false, t0 = performance.now(), last = t0;
  if ('IntersectionObserver' in window) { new IntersectionObserver(function (en) { visible = en[0].isIntersecting; if (visible) { last = performance.now(); start(); } }).observe(wrap); }
  function ease(x) { return 1 - Math.pow(1 - x, 3); }
  var tmp = new THREE.Vector3();

  function frame(now) {
    running = false;
    var dt = Math.min((now - last) / 1000, 0.05); last = now;
    var t = reduce ? 10 : (now - t0) / 1000, intro = ease(Math.min(t / 1.5, 1));
    mx += (nx - mx) * 0.07; my += (ny - my) * 0.07;
    boost = Math.max(0, boost - dt * 1.4);

    // spin: drag adds momentum, otherwise a slow turn that shows off the reflections
    if (!dragging) { spinVel += (0.0035 - spinVel) * 0.03; }
    spin += spinVel; rocket.rotation.y = spin;

    // rocket leans towards the cursor
    tilt.rotation.z = THREE.MathUtils.lerp(tilt.rotation.z, -0.5 - (mx - 0.4) * 0.35, 0.08);
    tilt.rotation.x = THREE.MathUtils.lerp(tilt.rotation.x, my * 0.32, 0.08);
    stage.scale.setScalar(baseScale * (0.35 + 0.65 * intro));
    stage.position.y = (wide ? 0 : -visH * 0.2) + Math.sin(t * 1.2) * 0.11 - (1 - intro) * 2.2;
    stage.rotation.y = mx * 0.18;

    // light that follows the cursor over the banner (moves the highlights on paint and chrome)
    cursorLight.position.set(mx * visW * 0.5, -my * visH * 0.5, 3.2);
    cursorLight.intensity = inside ? 4.6 : 2.2;

    // flame
    var fl = 1 + Math.sin(t * 38) * 0.06 + Math.sin(t * 23 + 1.3) * 0.05 + boost * 0.7;
    flameOuter.scale.set(1 + Math.sin(t * 31) * 0.05, fl * 1.05, 1 + Math.cos(t * 29) * 0.05);
    flameMid.scale.set(1, fl * 0.97, 1); flameCore.scale.set(1, fl * 0.9, 1);
    flameGlow.material.opacity = 0.75 + Math.sin(t * 20) * 0.1 + boost * 0.2;
    flameLight.intensity = 2.6 + Math.sin(t * 27) * 0.5 + boost * 3;

    // planets orbit
    planets.forEach(function (p, i) {
      var a = t * (0.5 + i * 0.12) + p.userData.o;
      p.position.set(Math.cos(a) * 2.2, Math.sin(a) * 2.2 * Math.sin(1.25) * 0.5, Math.sin(a) * 2.2 * 0.5);
      p.scale.setScalar(intro);
    });
    orbit.rotation.z = 0.25 + t * 0.05; orbit.scale.setScalar(intro);

    // exhaust: emit from the nozzle, travelling opposite to the rocket's nose
    stage.updateMatrixWorld(true);
    nz.set(0, -1.62, 0); rocket.localToWorld(nz);
    rocket.getWorldQuaternion(q); dn.set(0, -1, 0).applyQuaternion(q);
    var sc = stage.scale.x;
    spawnAcc += dt * (M / 0.9) * (1 + boost * 1.5);
    var made = 0;
    for (var i = 0; i < M; i++) {
      if (el[i] <= 0 && spawnAcc >= 1 && made < 12) {
        spawnAcc -= 1; made++; el[i] = 0.7 + Math.random() * 0.35;
        ep[i * 3] = nz.x + (Math.random() - 0.5) * 0.18 * sc; ep[i * 3 + 1] = nz.y + (Math.random() - 0.5) * 0.18 * sc; ep[i * 3 + 2] = nz.z + (Math.random() - 0.5) * 0.18 * sc;
        ev[i].copy(dn).multiplyScalar((2.4 + Math.random() * 1.4 + boost * 2) * sc);
        ev[i].x += (Math.random() - 0.5) * 0.7 * sc; ev[i].y += (Math.random() - 0.5) * 0.7 * sc;
      }
      if (el[i] > 0) {
        el[i] -= dt; var life = Math.max(el[i], 0) / 1.0;
        ep[i * 3] += ev[i].x * dt; ep[i * 3 + 1] += ev[i].y * dt; ep[i * 3 + 2] += ev[i].z * dt;
        var f = life * life;
        ec[i * 3] = 1.0 * f; ec[i * 3 + 1] = (0.35 + 0.4 * life) * f; ec[i * 3 + 2] = 0.12 * f;
      } else { ec[i * 3] = ec[i * 3 + 1] = ec[i * 3 + 2] = 0; }
    }
    eg.attributes.position.needsUpdate = true; eg.attributes.color.needsUpdate = true;

    stars.position.x = -mx * 0.4; stars.position.y = my * 0.25; stars.rotation.z = t * 0.004;
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
        st.iframe(HERO_HTML, height=340)
    else:
        import streamlit.components.v1 as components  # older Streamlit only

        components.html(HERO_HTML, height=340)


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

    tab_research, tab_plan, tab_pitch, tab_ai = st.tabs(
        ["Research", "30-Day Content Plan", "WhatsApp Pitch", "🤖 AI Agent"])

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

    with tab_ai:
        render_ai_tab(r)



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
