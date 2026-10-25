"""English templates (23). Each builder returns a randomised Document.

Original 8: invoice | receipt | certificate | application_form | business_letter | restaurant_menu |
            event_flyer | mobile_settings
Added 15:   bank_statement | payslip | boarding_pass | medical_prescription | resume | newsletter |
            nutrition_label | id_card | shipping_label | report_card | utility_bill | email_message |
            web_landing_page | chat_screenshot | presentation_slide
"""

from __future__ import annotations

import random

from .document import (Background, Band, Document, Obj, Rule, add_block, get_font, run_font, FAMILIES_BY_CLASS)

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
    add_block(d, "foot", ["All prices in INR, inclusive of taxes.", "Please inform us of any **dietary requirements**."],
              70, 970, 628, "small", 12, fam_b, "center", ink)
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
    add_block(d, "about", [f"Software version {r.randint(12, 15)}.{r.randint(0, 9)}  |  Build {r.randint(100000, 999999)}",
                           f"Last checked for updates on {_date(r)}"], 40, 962, 600, "small", 13, fam, color=sub)
    return d


# ------------------------------------------------------------------ 15 added templates
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
MONTHS_FULL = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
               "November", "December"]
BANKS = ["Meridian Bank", "Coastal Trust Bank", "Unity Savings Bank", "Peakline Bank", "First Harbor Bank",
         "Indus Valley Bank", "Granite Federal Bank"]
TXNS = ["UPI/Swiggy Order", "NEFT Salary Credit", "ATM Withdrawal", "POS Big Bazaar", "IMPS Rent Transfer",
        "UPI/Electricity Bill", "Card Amazon Purchase", "Interest Credit", "UPI/Uber Ride", "Cheque Deposit",
        "EMI Home Loan", "UPI/Zomato Order", "Mutual Fund SIP", "Mobile Recharge", "Insurance Premium"]
JOBS = ["Software Engineer", "Data Analyst", "Product Manager", "UX Designer", "Research Scientist",
        "Operations Lead", "Marketing Specialist", "Financial Analyst", "QA Engineer", "Machine Learning Engineer"]
DEPTS = ["Engineering", "Finance", "Human Resources", "Operations", "Research", "Sales", "Customer Success", "Design"]
AIRLINES = ["SkyBridge Air", "Aurora Airlines", "Pacific Crest", "Zenith Airways", "Monsoon Air", "Northstar Jet"]
AIRPORTS = [("MAA", "Chennai"), ("BLR", "Bengaluru"), ("BOM", "Mumbai"), ("DEL", "Delhi"), ("HYD", "Hyderabad"),
            ("SIN", "Singapore"), ("LHR", "London"), ("DXB", "Dubai"), ("ICN", "Seoul"), ("SYD", "Sydney"),
            ("CCU", "Kolkata"), ("YYZ", "Toronto")]
CLINICS = ["CareWell Clinic", "Sunrise Health Centre", "Lotus Family Clinic", "Green Valley Hospital",
           "Apollo Street Clinic", "Harmony Medical Centre"]
QUALS = ["MBBS, MD (General Medicine)", "MBBS, DCH (Paediatrics)", "MBBS, MS (ENT)", "MBBS, DNB (Family Medicine)",
         "MBBS, MD (Dermatology)"]
DIAG = ["Acute upper respiratory tract infection", "Seasonal allergic rhinitis", "Viral fever", "Mild gastritis",
        "Vitamin D deficiency", "Tension-type headache", "Contact dermatitis"]
MEDICINES = [("Amoxicillin 500 mg", "1 capsule three times a day after food", "5 days"),
             ("Paracetamol 650 mg", "1 tablet when needed for fever, max 4 a day", "3 days"),
             ("Cetirizine 10 mg", "1 tablet at night", "7 days"),
             ("Pantoprazole 40 mg", "1 tablet before breakfast", "14 days"),
             ("Vitamin D3 60,000 IU", "1 sachet once a week with milk", "8 weeks"),
             ("Ibuprofen 400 mg", "1 tablet twice a day after food", "3 days"),
             ("Saline nasal spray", "2 puffs in each nostril twice a day", "5 days"),
             ("ORS sachets", "1 sachet in 1 litre of water, sip through the day", "3 days")]
ADVICE = ["Drink plenty of warm fluids and take adequate rest.", "Avoid spicy and oily food; eat small, frequent meals.",
          "Get 20 minutes of morning sunlight every day.", "Avoid dust exposure and keep the room well ventilated."]
SKILLS = ["Python", "SQL", "Machine learning", "Data visualisation", "Project planning", "Public speaking",
          "Figma", "Cloud (AWS)", "Statistics", "Stakeholder management", "React", "Technical writing"]
DOMAINS = ["fintech platforms", "retail analytics", "healthcare software", "mobile applications", "logistics systems"]
ACHIEVEMENTS = ["Led a team of five to ship a reporting dashboard used by 300+ analysts every week.",
                "Reduced data pipeline cost by 35% by moving batch jobs to an event-driven design.",
                "Designed an onboarding flow that improved first-week retention by 18%.",
                "Automated quarterly compliance checks, saving roughly 40 hours of manual work each cycle.",
                "Mentored four junior engineers and introduced weekly code-review clinics.",
                "Built a forecasting model that cut stock-outs by 22% across 60 stores."]
DEGREES = ["B.Tech in Computer Science", "M.Sc. in Data Science", "B.Des. in Interaction Design", "MBA in Operations",
           "B.Com (Honours)", "M.Tech in Artificial Intelligence"]
UNIS = ["VIT University", "Anna University", "IIT Madras", "University of Toronto", "National University of Singapore",
        "Delhi University"]
MASTHEADS = ["The Weekly Ledger", "Campus Chronicle", "Metro Morning", "The Tech Bulletin", "Riverside Gazette"]
HEADLINES = ["City council approves new cycling lanes across the old market district",
             "Local students build a low-cost water sensor for village wells",
             "Startups bet on regional languages as the next wave of internet users",
             "Monsoon arrives early, bringing relief to farmers in the south",
             "Public library reopens with a makerspace and late-night study hall"]
DECKS = ["Residents and shop owners share mixed reactions", "The project took two years and four prototypes",
         "Experts say the trend will reshape product design", "Officials expect normal rainfall through September"]
ARTICLE = ["The proposal was debated for nearly three hours before members voted in favour. Supporters argued that "
           "safer streets would bring more visitors to small businesses, while critics worried about delivery access.",
           "Work is expected to begin next month and will be completed in phases so that the busiest roads stay open. "
           "Temporary signage will guide drivers and pedestrians through each section.",
           "A survey conducted last year found that two in three residents would cycle more often if dedicated lanes "
           "were available. The council says it will publish quarterly updates on usage and safety.",
           "Traders in the area have asked for clear loading windows and more parking at the edges of the district. "
           "The planning team has promised a public meeting before the first phase starts.",
           "Similar schemes in other cities saw a measurable drop in accidents within the first year, according to a "
           "report shared with the council. Officials hope to replicate those results here.",
           "Volunteers will run free bicycle repair camps every Saturday during the first month to encourage families "
           "to try the new routes."]
QUOTES = ["Small changes in how a street works can change how a whole neighbourhood feels.",
          "We designed it so that anyone with basic tools can repair it.", "This is the beginning, not the finish line."]
FOOD_BRANDS = ["Harvest Lane", "Golden Field", "Nature's Basket", "Morning Mill", "Spice Garden"]
FOODS = ["Roasted Almond Granola", "Multigrain Crackers", "Dark Chocolate Oat Bar", "Masala Peanut Mix",
         "Honey Wheat Flakes", "Baked Ragi Chips"]
CLAIMS = ["High in fibre", "No added preservatives", "Source of protein", "Made with whole grains", "No palm oil"]
INGREDIENTS = ["rolled oats", "almonds", "honey", "rice flour", "sunflower oil", "jaggery", "salt", "wheat flour",
               "milk solids", "cocoa powder", "ragi flour", "spices", "dried cranberries", "flax seeds"]
ORGS = ["Crescent Labs", "Northwind Traders", "Vellore Institute", "Bluepeak Systems", "Harbor Tech", "Summit Consulting"]
COURIERS = ["SwiftShip", "BlueDart Express", "Parcel Hub", "RapidRoute", "CargoLink"]
SCHOOLS = ["Greenwood Public School", "St. Mary's Higher Secondary", "Sunbeam Academy", "Delhi Model School",
           "Lakeside International School"]
SUBJECTS = ["English", "Mathematics", "Science", "Social Studies", "Computer Science", "Hindi", "Tamil", "Physics",
            "Chemistry", "Biology", "Economics"]
REMARKS = ["is attentive in class and participates actively in discussions.",
           "shows steady progress and completes assignments on time.",
           "is curious, well-behaved and works well with classmates."]
REMARKS2 = ["Regular reading practice will further improve written expression.",
            "More attention to neat presentation is encouraged.", "Keep up the excellent effort next term."]
PROVIDERS = ["BrightGrid Power", "CityLight Electricity Board", "Volt Energy Ltd", "Sunline Power Distribution"]
EMAIL_SUBJECTS = ["Q3 planning review - agenda and pre-reads", "Your order has been shipped",
                  "Reminder: design sync moved to Thursday", "Welcome to the research programme!",
                  "Invoice INV-2026-4417 for October"]
EMAIL_BODY = ["Thanks for joining the call earlier. As discussed, I have attached the updated timeline and the list "
              "of open questions for each workstream.",
              "Could you please review the numbers in section two before Wednesday? The finance team needs the final "
              "version by the end of the week.",
              "If anything in the plan does not look right, reply to this thread and we can set up a short call.",
              "We have also added a summary slide for leadership, so feel free to reuse it in your team updates."]
STARTUPS = ["Lumen", "Orbit", "Kite", "Vela", "Nimbus", "Quanta"]
TAGLINES = ["Analytics your whole team can understand", "Ship faster with fewer meetings",
            "Every invoice, matched in seconds", "Smart scheduling for busy clinics"]
FEATURES = [("Real-time sync", "Changes appear for everyone instantly, even on slow connections."),
            ("Bank-grade security", "Data is encrypted at rest and in transit, with audit logs for every action."),
            ("Smart reports", "Build a weekly report in minutes using templates your team already likes."),
            ("Open API", "Connect your existing tools with a simple, well-documented REST API."),
            ("Offline mode", "Keep working on the train; everything syncs when you are back online.")]
CHAT_LINES = ["Hey! Are we still on for the review at 4?", "Yes, I just booked the small meeting room.",
              "Great. Can you bring the printed copies of the report?", "Sure, I'll print three. Anything else?",
              "Please also check the totals on page 2, they looked off yesterday.",
              "Found it - the tax row was counted twice. Fixed now.", "Perfect, thanks! See you at 4.",
              "Running 5 minutes late, start without me.", "No problem, we'll begin with the summary slides."]
SLIDE_TITLES = ["Quarterly results and next steps", "Why minute changes matter in document translation",
                "Customer feedback: what we heard", "Roadmap for the next two quarters"]
BULLETS = ["Revenue grew 18% quarter on quarter, led by the enterprise segment.",
           "Two new regions launched with localised onboarding.", "Support response time fell from 9 to 4 hours.",
           "Churn is concentrated in the first 30 days of use.", "Next: self-serve billing and usage dashboards.",
           "Hiring plan focuses on data and reliability roles."]


def _seed(r):
    return r.randint(0, 10**9)


def _light(c, k=170):
    return tuple(min(255, int(x) + k) for x in c)


def _extent(b):
    """Rendered (width, height) of a block, for sizing bubbles and buttons around it."""
    sp = get_font(b.family, False, b.size).getlength(" ")
    w = max(sum(run_font(b.family, r.style, b.size, b.role).getlength(r.text) for r in ln) + sp * (len(ln) - 1)
            for ln in b.lines)
    return w, len(b.lines) * b.size * b.line_gap


def bank_statement(r: random.Random) -> Document:
    acc, ink, fam = r.choice(ACCENTS), r.choice(INKS), _fam(r, "sans")
    mono = r.choice(FAMILIES_BY_CLASS["mono"])
    bank, mon = r.choice(BANKS), r.choice(MONTHS)
    d = Document("bank_statement", W, H, _bg(r, base=(252, 252, 251), texture=r.uniform(3, 6),
                                            bands=[Band(0, 0, W, 96, acc), Band(40, 262, W - 80, 32, (236, 239, 243))]))
    d.objects.append(Obj("logo", 40, 14, 68, 68, (255, 255, 255), _seed(r), bank[0]))
    add_block(d, "bank", f"**{bank}**", 124, 20, 440, "title", 26, fam, color=(255, 255, 255))
    add_block(d, "doc", "Statement of Account", 124, 58, 420, "small", 15, fam, color=(235, 235, 235))
    add_block(d, "holder", ["**Account Holder**", _name(r), f"{r.randint(1, 300)} {r.choice(STREETS)}", r.choice(CITIES)],
              40, 116, 320, "body", 14, fam, color=ink, line_gap=1.5)
    add_block(d, "acct", [f"Account No: **XXXX {r.randint(1000, 9999)}**", f"IFSC: {bank[:4].upper()}0{r.randint(100000, 999999)}",
                          f"Period: 01-28 {mon} 2026", f"Branch: {r.choice(CITIES)}"], 420, 116, 310, "body", 14, fam,
              color=ink, line_gap=1.5)
    add_block(d, "th", f"**{'Date':<8}{'Description':<24}{'Debit':>10}{'Credit':>10}{'Balance':>12}**", 50, 270, 670,
              "heading", 13, mono, color=ink, pre=True)
    bal = opening = r.randint(60, 300) * 1000
    rows, deb, cre = [], 0, 0
    for day in sorted(r.sample(range(1, 29), r.randint(9, 13))):
        amt = r.randint(150, 9000)
        credit = r.random() < 0.3
        bal += amt if credit else -amt
        cre, deb = cre + (amt if credit else 0), deb + (0 if credit else amt)
        rows.append(f"{day:02d}-{mon:<5}{r.choice(TXNS)[:22]:<24}{'' if credit else f'{amt:,.2f}':>10}"
                    f"{f'{amt:,.2f}' if credit else '':>10}{bal:>12,.2f}")
    y = add_block(d, "rows", rows, 50, 306, 670, "body", 13, mono, color=ink, line_gap=1.75, pre=True)
    d.rules.append(Rule(40, y + 8, W - 40, y + 8, 1, (160, 160, 160)))
    add_block(d, "summary", [f"Opening balance: Rs. {opening:,.2f}", f"Total debits: Rs. {deb:,.2f}",
                             f"Total credits: Rs. {cre:,.2f}", f"[[Closing balance: Rs. {bal:,.2f}]]"],
              380, y + 22, 350, "body", 14, fam, align="right", color=ink, accent=acc, line_gap=1.5)
    d.objects.append(Obj("stamp", 60, y + 30, 120, 120, acc, _seed(r), "VERIFIED"))
    add_block(d, "note", "This is a computer-generated statement and does not need a signature. Please report any "
                         "**discrepancy within 15 days** of receipt, otherwise the statement will be treated as correct.",
              40, 900, 540, "small", 12, fam, color=(95, 95, 95), line_gap=1.45)
    d.objects.append(Obj("qr", W - 130, 890, 90, 90, (20, 20, 20), _seed(r)))
    return d


def payslip(r: random.Random) -> Document:
    acc, ink, fam = r.choice(ACCENTS), r.choice(INKS), _fam(r)
    mono = r.choice(FAMILIES_BY_CLASS["mono"])
    co, mon = r.choice(COMPANIES), r.choice(MONTHS_FULL)
    d = Document("payslip", W, H, _bg(r, base=(253, 253, 252), texture=r.uniform(3, 6),
                                     bands=[Band(40, 150, W - 80, 4, acc), Band(40, 300, W - 80, 34, (240, 242, 245))]))
    d.objects.append(Obj("logo", 40, 40, 80, 80, acc, _seed(r), co[0]))
    add_block(d, "co", f"**{co}**", 136, 46, 560, "title", 26, fam, color=ink)
    add_block(d, "title", f"Payslip for the month of {mon} 2026", 136, 86, 560, "heading", 16, fam, color=acc)
    add_block(d, "emp1", [f"Employee: **{_name(r)}**", f"Employee ID: E{r.randint(10000, 99999)}",
                          f"Designation: {r.choice(JOBS)}", f"Department: {r.choice(DEPTS)}"],
              40, 180, 360, "body", 14, fam, color=ink, line_gap=1.6)
    pan = "".join(r.choice("ABCDEFGHJKLMNPQRSTUVWXYZ") for _ in range(5)) + f"{r.randint(1000, 9999)}" + r.choice("ABCDEFGH")
    add_block(d, "emp2", [f"Bank A/c: XXXX{r.randint(1000, 9999)}", f"PAN: {pan}", f"Days paid: {r.randint(26, 31)}",
                          f"Joined: {_date(r)[:-5]} {r.randint(2015, 2025)}"], 430, 180, 300, "body", 14, fam, color=ink,
              line_gap=1.6)
    basic = r.randint(25, 90) * 1000
    earn = [("Basic", basic), ("HRA", int(basic * 0.4)), ("Special allowance", int(basic * r.uniform(0.2, 0.5))),
            ("Conveyance", 1600), ("Bonus", r.choice([0, 2500, 5000]))]
    ded = [("Provident fund", int(basic * 0.12)), ("Professional tax", 200),
           ("Income tax (TDS)", int(basic * r.uniform(0.05, 0.15))), ("Health insurance", r.choice([500, 750, 1200]))]
    add_block(d, "eh", f"**{'Earnings':<18}{'Amount':>10}**", 50, 309, 320, "heading", 13, mono, color=ink, pre=True)
    add_block(d, "dh", f"**{'Deductions':<18}{'Amount':>10}**", 410, 309, 320, "heading", 13, mono, color=ink, pre=True)
    ye = add_block(d, "earn", [f"{n:<18}{v:>10,.2f}" for n, v in earn], 50, 346, 320, "body", 13, mono, color=ink,
                   line_gap=1.8, pre=True)
    yd = add_block(d, "ded", [f"{n:<18}{v:>10,.2f}" for n, v in ded], 410, 346, 320, "body", 13, mono, color=ink,
                   line_gap=1.8, pre=True)
    y = max(ye, yd) + 12
    d.rules.append(Rule(40, y, W - 40, y, 1, (150, 150, 150)))
    ge, gd = sum(v for _, v in earn), sum(v for _, v in ded)
    add_block(d, "gross", f"**{'Gross earnings':<18}{ge:>10,.2f}**", 50, y + 12, 320, "body", 13, mono, color=ink, pre=True)
    add_block(d, "tded", f"**{'Total deductions':<18}{gd:>10,.2f}**", 410, y + 12, 320, "body", 13, mono, color=ink, pre=True)
    y += 60
    d.background.bands.append(Band(40, y, W - 80, 56, _light(acc, 150)))
    add_block(d, "net", f"[[Net pay: Rs. {ge - gd:,.2f}]]", 60, y + 15, 640, "heading", 20, fam, color=ink, accent=acc)
    leave = [r.randint(0, 12), r.randint(0, 8), r.randint(0, 15)]
    add_block(d, "leave", [f"**Leave balance**", f"Casual: {leave[0]} days   Sick: {leave[1]} days   Earned: {leave[2]} days"],
              40, y + 90, 688, "body", 14, fam, color=ink, line_gap=1.6)
    add_block(d, "foot", f"This is a system-generated payslip. Salary is credited to the registered bank account. "
                         f"For any query write to **payroll@{co.split()[0].lower()}.com** within 7 days.",
              40, 885, 688, "small", 12, fam, color=(95, 95, 95), line_gap=1.45)
    d.objects.append(Obj("signature", W - 230, 780, 150, 48, (20, 30, 90), _seed(r)))
    d.rules.append(Rule(W - 250, 834, W - 60, 834, 1, ink))
    add_block(d, "hr", "HR Manager", W - 250, 840, 190, "small", 12, fam, align="center", color=ink)
    return d


def boarding_pass(r: random.Random) -> Document:
    BW, BH = 1024, 480
    acc, fam = r.choice(ACCENTS), _fam(r, "sans")
    air = r.choice(AIRLINES)
    (c1, n1), (c2, n2) = r.sample(AIRPORTS, 2)
    ink, sub = (35, 35, 45), (105, 105, 115)
    d = Document("boarding_pass", BW, BH, _bg(r, base=(244, 245, 248), texture=r.uniform(2.5, 5),
                                             bands=[Band(0, 0, BW, 80, acc), Band(24, 100, BW - 48, BH - 124, (255, 255, 255), 18)]))
    d.objects.append(Obj("logo", 30, 8, 64, 64, (255, 255, 255), _seed(r), air[0]))
    add_block(d, "air", f"**{air.upper()}**", 110, 16, 420, "title", 24, fam, color=(255, 255, 255))
    add_block(d, "bp", "BOARDING PASS", 110, 50, 300, "small", 14, fam, color=(235, 235, 235))
    add_block(d, "bp2", "BOARDING PASS", 740, 28, 250, "heading", 16, fam, color=(255, 255, 255))
    add_block(d, "from", c1, 60, 120, 200, "title", 54, fam, color=ink)
    add_block(d, "fromn", n1, 60, 190, 200, "small", 15, fam, color=sub)
    add_block(d, "to", c2, 420, 120, 200, "title", 54, fam, color=ink)
    add_block(d, "ton", n2, 420, 190, 200, "small", 15, fam, color=sub)
    d.objects.append(Obj("icon", 290, 136, 56, 56, acc, _seed(r)))
    pax = _name(r).upper()
    flight = f"{air[:2].upper()} {r.randint(100, 9999)}"
    gate, seat = f"{r.choice('ABCD')}{r.randint(1, 40)}", f"{r.randint(1, 38)}{r.choice('ABCDEF')}"
    t = f"{r.randint(5, 22):02d}:{r.choice(['00', '15', '30', '45', '05', '50'])}"
    add_block(d, "pax", ["Passenger", f"**{pax}**"], 60, 236, 330, "body", 15, fam, color=ink)
    add_block(d, "fl", ["Flight", f"**{flight}**"], 420, 236, 200, "body", 15, fam, color=ink)
    add_block(d, "gate", ["Gate", f"**{gate}**"], 60, 306, 100, "body", 15, fam, color=ink)
    add_block(d, "seat", ["Seat", f"[[{seat}]]"], 175, 306, 100, "body", 15, fam, color=ink, accent=acc)
    add_block(d, "board", ["Boarding", f"**{t}**"], 290, 306, 120, "body", 15, fam, color=ink)
    add_block(d, "date", ["Date", f"**{_date(r)}**"], 420, 306, 200, "body", 15, fam, color=ink)
    add_block(d, "note", "Gate closes **20 minutes** before departure. Please carry a valid photo ID together with "
                         "this boarding pass.", 60, 380, 580, "small", 13, fam, color=sub, line_gap=1.45)
    for yy in range(112, BH - 30, 16):
        d.rules.append(Rule(700, yy, 700, yy + 8, 2, (205, 205, 215)))
    add_block(d, "stub", [f"**{pax}**", f"{c1} to {c2}", f"Flight {flight}", f"Seat [[{seat}]]  Gate {gate}",
                          f"Boarding {t}"], 730, 118, 270, "body", 14, fam, color=ink, accent=acc, line_gap=1.6)
    d.objects.append(Obj("qr", 800, 286, 130, 130, (20, 20, 20), _seed(r)))
    return d


def medical_prescription(r: random.Random) -> Document:
    acc = r.choice([(0, 120, 110), (20, 90, 170), (0, 110, 60), (150, 40, 90)])
    ink, fam = r.choice(INKS), _fam(r)
    d = Document("medical_prescription", W, H, _bg(r, base=(253, 253, 250), texture=r.uniform(3, 6),
                                                  bands=[Band(0, 0, W, 10, acc), Band(0, H - 50, W, 50, _light(acc))]))
    d.objects.append(Obj("logo", 40, 34, 70, 70, acc, _seed(r), "+"))
    add_block(d, "clinic", f"**{r.choice(CLINICS)}**", 126, 36, 450, "title", 26, fam, color=acc)
    add_block(d, "caddr", [f"{r.randint(1, 300)} {r.choice(STREETS)}, {r.choice(CITIES)}",
                           f"Ph: +91 {r.randint(70000, 99999)} {r.randint(10000, 99999)}  |  Mon-Sat 9 AM - 8 PM"],
              126, 72, 600, "small", 13, fam, color=(90, 90, 90))
    add_block(d, "dr", [f"**Dr. {_name(r)}**", r.choice(QUALS), f"Reg. No. {r.choice(['TN', 'KA', 'MH', 'DL'])}/{r.randint(10000, 99999)}"],
              430, 122, 300, "body", 14, fam, align="right", color=ink)
    d.rules.append(Rule(40, 200, W - 40, 200, 2, acc))
    add_block(d, "pt", [f"Patient: **{_name(r)}**", f"Age / Sex: {r.randint(4, 85)} / {r.choice(['M', 'F'])}",
                        f"Date: {_date(r)}"], 40, 216, 400, "body", 14, fam, color=ink, line_gap=1.55)
    add_block(d, "dx", f"Diagnosis: [[{r.choice(DIAG)}]]", 40, 296, 680, "body", 15, fam, color=ink, accent=acc)
    add_block(d, "rx", "Rx", 40, 338, 120, "title", 40, _fam(r, "serif"), color=acc)
    y = 400
    for i, (m, how, dur) in enumerate(r.sample(MEDICINES, r.randint(3, 5))):
        y = add_block(d, f"med{i}", [f"{i + 1}. **{m}**", f"{how} - for {dur}"], 70, y, 620, "body", 15, fam,
                      color=ink, line_gap=1.5) + 14
    y = add_block(d, "adv", f"Advice: {r.choice(ADVICE)} Review after **{r.randint(5, 14)} days** or earlier if "
                            f"symptoms get worse.", 40, y + 10, 680, "body", 14, fam, color=ink, line_gap=1.5)
    d.objects.append(Obj("stamp", 360, y + 22, 110, 110, acc, _seed(r), "CLINIC"))
    d.objects.append(Obj("signature", 545, y + 40, 150, 50, (20, 30, 90), _seed(r)))
    d.rules.append(Rule(520, y + 96, 720, y + 96, 1, ink))
    add_block(d, "sig", "Signature and seal", 520, y + 104, 200, "small", 12, fam, align="center", color=ink)
    add_block(d, "foot", "Not valid for medico-legal purposes. Take medicines only as prescribed.", 40, H - 36, 690,
              "small", 12, fam, color=(60, 60, 60))
    return d


def resume(r: random.Random) -> Document:
    acc, ink = r.choice(ACCENTS), r.choice(INKS)
    fam, fam_h = _fam(r), _fam(r)
    side = tuple(int(c * 0.25 + 28) for c in acc)
    light = (226, 226, 232)
    d = Document("resume", W, H, _bg(r, base=r.choice(PAPER), texture=r.uniform(3, 6), bands=[Band(0, 0, 240, H, side)]))
    nm = _name(r)
    first, last = nm.lower().split()
    d.objects.append(Obj("avatar", 60, 40, 120, 120, acc, _seed(r), nm[0]))
    add_block(d, "contact_h", "CONTACT", 24, 190, 200, "heading", 15, fam, color=(255, 255, 255))
    add_block(d, "contact", [f"+91 {r.randint(70000, 99999)} {r.randint(10000, 99999)}", f"{first}.{last}@mail.com",
                             r.choice(CITIES), f"linkedin.com/in/{first}{r.randint(10, 99)}"],
              24, 220, 205, "small", 12, fam, color=light, line_gap=1.6)
    add_block(d, "skills_h", "SKILLS", 24, 360, 200, "heading", 15, fam, color=(255, 255, 255))
    add_block(d, "skills", r.sample(SKILLS, 6), 24, 390, 200, "small", 13, fam, color=light, line_gap=1.7)
    add_block(d, "lang_h", "LANGUAGES", 24, 560, 200, "heading", 15, fam, color=(255, 255, 255))
    add_block(d, "lang", r.sample(["English", "Hindi", "Tamil", "Kannada", "Telugu", "French", "German", "Korean"], 3),
              24, 590, 200, "small", 13, fam, color=light, line_gap=1.7)
    add_block(d, "name", nm.upper(), 270, 44, 470, "title", 34, fam_h, color=ink)
    job = r.choice(JOBS)
    add_block(d, "role", f"[[{job}]]", 270, 92, 470, "heading", 17, fam, color=ink, accent=acc)
    d.rules.append(Rule(270, 128, W - 36, 128, 2, acc))
    add_block(d, "prof_h", "PROFILE", 270, 145, 470, "heading", 16, fam, color=acc)
    y = add_block(d, "prof", f"{job} with **{r.randint(2, 12)} years** of experience in {r.choice(DOMAINS)}. Known for "
                             f"clear communication, ownership of outcomes and building reliable systems that teams enjoy "
                             f"using.", 270, 172, 460, "body", 14, fam, color=ink, line_gap=1.5) + 18
    add_block(d, "exp_h", "EXPERIENCE", 270, y, 470, "heading", 16, fam, color=acc)
    y += 30
    for i, ach in enumerate((r.sample(ACHIEVEMENTS, 2), r.sample(ACHIEVEMENTS, 2))):
        y0 = r.randint(2016, 2022)
        add_block(d, f"job{i}", f"**{r.choice(JOBS)}** - {r.choice(COMPANIES)}", 270, y, 470, "body", 14, fam, color=ink)
        y += 22
        add_block(d, f"yr{i}", f"{y0} - {'Present' if i == 0 else y0 + r.randint(1, 3)}  |  {r.choice(CITIES)}",
                  270, y, 470, "small", 12, fam, color=(110, 110, 110))
        y += 22
        y = add_block(d, f"ach{i}", [f"- {a}" for a in ach], 270, y, 460, "body", 13, fam, color=ink, line_gap=1.5) + 16
    add_block(d, "edu_h", "EDUCATION", 270, y, 470, "heading", 16, fam, color=acc)
    add_block(d, "edu", [f"**{r.choice(DEGREES)}**", f"{r.choice(UNIS)}, {r.randint(2010, 2020)}  |  CGPA [[{r.uniform(7.5, 9.8):.2f}]]"],
              270, y + 30, 460, "body", 14, fam, color=ink, accent=acc, line_gap=1.5)
    return d


def newsletter(r: random.Random) -> Document:
    acc, ink = r.choice(ACCENTS), r.choice(INKS)
    fam_t, fam_b = _fam(r, "serif"), _fam(r, "serif" if r.random() < 0.6 else "sans")
    d = Document("newsletter", W, H, _bg(r, base=r.choice(PAPER), texture=r.uniform(4, 8)))
    mast = r.choice(MASTHEADS)
    add_block(d, "mast", mast.upper(), 40, 30, 688, "title", 42, fam_t, align="center", color=ink)
    d.rules += [Rule(40, 92, W - 40, 92, 3, ink), Rule(40, 122, W - 40, 122, 1, ink)]
    add_block(d, "dateline", f"{r.choice(CITIES).upper()}  |  {_date(r).upper()}  |  ISSUE {r.randint(10, 250)}",
              40, 100, 688, "small", 12, fam_b, align="center", color=ink)
    y = add_block(d, "headline", r.choice(HEADLINES), 40, 142, 688, "title", 30, fam_t, color=ink, line_gap=1.2) + 8
    y = add_block(d, "deck", f"[[{r.choice(DECKS)}]]", 40, y, 688, "heading", 16, fam_b, color=ink, accent=acc) + 12
    d.objects.append(Obj("photo", 40, y, 688, 220, acc, _seed(r)))
    add_block(d, "caption", f"Photo: {_name(r)} / {mast}", 40, y + 226, 688, "small", 11, fam_b, color=(110, 110, 110))
    y += 256
    paras = r.sample(ARTICLE, 4)
    add_block(d, "col1", paras[0] + " " + paras[1], 40, y, 330, "body", 13, fam_b, color=ink, line_gap=1.5)
    y2 = add_block(d, "col2", paras[2], 398, y, 330, "body", 13, fam_b, color=ink, line_gap=1.5) + 14
    d.rules.append(Rule(398, y2, 728, y2, 2, acc))
    y2 = add_block(d, "quote", f'[["{r.choice(QUOTES)}"]]', 398, y2 + 12, 330, "body", 16, fam_t, color=ink, accent=acc,
                   line_gap=1.35) + 14
    d.rules.append(Rule(398, y2, 728, y2, 2, acc))
    add_block(d, "col2b", paras[3], 398, y2 + 14, 330, "body", 13, fam_b, color=ink, line_gap=1.5)
    d.rules.append(Rule(40, H - 52, W - 40, H - 52, 1, ink))
    add_block(d, "foot", f"Continued on page {r.randint(2, 9)}  |  {mast.lower().replace(' ', '')}.news", 40, H - 42,
              688, "small", 12, fam_b, align="center", color=ink)
    return d


def nutrition_label(r: random.Random) -> Document:
    acc, ink, fam = r.choice(ACCENTS), (20, 20, 20), _fam(r, "sans")
    mono = r.choice(FAMILIES_BY_CLASS["mono"])
    d = Document("nutrition_label", W, H, _bg(r, base=r.choice(PAPER), texture=r.uniform(3, 6),
                                             bands=[Band(0, 0, W, 250, acc), Band(390, 280, 340, 640, (255, 255, 255))]))
    add_block(d, "brand", r.choice(FOOD_BRANDS).upper(), 40, 40, 690, "heading", 20, fam, color=(255, 255, 255))
    add_block(d, "prod", r.choice(FOODS), 40, 80, 690, "title", 40, _fam(r, "serif"), color=(255, 255, 255), line_gap=1.15)
    add_block(d, "claim", f"[[{r.choice(CLAIMS)}]]  |  Net wt. **{r.choice([200, 250, 400, 500, 750])} g**", 40, 196, 690,
              "body", 17, fam, color=(255, 255, 255), accent=(255, 236, 150))
    d.objects.append(Obj("photo", 40, 280, 320, 260, acc, _seed(r)))
    add_block(d, "nf", "Nutrition Facts", 408, 292, 300, "title", 28, fam, color=ink)
    d.rules.append(Rule(408, 334, 712, 334, 1, ink))
    add_block(d, "serv", [f"{r.randint(4, 12)} servings per pack", f"**Serving size {r.choice([25, 30, 40, 50])} g**"],
              408, 342, 304, "body", 14, fam, color=ink)
    d.rules.append(Rule(408, 386, 712, 386, 8, ink))
    add_block(d, "cal", f"**Calories {r.randint(90, 280)}**", 408, 396, 304, "heading", 22, fam, color=ink)
    d.rules.append(Rule(408, 430, 712, 430, 4, ink))
    nut = [("Total Fat", "g", 0, 18), ("Saturated Fat", "g", 0, 8), ("Trans Fat", "g", 0, 0), ("Cholesterol", "mg", 0, 30),
           ("Sodium", "mg", 40, 400), ("Total Carbohydrate", "g", 10, 40), ("Dietary Fiber", "g", 1, 9),
           ("Total Sugars", "g", 1, 20), ("Protein", "g", 2, 14)]
    rows = []
    for n, u, lo, hi in nut:
        v = r.randint(lo, hi)
        pct = round(v * 100 / (70 if u == "g" else 2300))
        rows.append(f"{n:<19}{str(v) + u:>6}{pct:>4}%")
    y = add_block(d, "nut", rows, 408, 442, 304, "body", 14, mono, color=ink, line_gap=1.75, pre=True)
    d.rules.append(Rule(408, y + 6, 712, y + 6, 4, ink))
    add_block(d, "dv", "* The % Daily Value tells you how much a nutrient in one serving adds to a daily diet. "
                       "2,000 calories a day is used for general nutrition advice.", 408, y + 18, 304, "small", 11, fam,
              color=ink, line_gap=1.4)
    y = add_block(d, "ingr", f"**Ingredients:** {', '.join(r.sample(INGREDIENTS, 7))}.", 40, 565, 320, "body", 13, fam,
                  color=ink, line_gap=1.5) + 12
    y = add_block(d, "allergen", f"[[Allergen information: contains {' and '.join(r.sample(['milk', 'soy', 'wheat', 'nuts', 'sesame'], 2))}.]]",
                  40, y, 320, "body", 13, fam, color=ink, accent=(190, 30, 30), line_gap=1.5) + 12
    add_block(d, "store", ["Store in a cool, dry place.", f"Best before: {_date(r)}",
                           f"Made by {r.choice(COMPANIES)}, {r.choice(CITIES)}"], 40, y, 320, "small", 12, fam,
              color=(70, 70, 70), line_gap=1.5)
    d.objects.append(Obj("qr", 40, 885, 90, 90, ink, _seed(r)))
    return d


def id_card(r: random.Random) -> Document:
    CW, CH = 900, 560
    acc, ink, fam = r.choice(ACCENTS), r.choice(INKS), _fam(r, "sans")
    org = r.choice(ORGS)
    d = Document("id_card", CW, CH, _bg(r, base=(232, 234, 240), texture=r.uniform(2, 4),
                                       bands=[Band(20, 20, CW - 40, CH - 40, (255, 255, 255), 26),
                                              Band(20, 20, CW - 40, 100, acc, 26), Band(20, 92, CW - 40, 28, acc)]))
    d.objects.append(Obj("logo", 44, 34, 70, 70, (255, 255, 255), _seed(r), org[0]))
    add_block(d, "org", f"**{org.upper()}**", 130, 38, 600, "title", 26, fam, color=(255, 255, 255))
    add_block(d, "type", r.choice(["EMPLOYEE IDENTITY CARD", "STUDENT IDENTITY CARD", "VISITOR PASS", "STAFF ID"]),
              130, 78, 600, "small", 14, fam, color=(240, 240, 240))
    d.objects.append(Obj("photo", 50, 148, 170, 210, (180, 190, 200), _seed(r), "PHOTO"))
    add_block(d, "name", _name(r), 250, 146, 420, "title", 30, fam, color=ink)
    add_block(d, "desig", f"[[{r.choice(JOBS)}]]", 250, 190, 420, "heading", 17, fam, color=ink, accent=acc)
    add_block(d, "fields", [f"ID No: **{org[:3].upper()}-{r.randint(100000, 999999)}**", f"Department: {r.choice(DEPTS)}",
                            f"Blood group: {r.choice(['A+', 'B+', 'O+', 'AB+', 'O-', 'A-'])}",
                            f"Valid till: {_date(r)[:-4]}{r.randint(2027, 2030)}"], 250, 230, 400, "body", 16, fam,
              color=ink, line_gap=1.6)
    d.objects.append(Obj("qr", CW - 200, 152, 140, 140, (20, 20, 20), _seed(r)))
    d.objects.append(Obj("signature", 250, 378, 150, 46, (20, 30, 90), _seed(r)))
    d.rules.append(Rule(250, 428, 430, 428, 1, ink))
    add_block(d, "sigl", "Authorised signatory", 250, 434, 200, "small", 12, fam, color=(90, 90, 90))
    add_block(d, "note", f"This card is the property of {org}. If found, please return it to the security office or "
                         f"call **+91 {r.randint(70000, 99999)} {r.randint(10000, 99999)}**.", 50, 474, 800, "small",
              13, fam, color=(90, 90, 90), line_gap=1.4)
    return d


def shipping_label(r: random.Random) -> Document:
    ink, fam = (15, 15, 15), _fam(r, "sans")
    mono = r.choice(FAMILIES_BY_CLASS["mono"])
    courier = r.choice(COURIERS)
    d = Document("shipping_label", W, H, _bg(r, base=(222, 200, 160), texture=r.uniform(6, 10),
                                            bands=[Band(64, 40, W - 128, H - 80, (252, 252, 250)), Band(64, 40, W - 128, 90, ink)]))
    d.rules += [Rule(64, 40, 64, H - 40, 2, ink), Rule(W - 64, 40, W - 64, H - 40, 2, ink), Rule(64, H - 40, W - 64, H - 40, 2, ink)]
    add_block(d, "courier", f"**{courier.upper()}**", 90, 64, 400, "title", 30, fam, color=(255, 255, 255))
    add_block(d, "svc", r.choice(["EXPRESS", "PRIORITY", "STANDARD", "OVERNIGHT"]), 500, 70, 180, "heading", 22, fam,
              align="right", color=(255, 255, 255))
    add_block(d, "fromh", "FROM", 90, 150, 200, "heading", 13, fam, color=(90, 90, 90))
    add_block(d, "from", [r.choice(COMPANIES), f"{r.randint(1, 300)} {r.choice(STREETS)}",
                          f"{r.choice(CITIES)} - {r.randint(100000, 999999)}"], 90, 172, 380, "body", 14, fam, color=ink,
              line_gap=1.45)
    d.rules.append(Rule(64, 250, W - 64, 250, 2, ink))
    add_block(d, "toh", "SHIP TO", 90, 266, 200, "heading", 14, fam, color=(90, 90, 90))
    add_block(d, "to", [f"**{_name(r).upper()}**", f"{r.randint(1, 300)} {r.choice(STREETS)}",
                        f"{r.choice(CITIES)} - {r.randint(100000, 999999)}",
                        f"Ph: +91 {r.randint(70000, 99999)} {r.randint(10000, 99999)}"], 90, 292, 560, "body", 22, fam,
              color=ink, line_gap=1.4)
    d.rules.append(Rule(64, 440, W - 64, 440, 2, ink))
    trk = f"{courier[:2].upper()}{r.randint(10**9, 10**10 - 1)}IN"
    add_block(d, "trkh", "TRACKING NUMBER", 90, 456, 300, "heading", 13, fam, color=(90, 90, 90))
    add_block(d, "trk", f"**{trk}**", 90, 478, 560, "title", 28, mono, color=ink)
    bx = 92
    while bx < W - 100:
        wd = r.choice([1, 2, 2, 3, 4])
        d.rules.append(Rule(bx, 530, bx, 636, wd, ink))
        bx += wd + r.choice([2, 3, 3, 4, 6])
    add_block(d, "trk2", trk, 90, 644, 588, "small", 13, mono, align="center", color=ink)
    d.rules.append(Rule(64, 680, W - 64, 680, 2, ink))
    add_block(d, "meta", [f"Weight: **{r.uniform(0.2, 12):.2f} kg**",
                          f"Size: {r.randint(10, 60)} x {r.randint(10, 40)} x {r.randint(5, 30)} cm",
                          f"Order ID: #{r.randint(100000, 999999)}", f"Ship date: {_date(r)}"], 90, 700, 340, "body", 15,
              fam, color=ink, line_gap=1.55)
    d.objects.append(Obj("qr", W - 230, 700, 140, 140, ink, _seed(r)))
    add_block(d, "handle", f"[[{r.choice(['HANDLE WITH CARE', 'FRAGILE', 'KEEP DRY', 'THIS SIDE UP'])}]] - Do not bend. "
                           f"If undelivered, please return to the sender at the address above.", 90, 880, 590, "body", 14,
              fam, color=ink, accent=(200, 30, 30), line_gap=1.45)
    return d


def report_card(r: random.Random) -> Document:
    acc, ink, fam = r.choice(ACCENTS), r.choice(INKS), _fam(r)
    mono = r.choice(FAMILIES_BY_CLASS["mono"])
    d = Document("report_card", W, H, _bg(r, base=r.choice(PAPER), texture=r.uniform(3, 7),
                                         bands=[Band(40, 330, W - 80, 32, _light(acc))]))
    d.rules += [Rule(24, 24, W - 24, 24, 3, acc), Rule(24, H - 24, W - 24, H - 24, 3, acc),
                Rule(24, 24, 24, H - 24, 3, acc), Rule(W - 24, 24, W - 24, H - 24, 3, acc)]
    d.objects.append(Obj("badge", 50, 44, 90, 90, acc, _seed(r)))
    add_block(d, "school", r.choice(SCHOOLS).upper(), 156, 54, 560, "title", 25, _fam(r, "serif"), color=ink)
    add_block(d, "saddr", f"Affiliated to the Central Board  |  {r.choice(CITIES)}", 156, 94, 560, "small", 13, fam,
              color=(100, 100, 100))
    add_block(d, "rt", f"PROGRESS REPORT {r.choice(['2025-26', '2026-27'])}", 40, 160, 688, "heading", 20, fam,
              align="center", color=acc)
    student = _name(r)
    add_block(d, "stu", [f"Student: **{student}**", f"Class: {r.randint(1, 12)}-{r.choice('ABCD')}",
                         f"Roll No: {r.randint(1, 60)}"], 50, 205, 340, "body", 15, fam, color=ink, line_gap=1.55)
    add_block(d, "stu2", [f"Term: {r.choice(['Term I', 'Term II', 'Annual'])}", f"Attendance: {r.randint(150, 200)}/200",
                          f"Date of birth: {_date(r)[:-4]}{r.randint(2009, 2020)}"], 420, 205, 310, "body", 15, fam,
              color=ink, line_gap=1.55)
    add_block(d, "th", f"**{'Subject':<20}{'Max':>6}{'Marks':>8}{'Grade':>8}**", 56, 339, 660, "heading", 14, mono,
              color=ink, pre=True)
    rows, tot = [], 0
    for s in r.sample(SUBJECTS, 6):
        m = r.randint(48, 99)
        tot += m
        g = "A1" if m >= 91 else "A2" if m >= 81 else "B1" if m >= 71 else "B2" if m >= 61 else "C1"
        rows.append(f"{s:<20}{100:>6}{m:>8}{g:>8}")
    y = add_block(d, "marks", rows, 56, 376, 660, "body", 14, mono, color=ink, line_gap=1.8, pre=True)
    d.rules.append(Rule(40, y + 6, W - 40, y + 6, 1, (140, 140, 140)))
    add_block(d, "total", [f"Total: **{tot} / 600**", f"Percentage: **{tot / 6:.1f}%**", "Result: [[PASS]]"],
              420, y + 18, 300, "body", 15, fam, align="right", color=ink, accent=acc, line_gap=1.5)
    add_block(d, "remh", "Class teacher's remarks", 50, y + 118, 400, "heading", 15, fam, color=acc)
    add_block(d, "rem", f"{student.split()[0]} {r.choice(REMARKS)} {r.choice(REMARKS2)}", 50, y + 146, 668, "body", 14,
              fam, color=ink, line_gap=1.5)
    for i, (x, role) in enumerate(((90, "Class Teacher"), (500, "Principal"))):
        d.objects.append(Obj("signature", x + 15, 820, 150, 48, (20, 30, 90), _seed(r)))
        d.rules.append(Rule(x, 876, x + 180, 876, 1, ink))
        add_block(d, f"sig{i}", role, x, 884, 180, "small", 13, fam, align="center", color=ink)
    return d


def utility_bill(r: random.Random) -> Document:
    acc, ink, fam = r.choice(ACCENTS), r.choice(INKS), _fam(r, "sans")
    mono = r.choice(FAMILIES_BY_CLASS["mono"])
    prov = r.choice(PROVIDERS)
    d = Document("utility_bill", W, H, _bg(r, base=(253, 253, 253), texture=r.uniform(3, 6),
                                          bands=[Band(0, 0, W, 110, acc), Band(420, 140, 310, 150, _light(acc, 175), 14)]))
    d.objects.append(Obj("logo", 36, 20, 70, 70, (255, 255, 255), _seed(r), prov[0]))
    add_block(d, "prov", f"**{prov}**", 122, 26, 600, "title", 26, fam, color=(255, 255, 255))
    add_block(d, "kind", "Electricity Bill  |  Tax Invoice", 122, 66, 600, "small", 15, fam, color=(240, 240, 240))
    add_block(d, "cons", [f"Consumer: **{_name(r)}**", f"Consumer No: {r.randint(10**9, 10**10 - 1)}",
                          f"{r.randint(1, 300)} {r.choice(STREETS)}", r.choice(CITIES),
                          f"Tariff: {r.choice(['LT-1 Domestic', 'LT-2 Commercial'])}"], 40, 140, 360, "body", 14, fam,
              color=ink, line_gap=1.55)
    units = r.randint(90, 650)
    energy = units * r.choice([4.5, 5.2, 6.1, 7.0])
    charges = [("Energy charges", energy), ("Fixed charges", r.choice([60, 90, 120])), ("Electricity duty", energy * 0.05),
               ("Meter rent", 25), ("Arrears", r.choice([0, 0, 0, 340.5, 1210.0]))]
    amount = sum(v for _, v in charges)
    add_block(d, "duel", "Amount payable", 442, 156, 270, "small", 14, fam, color=ink)
    add_block(d, "due", f"**Rs. {amount:,.2f}**", 442, 182, 270, "title", 32, fam, color=ink)
    add_block(d, "dued", f"Due date: [[{_date(r)}]]", 442, 238, 270, "body", 15, fam, color=ink, accent=acc)
    d.rules.append(Rule(40, 318, W - 40, 318, 2, ink))
    prev = r.randint(10000, 90000)
    add_block(d, "mh", f"**{'Meter No':<12}{'Previous':>10}{'Current':>10}{'Units':>8}**", 40, 334, 688, "heading", 13,
              mono, color=ink, pre=True)
    add_block(d, "meter", f"{'M' + str(r.randint(100000, 999999)):<12}{prev:>10}{prev + units:>10}{units:>8}", 40, 358,
              688, "body", 13, mono, color=ink, pre=True)
    add_block(d, "ch", f"**{'Charges':<28}{'Amount (Rs.)':>14}**", 40, 404, 688, "heading", 13, mono, color=ink, pre=True)
    y = add_block(d, "charges", [f"{n:<28}{v:>14,.2f}" for n, v in charges], 40, 430, 688, "body", 13, mono, color=ink,
                  line_gap=1.75, pre=True)
    d.rules.append(Rule(40, y + 6, W - 40, y + 6, 1, (150, 150, 150)))
    add_block(d, "hist", "Consumption history (units)", 40, y + 24, 400, "heading", 14, fam, color=ink)
    base_y, hist = y + 230, [max(40, int(units * r.uniform(0.6, 1.3))) for _ in range(5)] + [units]
    top = max(hist)
    m0 = r.randrange(12)
    mons = [MONTHS[(m0 + k) % 12] for k in range(6)]
    for i, (u, m) in enumerate(zip(hist, mons)):
        x = 70 + i * 110
        h = int(150 * u / top)
        d.background.bands.append(Band(x, base_y - h, 64, h, acc if i == 5 else _light(acc, 110)))
        add_block(d, f"hv{i}", str(u), x, base_y - h - 18, 64, "small", 11, fam, align="center", color=ink)
        add_block(d, f"hm{i}", m, x, base_y + 6, 64, "small", 12, fam, align="center", color=ink)
    d.rules.append(Rule(50, base_y, W - 60, base_y, 1, ink))
    add_block(d, "pay", f"Pay online at **www.{prov.split()[0].lower()}.in** or by UPI using the QR code. A late "
                        f"payment surcharge of [[1.5% per month]] applies after the due date.", 40, 880, 560, "small", 13,
              fam, color=ink, accent=acc, line_gap=1.45)
    d.objects.append(Obj("qr", W - 140, 870, 100, 100, (20, 20, 20), _seed(r)))
    return d


def email_message(r: random.Random) -> Document:
    dark = r.random() < 0.3
    base = (32, 33, 36) if dark else (255, 255, 255)
    ink = (232, 234, 237) if dark else (32, 33, 36)
    sub = (154, 160, 166) if dark else (95, 99, 104)
    bar = (41, 42, 45) if dark else (242, 246, 252)
    acc = r.choice([(26, 115, 232), (0, 137, 123), (161, 66, 244), (217, 48, 37)])
    fam = r.choice(["Poppins", "Carlito", "LiberationSans", "DejaVuSans", "FreeSans"])
    d = Document("email_message", W, H, _bg(r, base=base, texture=r.uniform(1.0, 2.5),
                                           bands=[Band(0, 0, W, 64, bar), Band(0, 64, W, 1, (60, 60, 64) if dark else (218, 220, 224))]))
    for i in range(3):
        d.objects.append(Obj("icon", 24 + i * 52, 14, 34, 34, sub, _seed(r)))
    add_block(d, "folder", "Inbox", W - 200, 20, 160, "body", 16, fam, align="right", color=sub)
    y = add_block(d, "subject", r.choice(EMAIL_SUBJECTS), 40, 92, 688, "title", 24, fam, color=ink, line_gap=1.25) + 16
    sender = _name(r)
    first, last = sender.lower().split()
    d.objects.append(Obj("avatar", 40, y, 48, 48, acc, _seed(r), sender[0]))
    add_block(d, "from", [f"**{sender}** <{first}.{last}@{r.choice(COMPANIES).split()[0].lower()}.com>", "to me"],
              104, y + 2, 460, "small", 14, fam, color=ink)
    add_block(d, "when", f"{_date(r)}, {r.randint(8, 18)}:{r.randint(10, 59)}", 520, y + 2, 208, "small", 13, fam,
              align="right", color=sub)
    y += 80
    y = add_block(d, "greet", f"Hi {_name(r).split()[0]},", 40, y, 688, "body", 15, fam, color=ink) + 14
    for i, p in enumerate(r.sample(EMAIL_BODY, 3)):
        y = add_block(d, f"p{i}", p, 40, y, 660, "body", 15, fam, color=ink, accent=acc, line_gap=1.55) + 16
    y = add_block(d, "sign", ["Best regards,", f"**{sender}**", r.choice(JOBS)], 40, y + 4, 400, "body", 15, fam,
                  color=ink, line_gap=1.5) + 30
    d.background.bands.append(Band(40, y, 280, 60, bar, 10))
    d.objects.append(Obj("icon", 54, y + 12, 36, 36, acc, _seed(r)))
    add_block(d, "att", [f"**{r.choice(['Q3_review', 'timeline_v2', 'invoice_4417', 'onboarding_pack'])}.pdf**",
                         f"{r.randint(80, 900)} KB"], 102, y + 10, 210, "small", 13, fam, color=ink)
    return d


def web_landing_page(r: random.Random) -> Document:
    acc = r.choice(ACCENTS)
    dark_hero = r.random() < 0.5
    fam = r.choice(["Poppins", "Carlito", "LiberationSans", "DejaVuSans", "FreeSans"])
    hero = tuple(int(c * 0.35 + 10) for c in acc) if dark_hero else _light(acc, 185)
    hink = (255, 255, 255) if dark_hero else (20, 20, 30)
    card = (241, 243, 247)
    d = Document("web_landing_page", W, H, _bg(r, base=(250, 250, 252), texture=r.uniform(1.0, 2.5),
                                              bands=[Band(0, 0, W, 64, (255, 255, 255)), Band(0, 64, W, 1, (225, 225, 230)),
                                                     Band(0, 65, W, 400, hero), Band(0, 930, W, 94, (30, 30, 36))]))
    brand = r.choice(STARTUPS)
    d.objects.append(Obj("logo", 24, 14, 36, 36, acc, _seed(r), brand[0]))
    add_block(d, "brand", f"**{brand}**", 70, 20, 200, "heading", 20, fam, color=(20, 20, 30))
    add_block(d, "nav", "Product    Pricing    Docs    Blog", 300, 23, 320, "small", 15, fam, color=(70, 70, 80))
    d.background.bands.append(Band(640, 14, 104, 36, acc, 18))
    add_block(d, "signup", "**Sign up**", 640, 22, 104, "small", 15, fam, align="center", color=(255, 255, 255))
    y = add_block(d, "hero", r.choice(TAGLINES), 60, 120, 640, "title", 42, fam, color=hink, line_gap=1.2) + 18
    y = add_block(d, "herosub", f"{brand} helps teams of every size work with **less friction**. Start free, invite your "
                                f"colleagues and see results in your first week.", 60, y, 600, "body", 18, fam, color=hink,
                  line_gap=1.5) + 28
    d.background.bands.append(Band(60, y, 190, 52, acc, 26))
    add_block(d, "cta", "**Start free trial**", 60, y + 15, 190, "body", 17, fam, align="center", color=(255, 255, 255))
    add_block(d, "cta2", "Book a demo", 280, y + 15, 160, "body", 17, fam, color=hink)
    add_block(d, "feat_h", "Why teams choose us", 40, 500, 688, "title", 26, fam, align="center", color=(20, 20, 30))
    for i, (t, desc) in enumerate(r.sample(FEATURES, 3)):
        x = 40 + i * 236
        d.background.bands.append(Band(x, 556, 216, 320, card, 16))
        d.objects.append(Obj("icon", x + 20, 576, 44, 44, acc, _seed(r)))
        add_block(d, f"ft{i}", f"**{t}**", x + 20, 636, 180, "body", 17, fam, color=(20, 20, 30))
        add_block(d, f"fd{i}", desc, x + 20, 668, 180, "body", 14, fam, color=(80, 80, 90), line_gap=1.55)
    add_block(d, "foot", [f"(c) 2026 {brand} Inc.  |  Privacy  |  Terms  |  Contact", f"Made in {r.choice(CITIES)}"],
              40, 955, 688, "small", 13, fam, align="center", color=(200, 200, 210), line_gap=1.6)
    return d


def chat_screenshot(r: random.Random) -> Document:
    dark = r.random() < 0.4
    base = (17, 27, 33) if dark else (236, 229, 221)
    head = (32, 44, 51) if dark else r.choice([(0, 128, 105), (18, 140, 126), (30, 110, 230)])
    inb, outb = ((32, 44, 51), (0, 92, 75)) if dark else ((255, 255, 255), (217, 253, 211))
    ink = (233, 237, 239) if dark else (17, 27, 33)
    meta = (134, 150, 160) if dark else (102, 119, 129)
    fam = r.choice(["Poppins", "Carlito", "LiberationSans", "DejaVuSans", "FreeSans"])
    d = Document("chat_screenshot", W, H, _bg(r, base=base, texture=r.uniform(2, 4),
                                             bands=[Band(0, 0, W, 96, head), Band(0, H - 84, W, 84, (32, 44, 51) if dark else (240, 240, 240)),
                                                    Band(20, H - 70, W - 120, 56, inb, 28)]))
    contact = _name(r)
    d.objects.append(Obj("avatar", 20, 18, 60, 60, r.choice(ACCENTS), _seed(r), contact[0]))
    add_block(d, "contact", f"**{contact}**", 96, 22, 400, "heading", 20, fam, color=(255, 255, 255))
    add_block(d, "status", r.choice(["online", "typing...", "last seen today at 10:12"]), 96, 54, 400, "small", 14, fam,
              color=(220, 230, 235))
    d.objects.append(Obj("icon", W - 140, 30, 36, 36, (255, 255, 255), _seed(r)))
    d.objects.append(Obj("icon", W - 80, 30, 36, 36, (255, 255, 255), _seed(r)))
    add_block(d, "day", "TODAY", 334, 112, 100, "small", 12, fam, align="center", color=meta)
    y, hh, mm = 140, r.randint(9, 20), r.randint(0, 40)
    lines = CHAT_LINES[:]
    start = r.randint(0, 2)
    for i, text in enumerate(lines[start:start + 7]):
        out = (i + start) % 2 == 1
        add_block(d, f"msg{i}", text, 0, y + 10, 420, "body", 16, fam, color=ink, line_gap=1.4)
        b = d.blocks[-1]
        tw, th = _extent(b)
        bw, bh = max(120, int(tw * 1.14) + 32), int(th) + 52
        x = W - 30 - bw if out else 30
        if y + bh > H - 110:
            d.blocks.pop()
            break
        b.x = x + 14
        d.background.bands.append(Band(x, y, bw, bh, outb if out else inb, 14))
        mm += r.randint(0, 4)
        add_block(d, f"time{i}", f"{hh}:{mm:02d}", x + bw - 70, y + bh - 20, 60, "small", 11, fam, align="right", color=meta)
        y += bh + 12
    add_block(d, "input", "Type a message", 50, H - 52, 400, "body", 17, fam, color=meta)
    d.objects.append(Obj("avatar", W - 86, H - 74, 64, 64, head if not dark else (0, 168, 132), _seed(r), ">"))
    return d


def presentation_slide(r: random.Random) -> Document:
    SW, SH = 1024, 768
    acc = r.choice(ACCENTS)
    dark = r.random() < 0.35
    base = (28, 30, 38) if dark else (252, 252, 252)
    ink = (240, 240, 245) if dark else (30, 32, 40)
    sub = (170, 172, 185) if dark else (100, 102, 112)
    fam_t, fam = _fam(r), _fam(r, "sans")
    d = Document("presentation_slide", SW, SH, _bg(r, base=base, texture=r.uniform(1, 2.5),
                                                  bands=[Band(0, 0, 18, SH, acc), Band(0, SH - 46, SW, 46, tuple(int(c * 0.92) for c in base))]))
    y = add_block(d, "title", r.choice(SLIDE_TITLES), 70, 48, 880, "title", 38, fam_t, color=ink, line_gap=1.2) + 12
    d.rules.append(Rule(70, y, 250, y, 4, acc))
    add_block(d, "bullets", [f"- {b}" for b in r.sample(BULLETS, 4)], 70, y + 32, 470, "body", 20, fam, color=ink,
              accent=acc, line_gap=1.45)
    add_block(d, "chart_h", r.choice(["Revenue by quarter (Rs. cr)", "Active users (thousands)", "Tickets resolved per week"]),
              600, y + 30, 380, "heading", 16, fam, color=ink)
    base_y = 600
    vals = [r.randint(20, 100) for _ in range(4)]
    for i, v in enumerate(vals):
        x = 620 + i * 88
        h = int(230 * v / max(vals))
        d.background.bands.append(Band(x, base_y - h, 56, h, acc if i == 3 else _light(acc, 90)))
        add_block(d, f"cv{i}", str(v), x, base_y - h - 20, 56, "small", 13, fam, align="center", color=ink)
        add_block(d, f"cl{i}", f"Q{i + 1}", x, base_y + 8, 56, "small", 13, fam, align="center", color=sub)
    d.rules.append(Rule(605, base_y, 975, base_y, 2, sub))
    d.objects.append(Obj("logo", 30, SH - 40, 34, 34, acc, _seed(r), r.choice(COMPANIES)[0]))
    add_block(d, "foot", f"{r.choice(COMPANIES)}  |  Confidential", 74, SH - 33, 500, "small", 13, fam, color=sub)
    add_block(d, "num", f"{r.randint(2, 18)} / {r.randint(19, 30)}", 860, SH - 33, 130, "small", 13, fam, align="right",
              color=sub)
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
    "bank_statement": bank_statement,
    "payslip": payslip,
    "boarding_pass": boarding_pass,
    "medical_prescription": medical_prescription,
    "resume": resume,
    "newsletter": newsletter,
    "nutrition_label": nutrition_label,
    "id_card": id_card,
    "shipping_label": shipping_label,
    "report_card": report_card,
    "utility_bill": utility_bill,
    "email_message": email_message,
    "web_landing_page": web_landing_page,
    "chat_screenshot": chat_screenshot,
    "presentation_slide": presentation_slide,
}


def build_document(template: str, seed: int) -> Document:
    return TEMPLATES[template](random.Random(seed))
