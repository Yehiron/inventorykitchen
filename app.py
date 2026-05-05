"""
Kitchen Inventory — MVP Flask App
Ejecutar: python app.py
"""

import os
from datetime import date
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from models import db, Proveedor, Ingrediente, Receta, RecetaIngrediente, Produccion
from database import init_db
from logic import calcular_orden

# ──────────────────────────────────────────────
# Configuración
# ──────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__)
app.config["SECRET_KEY"] = "kitchen-inventory-secret-2025"
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{os.path.join(BASE_DIR, 'inventory.db')}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

# ══════════════════════════════════════════════
# ██  RUTAS HTML  ██
# ══════════════════════════════════════════════

# ─── Dashboard ───────────────────────────────
@app.route("/")
def index():
    stats = {
        "ingredientes": Ingrediente.query.count(),
        "recetas": Receta.query.count(),
        "proveedores": Proveedor.query.count(),
    }
    ingredientes = Ingrediente.query.all()
    producciones = Produccion.query.order_by(Produccion.fecha.desc()).limit(10).all()
    return render_template("index.html", stats=stats, ingredientes=ingredientes, producciones=producciones)


# ─── Proveedores ─────────────────────────────
@app.route("/proveedores", methods=["GET", "POST"])
def proveedores():
    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        contacto = request.form.get("contacto", "").strip()
        if not nombre:
            flash("El nombre es obligatorio.", "danger")
            return redirect(url_for("proveedores"))
        if Proveedor.query.filter_by(nombre=nombre).first():
            flash(f"Ya existe un proveedor con el nombre '{nombre}'.", "danger")
            return redirect(url_for("proveedores"))
        db.session.add(Proveedor(nombre=nombre, contacto=contacto or None))
        db.session.commit()
        flash(f"Proveedor '{nombre}' creado correctamente. ✅", "success")
        return redirect(url_for("proveedores"))

    proveedores_ = Proveedor.query.order_by(Proveedor.nombre).all()
    return render_template("proveedores.html", proveedores=proveedores_)


# ─── Ingredientes ────────────────────────────
@app.route("/ingredientes", methods=["GET", "POST"])
def ingredientes():
    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        stock  = request.form.get("stock_actual", 0, type=float)
        unidad = request.form.get("unidad", "unidad").strip()
        prov_id = request.form.get("proveedor_id") or None
        if not nombre:
            flash("El nombre es obligatorio.", "danger")
            return redirect(url_for("ingredientes"))
        if Ingrediente.query.filter_by(nombre=nombre).first():
            flash(f"Ya existe un ingrediente con el nombre '{nombre}'.", "danger")
            return redirect(url_for("ingredientes"))
        db.session.add(Ingrediente(nombre=nombre, stock_actual=stock, unidad=unidad, proveedor_id=prov_id))
        db.session.commit()
        flash(f"Ingrediente '{nombre}' creado correctamente. ✅", "success")
        return redirect(url_for("ingredientes"))

    ings = Ingrediente.query.order_by(Ingrediente.nombre).all()
    provs = Proveedor.query.order_by(Proveedor.nombre).all()
    return render_template("ingredientes.html", ingredientes=ings, proveedores=provs)


# ─── Recetas ─────────────────────────────────
@app.route("/recetas", methods=["GET", "POST"])
def recetas():
    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        desc   = request.form.get("descripcion", "").strip()
        ids_   = request.form.getlist("ingrediente_id[]")
        cants  = request.form.getlist("cantidad[]")

        if not nombre:
            flash("El nombre de la receta es obligatorio.", "danger")
            return redirect(url_for("recetas"))
        if Receta.query.filter_by(nombre=nombre).first():
            flash(f"Ya existe la receta '{nombre}'.", "danger")
            return redirect(url_for("recetas"))

        receta = Receta(nombre=nombre, descripcion=desc or None)
        db.session.add(receta)
        db.session.flush()

        for ing_id, cant in zip(ids_, cants):
            if ing_id and cant:
                db.session.add(RecetaIngrediente(
                    receta_id=receta.id,
                    ingrediente_id=int(ing_id),
                    cantidad=float(cant),
                ))

        db.session.commit()
        flash(f"Receta '{nombre}' creada correctamente. ✅", "success")
        return redirect(url_for("recetas"))

    recetas_ = Receta.query.order_by(Receta.nombre).all()
    ings = Ingrediente.query.order_by(Ingrediente.nombre).all()
    return render_template("recetas.html", recetas=recetas_, ingredientes=ings)


# ─── Producción ──────────────────────────────
@app.route("/produccion", methods=["GET", "POST"])
def produccion():
    if request.method == "POST":
        fecha   = request.form.get("fecha") or str(date.today())
        rec_ids = request.form.getlist("receta_id[]")
        unds    = request.form.getlist("unidades[]")

        if not rec_ids:
            flash("Debes registrar al menos una receta.", "danger")
            return redirect(url_for("produccion"))

        count = 0
        for rec_id, und in zip(rec_ids, unds):
            if rec_id and und:
                db.session.add(Produccion(fecha=fecha, receta_id=int(rec_id), unidades=int(und)))
                count += 1

        db.session.commit()
        flash(f"Producción registrada — {count} receta(s) para {fecha}. ✅", "success")
        return redirect(url_for("produccion"))

    prods = Produccion.query.order_by(Produccion.fecha.desc()).limit(20).all()
    recetas_ = Receta.query.order_by(Receta.nombre).all()
    return render_template("produccion.html", producciones=prods, recetas=recetas_)


# ─── Orden de Compra (HTML) ──────────────────
@app.route("/orden")
def orden():
    fecha_sel = request.args.get("fecha")

    query = Produccion.query
    if fecha_sel:
        query = query.filter_by(fecha=fecha_sel)
    prods = query.all()

    resultado = None
    if prods:
        resultado = calcular_orden(prods)
    elif request.args.get("fecha") is None:
        # Sin filtro: calcular sobre toda la producción
        all_prods = Produccion.query.all()
        if all_prods:
            resultado = calcular_orden(all_prods)

    return render_template("orden.html", resultado=resultado, fecha_sel=fecha_sel)


# ══════════════════════════════════════════════
# ██  API JSON  ██
# ══════════════════════════════════════════════

@app.route("/api/ingredientes", methods=["GET", "POST"])
def api_ingredientes():
    if request.method == "POST":
        data = request.get_json(force=True)
        nombre = (data.get("nombre") or "").strip()
        if not nombre:
            return jsonify({"error": "nombre es obligatorio"}), 400
        if Ingrediente.query.filter_by(nombre=nombre).first():
            return jsonify({"error": f"Ingrediente '{nombre}' ya existe"}), 409
        ing = Ingrediente(
            nombre=nombre,
            stock_actual=data.get("stock_actual", 0),
            unidad=data.get("unidad", "unidad"),
            proveedor_id=data.get("proveedor_id"),
        )
        db.session.add(ing)
        db.session.commit()
        return jsonify(ing.to_dict()), 201
    return jsonify([i.to_dict() for i in Ingrediente.query.all()])


@app.route("/api/proveedores", methods=["GET", "POST"])
def api_proveedores():
    if request.method == "POST":
        data = request.get_json(force=True)
        nombre = (data.get("nombre") or "").strip()
        if not nombre:
            return jsonify({"error": "nombre es obligatorio"}), 400
        if Proveedor.query.filter_by(nombre=nombre).first():
            return jsonify({"error": f"Proveedor '{nombre}' ya existe"}), 409
        p = Proveedor(nombre=nombre, contacto=data.get("contacto"))
        db.session.add(p)
        db.session.commit()
        return jsonify(p.to_dict()), 201
    return jsonify([p.to_dict() for p in Proveedor.query.all()])


@app.route("/api/recetas", methods=["GET", "POST"])
def api_recetas():
    if request.method == "POST":
        data = request.get_json(force=True)
        nombre = (data.get("nombre") or "").strip()
        if not nombre:
            return jsonify({"error": "nombre es obligatorio"}), 400
        if Receta.query.filter_by(nombre=nombre).first():
            return jsonify({"error": f"Receta '{nombre}' ya existe"}), 409
        r = Receta(nombre=nombre, descripcion=data.get("descripcion"))
        db.session.add(r)
        db.session.flush()
        for item in data.get("ingredientes", []):
            db.session.add(RecetaIngrediente(
                receta_id=r.id,
                ingrediente_id=item["ingrediente_id"],
                cantidad=item["cantidad"],
            ))
        db.session.commit()
        return jsonify(r.to_dict()), 201
    return jsonify([r.to_dict() for r in Receta.query.all()])


@app.route("/api/produccion", methods=["GET", "POST"])
def api_produccion():
    if request.method == "POST":
        data = request.get_json(force=True)
        fecha = data.get("fecha") or str(date.today())
        items = data.get("items", [])
        if not items:
            return jsonify({"error": "items es obligatorio y no puede estar vacío"}), 400
        creados = []
        for item in items:
            p = Produccion(fecha=fecha, receta_id=item["receta_id"], unidades=item["unidades"])
            db.session.add(p)
            db.session.flush()
            creados.append(p.to_dict())
        db.session.commit()
        return jsonify(creados), 201
    return jsonify([p.to_dict() for p in Produccion.query.order_by(Produccion.fecha.desc()).all()])


@app.route("/api/generar_orden", methods=["GET", "POST"])
def api_generar_orden():
    """
    GET  → calcula sobre TODA la producción (o filtra por ?fecha=YYYY-MM-DD)
    POST → body: {"fecha": "2025-06-01"} o {"produccion_ids": [1,2,3]}
    """
    if request.method == "POST":
        data = request.get_json(force=True)
        fecha = data.get("fecha")
        ids_  = data.get("produccion_ids")
        if ids_:
            prods = [Produccion.query.get(i) for i in ids_]
            prods = [p for p in prods if p]
        elif fecha:
            prods = Produccion.query.filter_by(fecha=fecha).all()
        else:
            prods = Produccion.query.all()
    else:
        fecha = request.args.get("fecha")
        if fecha:
            prods = Produccion.query.filter_by(fecha=fecha).all()
        else:
            prods = Produccion.query.all()

    if not prods:
        return jsonify({"error": "No hay producción registrada para los criterios dados."}), 404

    resultado = calcular_orden(prods)
    return jsonify(resultado)


# ══════════════════════════════════════════════
# ██  ENTRY POINT  ██
# ══════════════════════════════════════════════

if __name__ == "__main__":
    init_db(app)
    import socket
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    print("\n" + "═" * 50)
    print("🍔  Kitchen Inventory — SERVIDOR CORRIENDO")
    print("═" * 50)
    print(f"  → Desde ESTE computador: http://127.0.0.1:5000")
    print(f"  → Desde la red local:    http://{local_ip}:5000")
    print("  Comparte la dirección de red local con tus empleados")
    print("═" * 50 + "\n")
    app.run(debug=False, host="0.0.0.0", port=5000)
