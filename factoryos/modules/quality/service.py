class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        canvas.Canvas.__init__(self, *args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)

        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.setFont("Helvetica", 9)
            self.drawRightString(A4[0] - 2 * cm, 1.0 * cm, f"Seite {self._pageNumber} von {num_pages}")
            canvas.Canvas.showPage(self)

        canvas.Canvas.save(self)



class MarkerOverlay(Flowable):

    def __init__(self, markers):
        Flowable.__init__(self)
        self.markers = markers
        self.width = 16*cm
        self.height = 12*cm

    def draw(self):

        for m in self.markers:

            x = m["x"] * self.width
            y = (1 - m["y"]) * self.height

            # Kreis
            self.canv.setFillColor(colors.red)
            self.canv.circle(x, y, 8, fill=1)

            # Nummer
            self.canv.setFillColor(colors.white)
            self.canv.setFont("Helvetica-Bold",8)

            self.canv.drawCentredString(
                x,
                y-3,
                str(m["nr"])
            )

def generate_plan_pdf(version):

    # 1️⃣ Absoluter Static-Pfad deiner App
    folder = os.path.join(app.static_folder, "qm_snapshots")
    os.makedirs(folder, exist_ok=True)

    file_name = f"plan_{version.id}.pdf"
    file_path = os.path.join(folder, file_name)

    # 2️⃣ PDF erzeugen
    doc = SimpleDocTemplate(file_path)
    elements = []

    styles = getSampleStyleSheet()

    elements.append(Paragraph(
        f"Prüfplan Revision {version.revision}",
        styles["Heading1"]
    ))

    doc.build(elements)

    # 3️⃣ Nur relativen Pfad speichern!
    return f"qm_snapshots/{file_name}"


def calibration_status(gauge):

    # Messmittel deaktiviert
    if gauge.status == "inactive":
        return "inactive"

    if not gauge.next_calibration:
        return "unknown"

    today = datetime.today().date()

    diff = (gauge.next_calibration - today).days

    if diff < 0:
        return "expired"

    elif diff <= 30:
        return "warning"

    else:
        return "ok"

def log_change(version, action, message):

    log = QualityInspectionChangeLog(
        plan_id = version.plan.id,
        action = action,
        message = message,
        user_id = current_user.id
    )

    db.session.add(log)

def increase_revision(plan):

    if not plan.revision:
        plan.revision = "1.0"
        return

    try:
        major, minor = plan.revision.split(".")
        minor = int(minor) + 1
        plan.revision = f"{major}.{minor}"
    except:
        plan.revision = "1.0"


def draw_markers_on_image(image_path, characteristics):

    full_path = image_path

    img = load_drawing_image(full_path)

    width, height = img.size
    draw = ImageDraw.Draw(img)

    font_size = int(height * 0.022)

    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", font_size)
    except:
        font = ImageFont.load_default()

    r = int(height * 0.014)

    for c in sorted(characteristics, key=lambda x: x.sort_order or 0):

        if c.pos_x is None or c.pos_y is None:
            continue

        pos_x = float(c.pos_x)
        pos_y = float(c.pos_y)

        if pos_x > 1:
            pos_x /= 100
        if pos_y > 1:
            pos_y /= 100

        x = int(pos_x * width)
        y = int(pos_y * height)

        # Kreis
        draw.ellipse(
            (x-r, y-r, x+r, y+r),
            fill=(220,0,0),
            outline=(0,0,0),
            width=2
        )

        # TEXT automatisch zentrieren
        draw.text(
            (x, y),
            str(c.sort_order),
            fill=(255,255,255),
            font=font,
            anchor="mm"
        )

    output = BytesIO()
    img.save(output, format="PNG")
    output.seek(0)

    return output

def load_drawing_image(image_path):

    ext = image_path.lower().split(".")[-1]

    # PDF Zeichnung
    if ext == "pdf":

        pages = convert_from_path(
            image_path,
            dpi=300,
            poppler_path="/usr/bin"
        )

        img = pages[0].convert("RGB")

        return img

    # TIFF Zeichnung
    if ext in ["tif","tiff"]:

        img = PILImage.open(image_path)

        try:
            img.seek(0)
        except:
            pass

        return img.convert("RGB")

    # normale Bilder
    return PILImage.open(image_path).convert("RGB")
