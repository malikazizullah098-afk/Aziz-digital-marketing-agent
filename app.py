
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
# 3D hero banner (Three.js, PBR glass + chrome). Static markup only: no user input is injected.
# ---------------------------------------------------------------------------
HERO_HTML = """
<style>
  *{box-sizing:border-box}
  html,body{margin:0;height:100%;background:transparent;font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
  #wrap{position:relative;height:100%;border-radius:20px;overflow:hidden;
        background:
          radial-gradient(60% 90% at 78% 45%,rgba(124,92,255,.35) 0%,rgba(124,92,255,0) 70%),
          radial-gradient(40% 60% at 95% 100%,rgba(0,255,200,.18) 0%,rgba(0,255,200,0) 70%),
          linear-gradient(135deg,#0d0a26 0%,#14103a 50%,#080718 100%);
        box-shadow:inset 0 0 0 1px rgba(255,255,255,.07),0 20px 60px rgba(40,20,120,.35)}
  canvas{position:absolute;inset:0;width:100%;height:100%;display:block;opacity:0;transition:opacity 1.2s ease}
  canvas.on{opacity:1}
  .txt{position:absolute;left:34px;top:50%;transform:translateY(-50%);color:#fff;max-width:50%;z-index:2}
  .eyebrow{display:inline-flex;align-items:center;gap:8px;padding:6px 14px;border-radius:999px;font-size:14px;
        letter-spacing:.4px;color:#9dffd2;background:rgba(120,255,190,.10);border:1px solid rgba(125,255,191,.30);
        backdrop-filter:blur(8px)}
  .dot{width:7px;height:7px;border-radius:50%;background:#5dffb0;box-shadow:0 0 10px #5dffb0;animation:p 1.6s infinite}
  @keyframes p{50%{opacity:.35}}
  h1{margin:14px 0 10px;font-size:clamp(30px,4.8vw,56px);line-height:1.1;letter-spacing:-.8px;font-weight:800;
        background:linear-gradient(90deg,#fff 0%,#cfc6ff 45%,#7dffd0 100%);-webkit-background-clip:text;background-clip:text;
        color:transparent}
  p{margin:0;color:#d6d2f5;font-size:clamp(15px,1.9vw,20px);line-height:1.45}
  .chips{display:flex;flex-wrap:wrap;gap:8px;margin-top:16px}
  .chip{padding:7px 14px;border-radius:10px;font-size:14px;color:#e9e6ff;background:rgba(255,255,255,.06);
        border:1px solid rgba(255,255,255,.12);backdrop-filter:blur(10px)}
  @media(max-width:640px){.txt{left:18px;right:18px;max-width:none;top:18px;transform:none}h1{margin:10px 0 6px}.chips{display:none}}
</style>
<div id="wrap">
  <canvas id="c"></canvas>
  <div class="txt">
    <span class="eyebrow"><span class="dot"></span>Cloud LIVE</span>
    <h1>Aziz AI Marketing<br>Cloud Agent</h1>
    <p>Research, 30-day content plan aur WhatsApp pitch, ek minute mein.</p>
    <div class="chips"><span class="chip">11 Niches</span><span class="chip">30-Day Plan</span><span class="chip">WhatsApp Pitch</span></div>
  </div>
</div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
<script>
(function () {
  if (typeof THREE === 'undefined') { return; }            // CDN blocked: gradient banner only
  var wrap = document.getElementById('wrap'), canvas = document.getElementById('c'), renderer;
  try { renderer = new THREE.WebGLRenderer({ canvas: canvas, alpha: true, antialias: true, powerPreference: 'high-performance' }); }
  catch (e) { return; }                                    // no WebGL: gradient banner only

  var small = Math.min(window.screen.width || 1000, window.innerWidth) < 700;
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, small ? 1.5 : 2));
  renderer.outputEncoding = THREE.sRGBEncoding;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.15;

  var scene = new THREE.Scene();
  var camera = new THREE.PerspectiveCamera(40, 1, 0.1, 100);
  camera.position.set(0, 0, 6.3);

  // ---- Studio environment: gives real reflections on glass and chrome --------
  (function buildEnv() {
    var env = new THREE.Scene();
    env.add(new THREE.Mesh(new THREE.SphereGeometry(20, 32, 16),
      new THREE.MeshBasicMaterial({ color: 0x0b0a22, side: THREE.BackSide })));
    function panel(color, intensity, w, h, x, y, z) {
      var m = new THREE.Mesh(new THREE.PlaneGeometry(w, h),
        new THREE.MeshBasicMaterial({ color: new THREE.Color(color).multiplyScalar(intensity), side: THREE.DoubleSide }));
      m.position.set(x, y, z); m.lookAt(0, 0, 0); env.add(m);
    }
    panel(0xffffff, 6, 10, 3, 0, 12, 4);        // top softbox
    panel(0x66ffd0, 5, 3, 10, 12, 0, 2);        // teal strip right
    panel(0xff5fd2, 4, 3, 10, -12, 2, 2);       // magenta strip left
    panel(0x7c5cff, 4, 12, 3, 0, -10, 6);       // violet floor bounce
    panel(0xffffff, 3, 5, 5, 0, 2, 14);         // front fill
    var pm = new THREE.PMREMGenerator(renderer);
    scene.environment = pm.fromScene(env, 0.02).texture;
    pm.dispose();
  })();

  // ---- Lights -----------------------------------------------------------------
  scene.add(new THREE.AmbientLight(0x6655ff, 0.25));
  var key = new THREE.DirectionalLight(0xffffff, 1.6); key.position.set(4, 5, 6); scene.add(key);
  var teal = new THREE.PointLight(0x4dffc9, 2.2, 30); teal.position.set(5, -1, 3); scene.add(teal);
  var pink = new THREE.PointLight(0xff4fc8, 2.0, 30); pink.position.set(-5, 2, 3); scene.add(pink);

  var group = new THREE.Group(); scene.add(group);

  // ---- Glow sprite texture ----------------------------------------------------
  function glowTex(inner, outer) {
    var c = document.createElement('canvas'); c.width = c.height = 128;
    var g = c.getContext('2d'), gr = g.createRadialGradient(64, 64, 0, 64, 64, 64);
    gr.addColorStop(0, inner); gr.addColorStop(0.35, outer); gr.addColorStop(1, 'rgba(0,0,0,0)');
    g.fillStyle = gr; g.fillRect(0, 0, 128, 128);
    return new THREE.CanvasTexture(c);
  }

  // ---- Core: liquid glass shell + glowing nucleus -------------------------------
  var SEG = small ? 48 : 80;
  var shellGeo = new THREE.SphereGeometry(1.35, SEG, SEG);
  var base = shellGeo.attributes.position.array.slice();
  var shell = new THREE.Mesh(shellGeo, new THREE.MeshPhysicalMaterial({
    color: 0x4a2ee0, metalness: 0.25, roughness: 0.06, transmission: 0.62, thickness: 2.0, ior: 1.5,
    clearcoat: 1, clearcoatRoughness: 0.03, envMapIntensity: 1.6, attenuationColor: new THREE.Color(0x3b1fd0),
    attenuationDistance: 1.4, transparent: true
  }));
  group.add(shell);

  var nucleus = new THREE.Mesh(new THREE.IcosahedronGeometry(0.62, 2),
    new THREE.MeshStandardMaterial({ color: 0x0b2a2a, emissive: 0x19e6a8, emissiveIntensity: 1.0, metalness: 0.2, roughness: 0.35, flatShading: true }));
  group.add(nucleus);

  var lattice = new THREE.Mesh(new THREE.IcosahedronGeometry(0.98, 1),
    new THREE.MeshBasicMaterial({ color: 0x9ffff0, wireframe: true, transparent: true, opacity: 0.28 }));
  group.add(lattice);

  var halo = new THREE.Sprite(new THREE.SpriteMaterial({ map: glowTex('rgba(150,120,255,.9)', 'rgba(110,70,255,.25)'),
    blending: THREE.AdditiveBlending, depthWrite: false, transparent: true, opacity: 0.8 }));
  halo.scale.set(7.5, 7.5, 1); halo.position.z = -1.2; group.add(halo);

  // ---- Chrome / gold rings ------------------------------------------------------
  function ring(radius, tube, color, rx, ry) {
    var m = new THREE.Mesh(new THREE.TorusGeometry(radius, tube, 32, 160),
      new THREE.MeshPhysicalMaterial({ color: color, metalness: 1, roughness: 0.14, clearcoat: 1, envMapIntensity: 1.8 }));
    m.rotation.set(rx, ry, 0); group.add(m); return m;
  }
  var ringA = ring(1.95, 0.035, 0xe9e6ff, 1.2, 0.2);
  var ringB = ring(2.35, 0.025, 0x6dffd0, 0.4, 1.0);
  var ringC = ring(2.75, 0.018, 0xffc46b, 2.1, 0.6);

  // ---- Orbiting gems (stand for platforms) -----------------------------------------
  var gemColors = [0x4dffc9, 0xff5fd2, 0xffc46b, 0x7cc4ff, 0xb59cff];
  var gems = gemColors.map(function (col, i) {
    var m = new THREE.Mesh(new THREE.OctahedronGeometry(0.2, 0),
      new THREE.MeshPhysicalMaterial({ color: col, emissive: col, emissiveIntensity: 0.55, metalness: 0.3, roughness: 0.12, clearcoat: 1 }));
    m.userData = { r: 2.2 + (i % 3) * 0.4, s: 0.5 + i * 0.13, o: i * 1.26, tilt: 0.35 * (i - 2) };
    group.add(m); return m;
  });

  // ---- Particles --------------------------------------------------------------------
  var N = small ? 160 : 320, pos = new Float32Array(N * 3), seed = new Float32Array(N);
  for (var i = 0; i < N; i++) {
    pos[i * 3] = (Math.random() - 0.5) * 18; pos[i * 3 + 1] = (Math.random() - 0.5) * 9; pos[i * 3 + 2] = (Math.random() - 0.5) * 10 - 2;
    seed[i] = Math.random() * 6.28;
  }
  var pg = new THREE.BufferGeometry(); pg.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  var dust = new THREE.Points(pg, new THREE.PointsMaterial({ map: glowTex('rgba(255,255,255,1)', 'rgba(180,170,255,.4)'),
    size: 0.16, transparent: true, opacity: 0.85, depthWrite: false, blending: THREE.AdditiveBlending }));
  scene.add(dust);

  // ---- Interaction ---------------------------------------------------------------------
  var tx = 0, ty = 0, cx = 0, cy = 0;
  function aim(x, y) { tx = (x / window.innerWidth - 0.5) * 2; ty = (y / window.innerHeight - 0.5) * 2; }
  window.addEventListener('mousemove', function (e) { aim(e.clientX, e.clientY); });
  window.addEventListener('touchmove', function (e) { if (e.touches[0]) aim(e.touches[0].clientX, e.touches[0].clientY); }, { passive: true });

  function resize() {
    var w = wrap.clientWidth, h = wrap.clientHeight;
    renderer.setSize(w, h, false);
    camera.aspect = w / h; camera.updateProjectionMatrix();
    var wide = w > 640;
    group.position.x = wide ? 3.35 : 1.0; group.position.y = wide ? 0 : -1.45;
    group.scale.setScalar(wide ? 0.82 : 0.42);
  }
  window.addEventListener('resize', resize); resize();

  // ---- Animation ---------------------------------------------------------------------------
  var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var visible = true, running = false, t0 = performance.now();
  if ('IntersectionObserver' in window) {
    new IntersectionObserver(function (en) { visible = en[0].isIntersecting; if (visible) start(); }).observe(wrap);
  }
  function ease(x) { return 1 - Math.pow(1 - x, 3); }

  function wobble(t) {
    var p = shellGeo.attributes.position.array;
    for (var i = 0; i < p.length; i += 3) {
      var x = base[i], y = base[i + 1], z = base[i + 2];
      var d = 1 + 0.07 * Math.sin(x * 2.1 + t * 1.1) * Math.cos(y * 2.3 - t * 0.9) + 0.05 * Math.sin(z * 3.0 + t * 1.4);
      p[i] = x * d; p[i + 1] = y * d; p[i + 2] = z * d;
    }
    shellGeo.attributes.position.needsUpdate = true;
    shellGeo.computeVertexNormals();
  }

  function frame(now) {
    running = false;
    var t = reduce ? 10 : (now - t0) / 1000, intro = ease(Math.min(t / 1.6, 1));
    cx += (tx - cx) * 0.05; cy += (ty - cy) * 0.05;

    group.rotation.y = cx * 0.45 + Math.sin(t * 0.4) * 0.12;
    group.rotation.x = cy * 0.25;
    shell.scale.setScalar(0.55 + 0.45 * intro);
    shell.rotation.y = t * 0.12;
    nucleus.rotation.set(t * 0.5, t * 0.7, 0);
    nucleus.material.emissiveIntensity = 0.9 + Math.sin(t * 2.2) * 0.3;
    lattice.rotation.set(-t * 0.25, t * 0.2, 0);
    halo.material.opacity = 0.5 + Math.sin(t * 1.6) * 0.1;
    ringA.rotation.z = t * 0.35; ringB.rotation.z = -t * 0.28; ringC.rotation.z = t * 0.2;
    ringA.scale.setScalar(intro); ringB.scale.setScalar(intro); ringC.scale.setScalar(intro);

    gems.forEach(function (g) {
      var u = g.userData, a = t * u.s + u.o;
      g.position.set(Math.cos(a) * u.r, Math.sin(a * 0.9) * u.r * 0.35 + u.tilt, Math.sin(a) * u.r * 0.6);
      g.rotation.set(t * 1.2, t * 0.9, 0); g.scale.setScalar(intro);
    });
    var pa = pg.attributes.position.array;
    for (var i = 0; i < N; i++) { pa[i * 3 + 1] += Math.sin(t * 0.6 + seed[i]) * 0.0016; }
    pg.attributes.position.needsUpdate = true;
    dust.rotation.y = t * 0.02;

    wobble(t);
    camera.position.x = cx * 0.5; camera.position.y = -cy * 0.3; camera.lookAt(0, 0, 0);
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
