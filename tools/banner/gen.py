"""Profile banner generator: "One dot, three findings".

Sources (prompt-motion.com): #218 ultimaxbt "Orange dot motion system" (dot leaves the i,
squash/stretch jump, rides a spring graph, dot field), #135 Crux (number beside the chart),
#065 fionntobin (grid that fills while a number counts). All numbers are from the README.
Output: animated SVG (CSS keyframes only), one file per theme, 1200x360, 14 s loop,
last frame == first frame.

Run:  pip install fonttools brotli   then   python tools/banner/gen.py
Needs Google Chrome (set CHROME to its path if it isn't the Windows default); Chrome lays the
name out once so per-letter positions include real kerning. Fonts (OFL) download on first run
into tools/banner/fonts/. Writes assets/profile-banner-{light,dark}.svg; tools/banner/build/
gets a frame harness per theme (open harness-light.html#5.2 to see the frame at 5.2 s).
"""
import base64, io, json, math, os, subprocess, sys, urllib.request
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer
from fontTools import subset

HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(HERE, "fonts")
BUILD = os.path.join(HERE, "build")
ASSETS = os.path.normpath(os.path.join(HERE, "..", "..", "assets"))
CHROME = os.environ.get("CHROME", r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe")
FONT_URLS = {
    "Schibsted.ttf": "https://github.com/google/fonts/raw/main/ofl/schibstedgrotesk/SchibstedGrotesk%5Bwght%5D.ttf",
    "PlexMono-Medium.ttf": "https://github.com/google/fonts/raw/main/ofl/ibmplexmono/IBMPlexMono-Medium.ttf",
    "PlexMono-SemiBold.ttf": "https://github.com/google/fonts/raw/main/ofl/ibmplexmono/IBMPlexMono-SemiBold.ttf",
}

def ensure_fonts():
    os.makedirs(FONTS, exist_ok=True)
    for name, url in FONT_URLS.items():
        p = os.path.join(FONTS, name)
        if not os.path.exists(p):
            urllib.request.urlretrieve(url, p)
T = 14.0          # loop length, seconds
W, H = 1200, 360

PAL = {
    "light": dict(bg="#F4F1EA", ink="#15140F", mute="#77736A", faint="#D8D2C4", acc="#13A04F", edge="#E4DED1"),
    "dark":  dict(bg="#10151C", ink="#ECE7DC", mute="#8E949C", faint="#2B333D", acc="#3EDC81", edge="#222A33"),
}

# ---------------------------------------------------------------- text content
NAME = "Ausm\u0131n Deb"
NAME_SIZE, NAME_X, NAME_BASE = 124, 56, 196
SUB = "ASPIRING DATA ANALYST  \u00b7  PYTHON \u00b7 SQL \u00b7 EXCEL \u00b7 POWER BI"
PROOF = [("150K+", "loan records"), ("725K", "transactions"), ("10K", "bank customers")]
FLOOR_Y = 300

# ---------------------------------------------------------------- fonts
def font_b64(path, text, wght=None, out=None):
    f = TTFont(path)
    if wght is not None:
        f = instancer.instantiateVariableFont(f, {"wght": wght})
    opts = subset.Options(); opts.flavor = "woff2"; opts.layout_features = ["kern", "liga", "tnum"]
    opts.name_IDs = []; opts.notdef_outline = True
    s = subset.Subsetter(opts); s.populate(text=text); s.subset(f)
    buf = io.BytesIO(); f.flavor = "woff2"; f.recalcTimestamp = False; f.save(buf)   # same input -> same bytes
    return base64.b64encode(buf.getvalue()).decode()

# ---------------------------------------------------------------- timing helpers
def pct(t):
    return f"{max(0.0, min(100.0, t / T * 100)):.3f}%"

EASE = {
    "lin": "linear",
    "out": "cubic-bezier(.16,1,.3,1)",       # expo-ish out (entrances)
    "in": "cubic-bezier(.55,0,.8,.2)",       # exits
    "inout": "cubic-bezier(.65,0,.35,1)",
    "back": "cubic-bezier(.3,1.45,.5,1)",    # small overshoot
    "step": "step-end",
}

class Anim:
    def __init__(self):
        self.css = []; self.n = 0
    def add(self, stops, extra=""):
        """stops: [(t, 'css decls', ease_to_next)] -> returns class name."""
        self.n += 1; name = f"a{self.n}"
        stops = sorted(stops, key=lambda s: s[0])
        if stops[0][0] > 0: stops.insert(0, (0.0, stops[0][1], "lin"))
        if stops[-1][0] < T: stops.append((T, stops[-1][1], "lin"))
        body = []
        for t, decl, e in stops:
            body.append(f"{pct(t)}{{{decl};animation-timing-function:{EASE[e]}}}")
        self.css.append(f"@keyframes {name}{{{''.join(body)}}}")
        self.css.append(f".{name}{{animation:{name} {T}s infinite both;{extra}}}")
        return name

def tr(x=0, y=0): return f"transform:translate({x:.2f}px,{y:.2f}px)"
def sc(sx, sy=None): return f"transform:scale({sx:.4f},{(sx if sy is None else sy):.4f})"

def spring(tau, zeta=0.62, w=1.0):
    """Closed-form unit step response (0 -> 1)."""
    wd = w * math.sqrt(1 - zeta * zeta)
    return 1 - math.exp(-zeta * w * tau) * (math.cos(wd * tau) + zeta * w / wd * math.sin(wd * tau))

# ---------------------------------------------------------------- measuring
def measure(fonts_css):
    """Lay the name out in Chrome once, so per-letter positions include real kerning."""
    html = f"""<!doctype html><html><body><svg xmlns='http://www.w3.org/2000/svg' width='{W}' height='{H}'>
<style>{fonts_css} .n{{font-family:G;font-weight:800;font-size:{NAME_SIZE}px;letter-spacing:-0.02em}}
.m{{font-family:M;font-size:17px;letter-spacing:.12em}}</style>
<text id='n' class='n' x='{NAME_X}' y='{NAME_BASE}'>{NAME}</text>
<text id='s' class='m' x='0' y='100'>{SUB}</text></svg>
<script>document.fonts.ready.then(()=>{{const t=document.getElementById('n');const xs=[];
for(let i=0;i<t.getNumberOfChars();i++){{const p=t.getStartPositionOfChar(i);const e=t.getEndPositionOfChar(i);xs.push([p.x,e.x]);}}
const b=t.getBBox();const s=document.getElementById('s').getBBox();
document.body.setAttribute('data-m',JSON.stringify({{xs,b:[b.x,b.y,b.width,b.height],sub:s.width}}));}});</script></body></html>"""
    p = os.path.join(BUILD, "measure.html"); open(p, "w", encoding="utf-8").write(html)
    out = subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--virtual-time-budget=3000", "--dump-dom",
                          "file:///" + p.replace("\\", "/")], capture_output=True, text=True, encoding="utf-8").stdout
    raw = out.split("data-m=\"", 1)[1].split("\"", 1)[0].replace("&quot;", '"')
    return json.loads(raw)

def idot_geometry():
    """Centre and radius of the tittle of 'i' in Schibsted 800, in banner units."""
    from fontTools.pens.recordingPen import DecomposingRecordingPen
    from fontTools.pens.boundsPen import BoundsPen
    f = instancer.instantiateVariableFont(TTFont(os.path.join(FONTS, "Schibsted.ttf")), {"wght": 800})
    gs = f.getGlyphSet(); upm = f["head"].unitsPerEm
    rp = DecomposingRecordingPen(gs); gs["i"].draw(rp)
    contours, cur = [], []
    for op, args in rp.value:
        cur.append((op, args))
        if op in ("closePath", "endPath"): contours.append(cur); cur = []
    boxes = []
    for c in contours:
        bp = BoundsPen(gs)
        for op, args in c: getattr(bp, op)(*args)
        boxes.append(bp.bounds)
    dot = max(boxes, key=lambda b: b[3])       # the upper contour
    k = NAME_SIZE / upm
    cx = (dot[0] + dot[2]) / 2 * k; cy = (dot[1] + dot[3]) / 2 * k
    r = (dot[2] - dot[0]) / 2 * k
    adv = f["hmtx"]["i"][0] * k
    return cx, cy, r, adv

# ---------------------------------------------------------------- build
def build(theme, M, idot, fonts_css):
    P = PAL[theme]; A = Anim(); defs = []; body = []; clip_n = [0]

    def clip(x, y, w, h):
        clip_n[0] += 1; cid = f"c{clip_n[0]}"
        defs.append(f"<clipPath id='{cid}'><rect x='{x:.1f}' y='{y:.1f}' width='{w:.1f}' height='{h:.1f}'/></clipPath>")
        return cid

    def rise(inner, box, t_in, t_out, d_in=0.5, d_out=0.32, title=False):
        """Masked line reveal. Scene items: rise from below, leave upward.
        Title items: visible at t=0, leave downward, rise back at t_in."""
        x, y, w, h = box; cid = clip(x, y, w, h); dy = h + 4
        if title:
            cls = A.add([(t_out, tr(0, 0), "in"), (t_out + d_out, tr(0, dy), "lin"),
                         (t_in, tr(0, dy), "out"), (t_in + d_in, tr(0, 0), "lin")])
            base = ""
        else:
            cls = A.add([(t_in, tr(0, dy), "out"), (t_in + d_in, tr(0, 0), "lin"),
                         (t_out, tr(0, 0), "in"), (t_out + d_out, tr(0, -dy), "step"),
                         (t_out + d_out + 0.05, tr(0, dy), "lin")])
            base = f" transform='translate(0,{dy})'"
        body.append(f"<g clip-path='url(#{cid})'><g class='{cls}'{base}>{inner}</g></g>")

    def odometer(value, x, base, size, t_roll, t_end, t_out, cls_text, color):
        """Digits roll to their final value (Crux-style counter). Non-digits are static."""
        adv = size * 0.6; lh = size * 1.05
        top = base - size * 0.80; h = size * 0.92
        cid = clip(x - 4, top, adv * len(value) + 8, h)
        cols = []; digit_idx = [i for i, ch in enumerate(value) if ch.isdigit()]
        for i, ch in enumerate(value):
            cx = x + i * adv
            if ch.isdigit():
                d = int(ch); k = len(digit_idx) - digit_idx.index(i)   # right-most rolls most
                seq = list(range(10)) * k + list(range(d + 1))
                spans = "".join(f"<tspan x='{cx:.2f}' dy='{0 if j == 0 else lh:.2f}'>{n}</tspan>" for j, n in enumerate(seq))
                end = -(len(seq) - 1) * lh
                c = A.add([(t_roll, tr(0, 0), "out"), (t_end, tr(0, end), "lin"),
                           (t_out + 0.4, tr(0, end), "step"), (t_out + 0.45, tr(0, 0), "lin")])
                cols.append(f"<text class='{cls_text} {c}' y='{base:.2f}' fill='{color}'>{spans}</text>")
            else:
                cols.append(f"<text class='{cls_text}' x='{cx:.2f}' y='{base:.2f}' fill='{color}'>{ch}</text>")
        # the whole number rises in with the roll and leaves upward
        dy = h + 4
        # opacity drops once it has left: shifting a digit strip only reveals its neighbouring digits
        g = A.add([(t_roll - 0.05, tr(0, dy) + ";opacity:1", "out"), (t_roll + 0.35, tr(0, 0) + ";opacity:1", "lin"),
                   (t_out, tr(0, 0) + ";opacity:1", "in"), (t_out + 0.32, tr(0, -dy) + ";opacity:1", "step"),
                   (t_out + 0.37, tr(0, dy) + ";opacity:0", "lin")])
        body.append(f"<g clip-path='url(#{cid})'><g class='{g}' transform='translate(0,{dy})'>{''.join(cols)}</g></g>")

    # ---------------- background, floor rule with ticks (the chart axis in every scene)
    body.append(f"<rect width='{W}' height='{H}' rx='18' fill='{P['bg']}'/>")
    body.append(f"<rect x='.5' y='.5' width='{W-1}' height='{H-1}' rx='17.5' fill='none' stroke='{P['edge']}'/>")
    ticks = "".join(f"M{x} {FLOOR_Y}v5" for x in range(56, 1145, 33))
    body.append(f"<path d='M56 {FLOOR_Y}H1144{ticks}' stroke='{P['faint']}' stroke-width='1.5' fill='none'/>")

    # ---------------- TITLE CARD (0-2.0 s, back by 12.6 s)
    xs = M["xs"]; nb = M["b"]
    name_clip = clip(0, nb[1] - 30, W, nb[3] + 40)
    letters = []
    for i, ch in enumerate(NAME):
        if ch == " ": continue
        x0 = xs[i][0]
        t_out = 2.0 + i * 0.035; t_in = 11.95 + i * 0.045
        cls = A.add([(t_out, tr(0, 0), "in"), (t_out + 0.36, tr(0, 170), "lin"),
                     (t_in, tr(0, 170), "back"), (t_in + 0.55, tr(0, 0), "lin")])
        letters.append(f"<text class='nm {cls}' x='{x0:.2f}' y='{NAME_BASE}' fill='{P['ink']}'>{ch}</text>")
    body.append(f"<g clip-path='url(#{name_clip})'>{''.join(letters)}</g>")
    # the i's tittle position (the dot's home)
    i_index = NAME.index("\u0131")
    ix0, ix1 = xs[i_index]
    dcx, dcy, dr, dadv = idot_geometry()
    HOME = (ix0 + dcx * (ix1 - ix0) / dadv, NAME_BASE - dcy)
    R = dr

    rise(f"<text class='mono' x='{NAME_X+4}' y='252' fill='{P['mute']}'>{SUB}</text>",
         (NAME_X, 232, 900, 28), 12.35, 1.9, title=True)
    rise(f"<text class='mono sm' x='860' y='92' fill='{P['mute']}'>ANALYZED ACROSS PROJECTS</text>",
         (856, 76, 300, 22), 12.5, 1.85, title=True)
    for k, (num, lab) in enumerate(PROOF):
        y = 140 + k * 46
        rise(f"<text class='num md' x='860' y='{y}' fill='{P['ink']}'>{num}</text>"
             f"<text class='mono' x='962' y='{y}' fill='{P['mute']}'>{lab}</text>",
             (856, y - 30, 300, 40), 12.45 + k * 0.07, 1.8 + k * 0.05, title=True)

    # ---------------- SCENE B: credit risk (2.8-5.5 s)
    X0, X1 = 112, 700
    TARGET = FLOOR_Y - 0.6045 * 240          # 0-100 % maps to 300 -> 60
    # y labels + faint 50/100 guides
    guides = (f"<path d='M{X0} 60H{X1}M{X0} 180H{X1}' stroke='{P['faint']}' stroke-dasharray='2 6' fill='none'/>"
              f"<text class='mono xs' x='{X0-12}' y='64' text-anchor='end' fill='{P['mute']}'>100%</text>"
              f"<text class='mono xs' x='{X0-12}' y='184' text-anchor='end' fill='{P['mute']}'>50%</text>"
              f"<text class='mono xs' x='{X0-12}' y='304' text-anchor='end' fill='{P['mute']}'>0%</text>")
    g = A.add([(2.6, "opacity:0", "out"), (3.0, "opacity:1", "lin"), (5.2, "opacity:1", "in"), (5.5, "opacity:0", "lin")])
    body.append(f"<g class='{g}' opacity='0'>{guides}</g>")
    # target line (60.45 %), grows from the left
    g = A.add([(2.75, sc(0, 1), "out"), (3.2, sc(1, 1), "lin"), (5.2, sc(1, 1), "in"), (5.55, sc(0, 1), "lin")],
              "transform-box:fill-box;transform-origin:0 50%")
    body.append(f"<path class='{g}' transform='scale(0,1)' d='M{X0} {TARGET:.2f}H{X1+40}' stroke='{P['ink']}' stroke-width='1.5' stroke-dasharray='5 5' fill='none'/>")
    # spring trail: the same function moves the dot and draws the line (#218 build note 2)
    N = 40; TAU = 9.0; tB0, tB1 = 2.95, 4.05
    pts = []
    for j in range(N + 1):
        s = j / N; y = FLOOR_Y - (FLOOR_Y - TARGET) * spring(s * TAU, 0.62)
        pts.append((X0 + (X1 - X0) * s, y))
    seg = [0.0]
    for j in range(1, len(pts)):
        seg.append(seg[-1] + math.dist(pts[j - 1], pts[j]))
    L = seg[-1]
    d = "M" + " L".join(f"{x:.2f} {y:.2f}" for x, y in pts)
    st = [(tB0 + (tB1 - tB0) * j / N, f"stroke-dashoffset:{L - seg[j]:.2f}", "lin") for j in range(N + 1)]
    st += [(5.2, "stroke-dashoffset:0", "in"), (5.6, f"stroke-dashoffset:{-L:.2f}", "step"), (5.65, f"stroke-dashoffset:{L:.2f}", "lin")]
    g = A.add(st)
    body.append(f"<path class='{g}' d='{d}' stroke='{P['ink']}' stroke-width='2.5' stroke-linejoin='round' stroke-linecap='round' fill='none' stroke-dasharray='{L:.2f} {L+10:.2f}' stroke-dashoffset='{L:.2f}'/>")
    # sample marks along the curve, inked as the head passes (#218)
    for j in range(4, N, 4):
        x, y = pts[j]; tj = tB0 + (tB1 - tB0) * j / N
        g = A.add([(tj, sc(0), "back"), (tj + 0.18, sc(1), "lin"), (5.2 + j / N * 0.35, sc(1), "in"), (5.3 + j / N * 0.35, sc(0), "lin")],
                  "transform-box:fill-box;transform-origin:50% 50%")
        body.append(f"<circle class='{g}' transform='scale(0)' cx='{x:.2f}' cy='{y:.2f}' r='3.2' fill='{P['bg']}' stroke='{P['ink']}' stroke-width='1.8'/>")
    # right block
    BX = 760
    rise(f"<text class='mono sm' x='{BX}' y='92' fill='{P['acc']}'>01 \u00b7 CREDIT RISK</text>", (BX - 4, 76, 360, 22), 2.85, 5.2)
    odometer("60.45%", BX, 196, 92, 3.0, tB1, 5.22, "num xl", P["ink"])
    rise(f"<text class='gr' x='{BX}' y='244' fill='{P['ink']}'>default rate at 3+ late payments</text>", (BX - 4, 220, 400, 34), 3.35, 5.25)
    rise(f"<text class='mono sm' x='{BX}' y='334' fill='{P['mute']}'>150K+ LOAN RECORDS \u00b7 PYTHON \u00b7 PANDAS</text>", (BX - 4, 318, 400, 22), 3.5, 5.28)

    # ---------------- SCENE C: segmentation (5.6-8.9 s)
    GX, GY, PITCH, GR = 118, 86, 22, 7.0
    cells = [(c, r) for r in range(10) for c in range(10)]
    for idx, (c, r) in enumerate(cells):
        if idx == 0: continue                      # cell 0 is the accent dot itself
        x, y = GX + c * PITCH, GY + r * PITCH
        dist = math.hypot(c, r)
        t_in = 5.72 + dist * 0.045
        t_out = 8.75 + (9 - r) * 0.03 + abs(c - 4.5) * 0.012
        green = idx <= 18
        last = idx == 18                             # 18.8 % = 18 full + a 0.8 dot (area)
        s_full = math.sqrt(0.8) if last else 1.0
        g = A.add([(t_in, sc(0), "back"), (t_in + 0.3, sc(1), "lin"), (t_out, sc(1), "in"), (t_out + 0.25, sc(0), "lin")],
                  "transform-box:fill-box;transform-origin:50% 50%")
        if green:
            tg = 6.38 + idx * 0.032
            f = A.add([(tg, f"fill:{P['faint']}", "lin"), (tg + 0.08, f"fill:{P['acc']}", "lin"),
                       (t_out + 0.25, f"fill:{P['acc']}", "step"), (t_out + 0.3, f"fill:{P['faint']}", "lin")])
            rr = GR * s_full if last else GR
            body.append(f"<g class='{g}' transform='scale(0)'><circle class='{f}' cx='{x}' cy='{y}' r='{rr:.2f}' fill='{P['faint']}'/></g>")
        else:
            body.append(f"<circle class='{g}' transform='scale(0)' cx='{x}' cy='{y}' r='{GR}' fill='{P['faint']}'/>")
    CX = 380; BAR_W = 1144 - CX
    rise(f"<text class='mono sm' x='{CX}' y='78' fill='{P['acc']}'>02 \u00b7 SEGMENTATION</text>", (CX - 4, 62, 360, 22), 5.8, 8.7)
    odometer("18.8%", CX, 150, 64, 6.38, 6.98, 8.72, "num lg", P["ink"])
    rise(f"<text class='gr' x='{CX + 5 * 64 * 0.6 + 18:.1f}' y='150' fill='{P['ink']}'>of customers, the Champions</text>",
         (CX + 5 * 64 * 0.6 + 14, 124, 420, 36), 6.5, 8.74)
    # revenue bar: track, then the 71 % fill
    g = A.add([(6.05, sc(0, 1), "out"), (6.5, sc(1, 1), "lin"), (8.75, sc(1, 1), "in"), (9.05, sc(0, 1), "lin")],
              "transform-box:fill-box;transform-origin:0 50%")
    body.append(f"<rect class='{g}' transform='scale(0,1)' x='{CX}' y='178' width='{BAR_W}' height='22' rx='3' fill='{P['faint']}'/>")
    g = A.add([(7.05, sc(0, 1), "out"), (7.85, sc(1, 1), "lin"), (8.75, sc(1, 1), "in"), (9.0, sc(0, 1), "lin")],
              "transform-box:fill-box;transform-origin:0 50%")
    body.append(f"<rect class='{g}' transform='scale(0,1)' x='{CX}' y='178' width='{BAR_W * 0.71:.1f}' height='22' rx='3' fill='{P['acc']}'/>")
    odometer("71%", CX, 268, 64, 7.05, 7.85, 8.78, "num lg", P["ink"])
    rise(f"<text class='gr' x='{CX + 3 * 64 * 0.6 + 18:.1f}' y='268' fill='{P['ink']}'>of revenue</text>",
         (CX + 3 * 64 * 0.6 + 14, 242, 300, 36), 7.2, 8.8)
    rise(f"<text class='mono sm' x='{CX}' y='334' fill='{P['mute']}'>RFM + K-MEANS \u00b7 5,350 CUSTOMERS \u00b7 725K TRANSACTIONS</text>",
         (CX - 4, 318, 560, 22), 6.6, 8.82)

    # ---------------- SCENE D: churn (9.0-11.7 s)
    B1X, B2X, BW, BH = 150, 262, 84, 80
    tO0, tO1, tG0, tG1 = 9.25, 9.8, 9.45, 10.35
    def bar(x, h, t0, t1, fill, t_out):
        st = []
        for j in range(17):
            s = j / 16; st.append((t0 + (t1 - t0) * s, sc(1, spring(s * 9.0, 0.6)), "lin"))
        st += [(t_out, sc(1, 1), "in"), (t_out + 0.3, sc(1, 0), "lin")]
        g = A.add(st, "transform-box:fill-box;transform-origin:50% 100%")
        body.append(f"<rect class='{g}' transform='scale(1,0)' x='{x}' y='{FLOOR_Y - h}' width='{BW}' height='{h}' fill='{fill}'/>")
    bar(B1X, BH, tO0, tO1, P["faint"], 11.35)
    bar(B2X, 2 * BH, tG0, tG1, P["ink"], 11.42)
    rise(f"<text class='mono xs' x='{B1X + BW/2}' y='322' text-anchor='middle' fill='{P['mute']}'>OTHER REGIONS</text>"
         f"<text class='mono xs' x='{B2X + BW/2}' y='322' text-anchor='middle' fill='{P['ink']}'>GERMANY</text>",
         (100, 308, 320, 20), 9.5, 11.35)
    DX = 440
    rise(f"<text class='mono sm' x='{DX}' y='92' fill='{P['acc']}'>03 \u00b7 CUSTOMER CHURN</text>", (DX - 4, 76, 360, 22), 9.3, 11.3)
    rise(f"<text class='num xxl' x='{DX - 6}' y='236' fill='{P['ink']}'>2\u00d7</text>", (DX - 8, 120, 200, 128), 10.0, 11.33, d_in=0.6)
    rise(f"<text class='gr lg' x='{DX + 190}' y='176' fill='{P['ink']}'>churn rate in Germany</text>", (DX + 186, 144, 520, 42), 10.12, 11.36)
    rise(f"<text class='gr lg' x='{DX + 190}' y='222' fill='{P['mute']}'>vs every other region</text>", (DX + 186, 190, 520, 42), 10.22, 11.39)
    rise(f"<text class='mono sm' x='{DX}' y='334' fill='{P['mute']}'>10K BANK CUSTOMERS \u00b7 EDA \u00b7 NEXT.JS DASHBOARD</text>", (DX - 4, 318, 520, 22), 10.3, 11.4)

    # ---------------- THE DOT: one element through the whole film
    pos = []
    def hold(t, p): pos.append((t, p))
    def arc(t0, t1, p0, p1, apex, n=14):
        for j in range(n + 1):
            s = j / n; x = p0[0] + (p1[0] - p0[0]) * s
            yl = p0[1] + (p1[1] - p0[1]) * s
            y = yl - apex * 4 * s * (1 - s)
            pos.append((t0 + (t1 - t0) * s, (x, y)))
    hold(0, HOME); hold(2.12, HOME)
    START_B = (X0, FLOOR_Y - R)
    arc(2.18, 2.82, HOME, START_B, 70)
    for j in range(N + 1):                                    # rides the spring graph
        x, y = pts[j]; pos.append((tB0 + (tB1 - tB0) * j / N, (x, y - (R if j == 0 else 0))))
    END_B = (pts[-1][0], pts[-1][1])
    hold(5.18, END_B)
    CELL0 = (GX, GY)
    arc(5.25, 5.75, END_B, CELL0, 60)
    hold(9.0, CELL0)
    TOP_G0 = (B2X + BW / 2, FLOOR_Y - R)
    arc(9.0, tG0, CELL0, TOP_G0, 40, n=10)
    for j in range(17):                                       # rides the Germany bar
        s = j / 16; pos.append((tG0 + (tG1 - tG0) * s, (TOP_G0[0], FLOOR_Y - 2 * BH * spring(s * 9.0, 0.6) - R)))
    TOP_G = (TOP_G0[0], FLOOR_Y - 2 * BH - R)
    hold(11.5, TOP_G)
    arc(11.62, 12.3, TOP_G, HOME, 90)
    hold(T, HOME)
    st = []; last_t = -1
    for t, (x, y) in pos:
        if t <= last_t: t = last_t + 0.001
        st.append((t, tr(x, y), "lin")); last_t = t
    gpos = A.add(st)
    # squash & stretch: anticipation, take-off stretch, landing squash, cell shrink
    k = GR / R
    sq = A.add([(1.98, sc(1), "inout"), (2.12, sc(1.28, 0.74), "out"), (2.24, sc(0.84, 1.2), "inout"), (2.6, sc(1), "lin"),
                (2.8, sc(1), "out"), (2.86, sc(1.3, 0.72), "out"), (3.02, sc(1), "lin"),
                (5.2, sc(1), "out"), (5.3, sc(0.86, 1.16), "inout"), (5.7, sc(1), "out"), (5.78, sc(1.25 * k, 0.75 * k), "out"), (5.95, sc(k), "lin"),
                (8.95, sc(k), "out"), (9.12, sc(1), "lin"), (9.42, sc(1), "out"), (9.48, sc(1.3, 0.72), "out"), (9.62, sc(1), "lin"),
                (11.48, sc(1), "inout"), (11.6, sc(1.26, 0.76), "out"), (11.72, sc(0.84, 1.2), "inout"), (12.1, sc(1), "lin"),
                (12.28, sc(1), "out"), (12.34, sc(1.3, 0.74), "out"), (12.5, sc(1), "lin")],
               "transform-box:fill-box;transform-origin:50% 50%")
    body.append(f"<g class='{gpos}' transform='translate({HOME[0]:.2f},{HOME[1]:.2f})'><circle class='{sq}' r='{R:.2f}' fill='{P['acc']}'/></g>")

    css = f"""{fonts_css}
.nm{{font-family:G;font-weight:800;font-size:{NAME_SIZE}px;letter-spacing:-0.02em}}
.gr{{font-family:G;font-weight:600;font-size:26px;letter-spacing:-0.01em}}
.gr.lg{{font-size:34px;font-weight:700}}
.mono{{font-family:M;font-size:17px;letter-spacing:.12em}}
.mono.sm{{font-size:14px;letter-spacing:.14em}}
.mono.xs{{font-size:12px;letter-spacing:.12em}}
.num{{font-family:N;letter-spacing:0}}
.num.md{{font-size:30px}}.num.lg{{font-size:64px}}.num.xl{{font-size:92px}}.num.xxl{{font-size:150px;letter-spacing:-0.04em}}
{''.join(A.css)}
@media (prefers-reduced-motion: reduce){{*{{animation:none!important}}}}"""
    svg = (f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 {W} {H}' width='{W}' height='{H}' role='img' aria-labelledby='t d'>"
           f"<title id='t'>Ausmin Deb, Data Analyst</title>"
           f"<desc id='d'>A green dot leaves the i in Ausmin and becomes the data from three projects: a 60.45% default rate at 3+ late payments, "
           f"18.8% of customers driving 71% of revenue, and churn in Germany at twice other regions. It returns to the i.</desc>"
           f"<style>{css}</style><defs>{''.join(defs)}</defs>{''.join(body)}</svg>")
    return svg

def main():
    chars_name = NAME + "Aim"
    chars_gr = "default rate at 3+ late payments of customers, the Champions of revenue churn rate in Germany vs every other region"
    chars_mono = SUB + "ANALYZED ACROSS PROJECTS" + "".join(l for _, l in PROOF) + "0123456789%+.\u00b7 " \
        + "01 CREDIT RISK 150K+ LOAN RECORDS PYTHON PANDAS 02 SEGMENTATION RFM K-MEANS 5,350 CUSTOMERS 725K TRANSACTIONS" \
        + "03 CUSTOMER CHURN 10K BANK EDA NEXT.JS DASHBOARD OTHER REGIONS GERMANY"
    ensure_fonts(); os.makedirs(BUILD, exist_ok=True)
    fdir = FONTS
    g = font_b64(os.path.join(fdir, "Schibsted.ttf"), chars_name + chars_gr, wght=800)
    g6 = font_b64(os.path.join(fdir, "Schibsted.ttf"), chars_gr, wght=650)
    m = font_b64(os.path.join(fdir, "PlexMono-Medium.ttf"), chars_mono)
    n = font_b64(os.path.join(fdir, "PlexMono-SemiBold.ttf"), "0123456789%+.K\u00d7")
    fonts_css = (f"@font-face{{font-family:G;font-weight:700 900;src:url(data:font/woff2;base64,{g}) format('woff2')}}"
                 f"@font-face{{font-family:G;font-weight:400 650;src:url(data:font/woff2;base64,{g6}) format('woff2')}}"
                 f"@font-face{{font-family:M;src:url(data:font/woff2;base64,{m}) format('woff2')}}"
                 f"@font-face{{font-family:N;src:url(data:font/woff2;base64,{n}) format('woff2')}}")
    M = measure(fonts_css)
    json.dump(M, open(os.path.join(BUILD, "measure.json"), "w"))
    out = BUILD
    for theme in PAL:
        svg = build(theme, M, None, fonts_css)
        open(os.path.join(ASSETS, f"profile-banner-{theme}.svg"), "w", encoding="utf-8").write(svg)
        # frame harness: inline the svg, seek every animation to #t
        html = ("<!doctype html><html><head><style>html,body{margin:0;background:#888}</style></head><body>" + svg +
                "<script>function seek(t){document.getAnimations().forEach(a=>{a.pause();a.currentTime=t*1000;});}"
                "const t=parseFloat((location.hash||'#0').slice(1));document.fonts.ready.then(()=>{seek(t);document.body.dataset.ok=1;});</script></body></html>")
        open(os.path.join(out, f"harness-{theme}.html"), "w", encoding="utf-8").write(html)
        print(theme, len(svg) // 1024, "KB")
    print("name bbox", M["b"])

if __name__ == "__main__":
    main()
