"""Finalised English templates (8). Each builder returns a randomised Document.

invoice | receipt | certificate | application_form | business_letter | restaurant_menu | event_flyer | mobile_settings
"""

from __future__ import annotations

import random

from .document import (Background, Band, Document, Obj, Rule, add_block, FAMILIES_BY_CLASS)

W, H = 768, 1024

FIRST = ["Aarav", "Priya", "Rohan", "Ananya", "Vikram", "Meera", "Arjun", "Kavya", "Daniel", "Sophia",
         "Liam", "Emma", "Noah", "Olivia", "Ethan", "Grace", "Karthik", "Divya", "Samuel", "Nisha"]
LAST = ["Sharma", "Iyer", "Reddy", "Nair", "Patel", "Kumar", "Menon", "Johnson", "Williams", "Brown",
        "Garcia", "Miller", "Davis", "Fernandes", "Rao", "Gupta", "Singh", "Thomas", "Clarke", "Bose"]
COMPANIES = ["Northwind Traders", "Bluepeak Systems", "Crescent Labs", "Vertex Retail", "Greenleaf Foods",
             "Orbit Logistics", "Lumen Analytics", "Silverline Motors", "Harbor Tech", "Maple Office Supply",
             "Nova Electronics", "Summit Consulting", "Riverstone Media", "Apex Hardware", "Cobalt Software"]
CITIES = ["Chennai", "Bengaluru", "Hyderabad", "Mumbai", "Pune", "Delhi", "Kolkata", "Vellore", "Seoul",
          "Austin", "London", "Toronto", "Singapore", "Sydney", "Dublin"]
STREETS = ["Lake View Road", "Park Avenue", "Station Street", "Temple Road", "Hill Crescent", "Market Lane",
           "Gandhi Nagar", "MG Road", "Oak Street", "River Walk"]
PRODUCTS = [("Wireless Mouse", 499), ("USB-C Cable", 199), ("Laptop Stand", 1299), ("Bluetooth Speaker", 1999),
            ("Mechanical Keyboard", 3499), ("HD Webcam", 2299), ("Desk Lamp", 899), ("Power Bank", 1599),
            ("Noise Cancelling Headset", 4999), ("Monitor Arm", 2799), ("Smart Plug", 749), ("SSD 1TB", 5899),
            ("Router AX3000", 4299), ("Phone Case", 399), ("Screen Protector", 249), ("Charging Dock", 1199)]
DISHES = [("Masala Dosa", "Crisp rice crepe with spiced potato and coconut chutney", 120),
          ("Paneer Tikka", "Char-grilled cottage cheese with mint dip", 240),
          ("Margherita Pizza", "San Marzano tomato, basil and fresh mozzarella", 320),
          ("Caesar Salad", "Romaine, parmesan, croutons and house dressing", 210),
          ("Butter Chicken", "Slow-cooked tomato gravy with cream and fenugreek", 360),
          ("Veg Biryani", "Fragrant basmati layered with seasonal vegetables", 260),
          ("Grilled Salmon", "Lemon butter, herbed potatoes and greens", 540),
          ("Mushroom Risotto", "Arborio rice, porcini and parmesan", 380),
          ("Chocolate Brownie", "Warm brownie with vanilla ice cream", 180),
          ("Mango Lassi", "Chilled yoghurt drink with Alphonso mango", 90),
          ("Filter Coffee", "Traditional South Indian decoction coffee", 60),
          ("Tomato Soup", "Roasted tomato, basil oil and croutons", 140)]
EVENTS = ["Tech Innovation Summit", "Annual Science Fair", "Startup Pitch Night", "AI Research Symposium",
          "Community Music Festival", "Open Source Hack Day", "Design Thinking Workshop", "Robotics Expo"]
SETTINGS = [("Wi-Fi", "Connected to HomeNet_5G"), ("Bluetooth", "Galaxy Buds Pro"), ("Mobile data", "4G LTE"),
            ("Display", "Adaptive brightness on"), ("Battery", "82% - about 14h left"),
            ("Notifications", "Do not disturb off"), ("Sounds and vibration", "Ring mode"),
            ("Location", "On - high accuracy"), ("Security and privacy", "Screen lock: PIN"),
            ("Storage", "64.2 GB of 128 GB used"), ("Software update", "Last checked today"),
            ("Accessibility", "Large text off")]

PAPER = [(250, 249, 245), (252, 250, 242), (246, 244, 238), (255, 253, 248), (244, 246, 248), (248, 245, 236)]
INKS = [(25, 25, 30), (35, 40, 55), (45, 35, 30), (20, 30, 45)]
ACCENTS = [(178, 34, 52), (20, 90, 170), (0, 120, 90), (190, 100, 0), (110, 40, 150), (200, 50, 100)]


def _name(r):
    return f"{r.choice(FIRST)} {r.choice(LAST)}"


def _date(r):
    return f"{r.randint(1, 28):02d} {r.choice(['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'])} 2026"


def _fam(r, cls=None):
    cls = cls or r.choice(["sans", "sans", "serif"])
    return r.choice(FAMILIES_BY_CLASS[cls])


def _bg(r, base=None, texture=None, bands=None, gradient=None):
    return Background(base or r.choice(PAPER), texture if texture is not None else r.uniform(4.0, 8.0),
                      r.randint(0, 10**9), bands or [], gradient)


# ------------------------------------------------------------------ templates
def invoice(r: random.Random) -> Document:
    acc, ink, fam = r.choice(ACCENTS), r.choice(INKS), _fam(r)
    d = Document("invoice", W, H, _bg(r, bands=[Band(0, 0, W, 120, acc)]))
    co = r.choice(COMPANIES)
    d.objects.append(Obj("logo", 40, 22, 76, 76, (255, 255, 255), r.randint(0, 10**9), co[0]))
    add_block(d, "title", "INVOICE", 140, 34, 360, "title", r.uniform(34, 40), fam, color=(255, 255, 255))
    add_block(d, "company", f"**{co}**", 140, 82, 400, "small", 15, fam, color=(240, 240, 240))
    y = 150
    y = add_block(d, "meta", [f"Invoice No: **INV-2026-{r.randint(1000, 9999)}**", f"Date: {_date(r)}",
                              f"Due: [[{_date(r)}]]"], 40, y, 320, "body", 15, fam, color=ink)
    add_block(d, "billto", ["**Bill To**", _name(r), f"{r.randint(1, 300)} {r.choice(STREETS)}", r.choice(CITIES)],
              440, 150, 290, "body", 15, fam, color=ink)
    y = 290
    d.rules.append(Rule(40, y, W - 40, y, 2, ink))
    mono = r.choice(FAMILIES_BY_CLASS["mono"])
    add_block(d, "th", f"**{'Item':<34}{'Qty':>4}{'Price':>12}{'Amount':>14}**", 40, y + 10, 690,
              "heading", 14, mono, color=ink, pre=True)
    y += 44
    d.rules.append(Rule(40, y, W - 40, y, 1, (150, 150, 150)))
    items = r.sample(PRODUCTS, r.randint(4, 7))
    total = 0
    rows = []
    for name, price in items:
        q = r.randint(1, 4)
        total += q * price
        rows.append(f"{name:<34}{q:>4}{price:>12,.2f}{q * price:>14,.2f}")
    y = add_block(d, "items", rows, 40, y + 10, 690, "body", 14, mono, color=ink, line_gap=1.7, pre=True) + 10
    d.rules.append(Rule(40, y, W - 40, y, 2, ink))
    gst = round(total * 0.18, 2)
    add_block(d, "totals", [f"Subtotal: Rs. {total:,.2f}", f"GST (18%): Rs. {gst:,.2f}",
                            f"[[Total Due: Rs. {total + gst:,.2f}]]"], 430, y + 16, 300, "body", 16, fam,
              align="right", color=ink, accent=acc)
    d.objects.append(Obj("stamp", 70, y + 20, 130, 130, (200, 40, 40), r.randint(0, 10**9),
                         r.choice(["PAID", "RECEIVED", "APPROVED"])))
    add_block(d, "terms", [f"Payment terms: **{r.choice(['Net 15', 'Net 30', 'Due on receipt'])}**. "
                           f"Please quote the invoice number with every payment. Thank you for your business!"],
              40, 900, 690, "small", 13, fam, color=(90, 90, 90))
    d.objects.append(Obj("qr", W - 130, 880, 90, 90, (20, 20, 20), r.randint(0, 10**9)))
    return d


def receipt(r: random.Random) -> Document:
    ink = r.choice(INKS)
    mono = r.choice(FAMILIES_BY_CLASS["mono"])
    d = Document("receipt", W, H, _bg(r, base=(250, 250, 250), texture=r.uniform(5, 9),
                                     bands=[Band(164, 30, 440, 964, (255, 255, 252))]))
    shop = r.choice(COMPANIES)
    d.objects.append(Obj("logo", 344, 50, 80, 80, r.choice(ACCENTS), r.randint(0, 10**9), shop[0]))
    add_block(d, "shop", f"**{shop.upper()}**", 184, 145, 400, "title", 20, mono, "center", ink)
    add_block(d, "addr", [f"{r.randint(1, 300)} {r.choice(STREETS)}, {r.choice(CITIES)}", f"Tel: +91 {r.randint(70000, 99999)} {r.randint(10000, 99999)}"],
              184, 178, 400, "small", 13, mono, "center", ink)
    d.rules.append(Rule(184, 225, 584, 225, 1, ink))
    rows, total = [], 0
    for name, price in r.sample(PRODUCTS, r.randint(5, 9)):
        q = r.randint(1, 3)
        total += q * price
        rows.append(f"{name[:18]:<18} x{q} {q * price:>8,.0f}")
    y = add_block(d, "items", rows, 184, 240, 400, "body", 14, mono, color=ink, line_gap=1.6, pre=True)
    d.rules.append(Rule(184, y + 8, 584, y + 8, 1, ink))
    y = add_block(d, "total", [f"**TOTAL Rs. {total:,.0f}**", f"Paid by: [[{r.choice(['UPI', 'VISA ****4417', 'Cash'])}]]"],
                  184, y + 20, 400, "heading", 16, mono, color=ink, accent=r.choice(ACCENTS))
    add_block(d, "thanks", ["Thank you for shopping!", f"Bill #{r.randint(100000, 999999)}  {_date(r)}",
                            "**No exchange without bill**"], 184, y + 30, 400, "small", 13, mono, "center", ink)
    d.objects.append(Obj("qr", 334, 840, 100, 100, (10, 10, 10), r.randint(0, 10**9)))
    return d


def certificate(r: random.Random) -> Document:
    acc, fam = r.choice(ACCENTS), _fam(r, "serif")
    d = Document("certificate", W, H, _bg(r, base=r.choice([(252, 248, 235), (250, 246, 230), (248, 250, 244)]),
                                         bands=[Band(24, 24, W - 48, H - 48, (255, 252, 242), 6)]))
    for inset, wd in ((36, 4), (48, 1)):
        d.rules += [Rule(inset, inset, W - inset, inset, wd, acc), Rule(inset, H - inset, W - inset, H - inset, wd, acc),
                    Rule(inset, inset, inset, H - inset, wd, acc), Rule(W - inset, inset, W - inset, H - inset, wd, acc)]
    d.objects.append(Obj("badge", 334, 80, 100, 100, acc, r.randint(0, 10**9)))
    add_block(d, "title", "CERTIFICATE", 84, 210, 600, "title", r.uniform(42, 50), fam, "center", (40, 40, 40))
    add_block(d, "subtitle", f"OF {r.choice(['ACHIEVEMENT', 'EXCELLENCE', 'PARTICIPATION', 'COMPLETION'])}",
              84, 270, 600, "heading", 22, fam, "center", acc)
    add_block(d, "body1", "This certificate is proudly presented to", 84, 350, 600, "body", 18, fam, "center", (60, 60, 60))
    add_block(d, "name", f"[[{_name(r)}]]", 84, 395, 600, "body", 34, fam, "center", (30, 30, 30), acc)
    add_block(d, "body2", f"for **outstanding performance** in the {r.choice(EVENTS)} held at "
                          f"{r.choice(CITIES)}, recognising dedication, creativity and **technical excellence**.",
              114, 470, 540, "body", 17, fam, "center", (60, 60, 60), line_gap=1.5)
    for i, x in enumerate((110, 478)):
        d.objects.append(Obj("signature", x + 20, 760, 140, 50, (30, 40, 90), r.randint(0, 10**9)))
        d.rules.append(Rule(x, 820, x + 180, 820, 1, (80, 80, 80)))
        add_block(d, f"sig{i}", [f"**{_name(r)}**", ["Director", "Programme Chair", "Head of Department"][i % 3]],
                  x, 830, 180, "small", 14, fam, "center", (60, 60, 60))
    add_block(d, "date", f"Date: {_date(r)}", 84, 930, 600, "small", 14, fam, "center", (90, 90, 90))
    return d


def application_form(r: random.Random) -> Document:
    acc, ink, fam = r.choice(ACCENTS), r.choice(INKS), _fam(r, "sans")
    d = Document("application_form", W, H, _bg(r, base=(253, 253, 253), texture=r.uniform(3.5, 6),
                                              bands=[Band(0, 0, W, 8, acc)]))
    d.objects.append(Obj("logo", 40, 30, 64, 64, acc, r.randint(0, 10**9), "G"))
    add_block(d, "title", r.choice(["APPLICATION FORM", "REGISTRATION FORM", "ENROLMENT FORM"]), 120, 36, 520,
              "title", 30, fam, color=ink)
    add_block(d, "dept", f"Department of {r.choice(['Revenue', 'Education', 'Transport', 'Public Health', 'Labour'])}"
                         f" - Form {r.choice('ABCDE')}-{r.randint(10, 99)}", 120, 76, 520, "small", 14, fam, color=(100, 100, 100))
    d.rules.append(Rule(40, 112, W - 40, 112, 2, ink))
    add_block(d, "instr", "Fill all fields in **BLOCK LETTERS**. Fields marked [[*]] are [[mandatory]].",
              40, 126, 690, "small", 14, fam, color=ink, accent=acc)
    y = 170
    fields = r.sample(["Full Name", "Father's Name", "Date of Birth", "Gender", "Address", "City", "PIN Code",
                       "Phone Number", "Email", "Occupation", "Nationality", "ID Proof Type"], 8)
    add_block(d, "sec1", "Section A - **Personal Details**", 40, y, 690, "heading", 18, fam, color=acc)
    y += 40
    for i, f in enumerate(fields):
        add_block(d, f"f{i}", f"{f} [[*]]" if i % 3 == 0 else f, 40, y, 200, "body", 15, fam, color=ink, accent=acc)
        d.rules.append(Rule(250, y + 20, W - 60, y + 20, 1, (90, 90, 90)))
        y += 46
    add_block(d, "sec2", "Section B - **Declaration**", 40, y + 10, 690, "heading", 18, fam, color=acc)
    y = add_block(d, "decl", "I hereby declare that the information given above is **true and correct** to the best "
                             "of my knowledge. I understand that any false statement may lead to [[rejection]] "
                             "of this application.", 40, y + 50, 690, "body", 15, fam, color=ink, accent=acc, line_gap=1.5)
    d.objects.append(Obj("photo", W - 170, 170, 120, 150, (180, 190, 200), r.randint(0, 10**9), "PHOTO"))
    d.objects.append(Obj("signature", 60, y + 40, 150, 50, (20, 30, 90), r.randint(0, 10**9)))
    d.rules.append(Rule(50, y + 95, 260, y + 95, 1, ink))
    add_block(d, "sigl", "Signature of Applicant", 50, y + 102, 220, "small", 13, fam, color=ink)
    add_block(d, "datel", f"Date: {_date(r)}   Place: {r.choice(CITIES)}", 430, y + 102, 300, "small", 13, fam,
              align="right", color=ink)
    return d


def business_letter(r: random.Random) -> Document:
    acc, ink, fam = r.choice(ACCENTS), r.choice(INKS), _fam(r)
    co = r.choice(COMPANIES)
    d = Document("business_letter", W, H, _bg(r))
    d.objects.append(Obj("logo", 50, 40, 70, 70, acc, r.randint(0, 10**9), co[0]))
    add_block(d, "co", f"**{co}**", 135, 48, 400, "title", 26, fam, color=acc)
    add_block(d, "coaddr", f"{r.randint(1, 300)} {r.choice(STREETS)}, {r.choice(CITIES)}  |  www.{co.split()[0].lower()}.com",
              135, 86, 560, "small", 13, fam, color=(100, 100, 100))
    d.rules.append(Rule(50, 125, W - 50, 125, 2, acc))
    add_block(d, "date", _date(r), 50, 150, 300, "body", 15, fam, color=ink)
    add_block(d, "to", [_name(r), f"{r.choice(['Procurement Manager', 'HR Lead', 'Operations Head'])}",
                        r.choice(COMPANIES), r.choice(CITIES)], 50, 190, 400, "body", 15, fam, color=ink)
    add_block(d, "subj", f"Subject: **{r.choice(['Proposal for annual maintenance contract', 'Confirmation of partnership', 'Revised delivery schedule', 'Offer of internship position'])}**",
              50, 310, 670, "heading", 16, fam, color=ink)
    y = 350
    paras = [
        f"Dear {r.choice(['Sir', 'Madam', 'Team'])},",
        "We are pleased to share the details discussed during our recent meeting. Our team has reviewed the "
        f"requirements and we can **commit to delivery within {r.randint(2, 8)} weeks** of receiving the signed order.",
        "The attached schedule outlines milestones, responsibilities and payment terms. Please note that the "
        f"quoted price is [[valid until {_date(r)}]] and includes installation and first-year support.",
        "We value the opportunity to work with you and look forward to a **long and productive association**. "
        "Do not hesitate to contact us for any clarification.",
    ]
    for i, p in enumerate(paras):
        y = add_block(d, f"p{i}", p, 50, y, 668, "body", 15, fam, color=ink, accent=acc, line_gap=1.55) + 14
    add_block(d, "close", "Yours sincerely,", 50, y + 10, 300, "body", 15, fam, color=ink)
    d.objects.append(Obj("signature", 55, y + 40, 150, 50, (20, 30, 90), r.randint(0, 10**9)))
    add_block(d, "signer", [f"**{_name(r)}**", "Business Development Manager"], 50, y + 100, 400, "body", 15, fam, color=ink)
    return d


def restaurant_menu(r: random.Random) -> Document:
    acc = r.choice(ACCENTS)
    dark = r.random() < 0.4
    base = (32, 30, 34) if dark else r.choice(PAPER)
    ink = (240, 236, 228) if dark else r.choice(INKS)
    fam_t, fam_b = _fam(r, "serif"), _fam(r)
    d = Document("restaurant_menu", W, H, _bg(r, base=base, texture=r.uniform(4, 8)))
    name = r.choice(["The Spice Route", "Olive & Oak", "Banana Leaf", "Copper Kettle", "Saffron House", "Blue Door Cafe"])
    d.objects.append(Obj("photo", 0, 0, W, 210, acc, r.randint(0, 10**9)))
    d.objects.append(Obj("badge", W // 2 - 50, 160, 100, 100, acc, r.randint(0, 10**9)))
    add_block(d, "name", name.upper(), 84, 275, 600, "title", 36, fam_t, "center", ink)
    add_block(d, "tag", f"[[{r.choice(['Fresh. Local. Seasonal.', 'Since 1998', 'Authentic home-style cooking'])}]]",
              84, 325, 600, "small", 16, fam_b, "center", ink, acc)
    d.rules.append(Rule(234, 360, 534, 360, 2, acc))
    y = 385
    dishes = r.sample(DISHES, 6)
    for sec, chunk in (("Starters & Mains", dishes[:4]), ("Desserts & Drinks", dishes[4:])):
        add_block(d, f"sec{y}", sec.upper(), 70, y, 628, "heading", 20, fam_t, color=acc)
        y += 38
        for i, (n, desc, p) in enumerate(chunk):
            n_txt = f"**{n}**" + ("  [[Chef's special]]" if r.random() < 0.25 else "")
            add_block(d, f"dish{y}", n_txt, 70, y, 520, "body", 17, fam_b, color=ink, accent=acc)
            add_block(d, f"price{y}", f"**{p}**", 600, y, 98, "body", 17, fam_b, "right", ink)
            add_block(d, f"desc{y}", desc, 70, y + 25, 520, "small", 13, fam_b, color=tuple(int(c * 0.8 + 40) for c in ink) if dark else (100, 100, 100))
            y += 62
        y += 12
    add_block(d, "foot", "All prices in INR, inclusive of taxes. Please inform us of any **dietary requirements**.",
              70, 975, 628, "small", 12, fam_b, "center", ink)
    return d


def event_flyer(r: random.Random) -> Document:
    acc, acc2 = r.sample(ACCENTS, 2)
    fam = _fam(r, "sans")
    top = tuple(min(255, c + 30) for c in acc)
    d = Document("event_flyer", W, H, _bg(r, base=(245, 245, 250), texture=r.uniform(3, 6), gradient=(top, (250, 248, 246))))
    ev = r.choice(EVENTS)
    d.objects.append(Obj("photo", 60, 330, 648, 260, acc2, r.randint(0, 10**9)))
    add_block(d, "kicker", f"{r.choice(CITIES).upper()} 2026", 60, 60, 640, "heading", 20, fam, color=(255, 255, 255))
    add_block(d, "title", ev.upper(), 60, 100, 648, "title", 46, fam, color=(255, 255, 255), line_gap=1.15)
    add_block(d, "sub", f"Join **{r.randint(200, 2000)}+ attendees** for talks, demos and networking.", 60, 255, 648,
              "body", 18, fam, color=(255, 255, 255))
    y = 615
    add_block(d, "when", [f"**Date:** {_date(r)}", f"**Time:** {r.randint(9, 11)}:00 AM onwards",
                          f"**Venue:** {r.choice(['Anna Auditorium', 'Convention Centre Hall B', 'Tech Park Arena'])}"],
              60, y, 360, "body", 18, fam, color=(30, 30, 40), line_gap=1.6)
    add_block(d, "speak", ["[[Featured speakers]]", _name(r), _name(r), _name(r)], 440, y, 268, "body", 17, fam,
              color=(30, 30, 40), accent=acc, line_gap=1.6)
    d.objects.append(Obj("icon", 60, 780, 48, 48, acc, r.randint(0, 10**9)))
    add_block(d, "reg", f"Register free at **{ev.split()[0].lower()}{r.randint(10, 99)}.events** - [[limited seats!]]",
              120, 790, 588, "body", 17, fam, color=(30, 30, 40), accent=acc)
    d.objects.append(Obj("qr", W - 160, 860, 100, 100, (20, 20, 20), r.randint(0, 10**9)))
    add_block(d, "org", [f"Organised by **{r.choice(COMPANIES)}**", "In association with the student tech council"],
              60, 880, 520, "small", 14, fam, color=(80, 80, 90))
    return d


def mobile_settings(r: random.Random) -> Document:
    dark = r.random() < 0.4
    base = (18, 18, 20) if dark else (246, 246, 248)
    card = (34, 34, 38) if dark else (255, 255, 255)
    ink = (236, 236, 240) if dark else (20, 20, 24)
    sub = (150, 150, 160) if dark else (110, 110, 118)
    acc = r.choice([(30, 110, 230), (0, 140, 110), (120, 60, 200)])
    fam = r.choice(["Poppins", "Carlito", "LiberationSans", "DejaVuSans"])
    items = r.sample(SETTINGS, 8)
    bands = [Band(24, 150, W - 48, 70, card, 22)]
    y = 250
    for i in range(0, 8, 4):
        bands.append(Band(24, y, W - 48, 4 * 84, card, 22))
        y += 4 * 84 + 24
    d = Document("mobile_settings", W, H, _bg(r, base=base, texture=r.uniform(1.5, 3), bands=bands))
    add_block(d, "status", f"{r.randint(9, 12)}:{r.randint(10, 59)}", 32, 14, 200, "small", 15, fam, color=ink)
    add_block(d, "title", "Settings", 40, 60, 500, "title", 40, fam, color=ink)
    add_block(d, "search", "Search settings", 110, 172, 500, "body", 18, fam, color=sub)
    d.objects.append(Obj("icon", 52, 167, 36, 36, sub, r.randint(0, 10**9)))
    d.objects.append(Obj("avatar", W - 110, 56, 60, 60, acc, r.randint(0, 10**9), r.choice(FIRST)[0]))
    y = 250
    for i, (t, s) in enumerate(items):
        if i == 4:
            y += 24
        d.objects.append(Obj("icon", 48, y + 20, 40, 40, r.choice(ACCENTS), r.randint(0, 10**9)))
        add_block(d, f"it{i}", f"**{t}**" if r.random() < 0.5 else t, 108, y + 14, 480, "body", 19, fam, color=ink)
        add_block(d, f"st{i}", f"[[{s}]]" if r.random() < 0.3 else s, 108, y + 44, 480, "small", 14, fam, color=sub, accent=acc)
        if r.random() < 0.5:
            d.objects.append(Obj("toggle", W - 120, y + 26, 64, 34, acc, r.randint(0, 10**9)))
        if i % 4 != 3:
            d.rules.append(Rule(108, y + 83, W - 48, y + 83, 1, (60, 60, 66) if dark else (225, 225, 230)))
        y += 84
    return d


TEMPLATES = {
    "invoice": invoice,
    "receipt": receipt,
    "certificate": certificate,
    "application_form": application_form,
    "business_letter": business_letter,
    "restaurant_menu": restaurant_menu,
    "event_flyer": event_flyer,
    "mobile_settings": mobile_settings,
}


def build_document(template: str, seed: int) -> Document:
    return TEMPLATES[template](random.Random(seed))
