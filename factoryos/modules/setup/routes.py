@app.route("/admin/setup")
@login_required
@role_required("admin")
def admin_setup_home():
    return render_template("admin_setup_home.html")

@app.route("/admin/setup/company", methods=["GET", "POST"])
@login_required
@role_required("admin")
def admin_setup_company():
    s = AppSettings.query.first()
    if not s:
        s = AppSettings(company_name="Meine Firma")
        db.session.add(s)
        db.session.commit()

    if request.method == "POST":
        s.company_name = request.form.get("company_name", "").strip() or None
        s.company_address = request.form.get("company_address", "").strip() or None

        # Logo Upload
        f = request.files.get("logo")
        if f and f.filename:
            filename = secure_filename(f.filename)

            ext = filename.rsplit(".", 1)[-1].lower()
            if ext not in ["png", "jpg", "jpeg"]:
                flash("Logo nur als PNG/JPG erlaubt.", "danger")
                return redirect(url_for("admin_setup_company"))

            upload_dir = os.path.join(app.root_path, "static", "uploads")
            os.makedirs(upload_dir, exist_ok=True)

            new_name = f"company_logo.{ext}"
            save_path = os.path.join(upload_dir, new_name)
            f.save(save_path)

            s.logo_filename = new_name

        db.session.commit()
        flash("Firmeneinstellungen gespeichert.", "success")
        return redirect(url_for("admin_setup_company"))

    return render_template("admin_setup_company.html", s=s)