"""
Kitchen Inventory — MVP Flask App
Ejecutar: python app.py
"""

import json
import os
from collections import defaultdict
from datetime import date, timedelta

# pyrefly: ignore [missing-import]
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from models import db, Proveedor, Ingrediente, Receta, RecetaIngrediente, Produccion
from database import init_db
from logic import calcular_orden

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "kitchen-inventory-secret-2025")
db_path = os.environ.get("DB_PATH", os.path.join(BASE_DIR, "inventory.db"))
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False


db.init_app(app)
init_db(app)


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
    hoy = str(date.today())
    producciones_hoy = Produccion.query.filter_by(fecha=hoy).count()
    stock_bajo = Ingrediente.query.filter(
        Ingrediente.stock_actual <= Ingrediente.stock_minimo
    ).filter(Ingrediente.stock_minimo > 0).all()
    # Fallback: también incluir stock < 10 sin stock_minimo configurado
    sin_minimo_bajo = Ingrediente.query.filter(
        Ingrediente.stock_minimo == 0,
        Ingrediente.stock_actual < 10
    ).all()
    stock_bajo = list({i.id: i for i in stock_bajo + sin_minimo_bajo}.values())

    # Chart: producción (unidades totales) por día últimos 14 días
    labels = [(date.today() - timedelta(days=i)).isoformat() for i in range(13, -1, -1)]
    prod_por_dia: dict[str, int] = defaultdict(int)
    for p in Produccion.query.filter(Produccion.fecha >= labels[0]).all():
        prod_por_dia[p.fecha] += p.unidades
    chart_labels = json.dumps([l[5:] for l in labels])   # "MM-DD"
    chart_values = json.dumps([prod_por_dia.get(l, 0) for l in labels])

    return render_template(
        "index.html",
        stats=stats,
        ingredientes=ingredientes,
        producciones=producciones,
        producciones_hoy=producciones_hoy,
        stock_bajo=stock_bajo,
        chart_labels=chart_labels,
        chart_values=chart_values,
    )


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


@app.route("/proveedores/<int:id>/editar", methods=["POST"])
def editar_proveedor(id):
    prov = Proveedor.query.get_or_404(id)
    nombre = request.form.get("nombre", "").strip()
    contacto = request.form.get("contacto", "").strip()
    if not nombre:
        flash("El nombre es obligatorio.", "danger")
        return redirect(url_for("proveedores"))
    existente = Proveedor.query.filter_by(nombre=nombre).first()
    if existente and existente.id != id:
        flash(f"Ya existe otro proveedor con el nombre '{nombre}'.", "danger")
        return redirect(url_for("proveedores"))
    prov.nombre = nombre
    prov.contacto = contacto or None
    db.session.commit()
    flash(f"Proveedor '{nombre}' actualizado. ✅", "success")
    return redirect(url_for("proveedores"))


@app.route("/proveedores/<int:id>/eliminar", methods=["POST"])
def eliminar_proveedor(id):
    prov = Proveedor.query.get_or_404(id)
    nombre = prov.nombre
    for ing in prov.ingredientes:
        ing.proveedor_id = None
    db.session.delete(prov)
    db.session.commit()
    flash(f"Proveedor '{nombre}' eliminado. Ingredientes asociados quedaron sin proveedor.", "success")
    return redirect(url_for("proveedores"))


# ─── Ingredientes ────────────────────────────
@app.route("/ingredientes", methods=["GET", "POST"])
def ingredientes():
    if request.method == "POST":
        nombre  = request.form.get("nombre", "").strip()
        stock   = request.form.get("stock_actual", 0, type=float)
        minimo  = request.form.get("stock_minimo", 0, type=float)
        unidad  = request.form.get("unidad", "unidad").strip()
        prov_id = request.form.get("proveedor_id") or None
        if not nombre:
            flash("El nombre es obligatorio.", "danger")
            return redirect(url_for("ingredientes"))
        if Ingrediente.query.filter_by(nombre=nombre).first():
            flash(f"Ya existe un ingrediente con el nombre '{nombre}'.", "danger")
            return redirect(url_for("ingredientes"))
        db.session.add(Ingrediente(
            nombre=nombre, stock_actual=stock, stock_minimo=minimo,
            unidad=unidad, proveedor_id=prov_id
        ))
        db.session.commit()
        flash(f"Ingrediente '{nombre}' creado. ✅", "success")
        return redirect(url_for("ingredientes"))

    ings = Ingrediente.query.order_by(Ingrediente.nombre).all()
    provs = Proveedor.query.order_by(Proveedor.nombre).all()
    return render_template("ingredientes.html", ingredientes=ings, proveedores=provs)


@app.route("/ingredientes/<int:id>/editar", methods=["POST"])
def editar_ingrediente(id):
    ing = Ingrediente.query.get_or_404(id)
    nombre  = request.form.get("nombre", "").strip()
    stock   = request.form.get("stock_actual", 0, type=float)
    minimo  = request.form.get("stock_minimo", 0, type=float)
    unidad  = request.form.get("unidad", "unidad").strip()
    prov_id = request.form.get("proveedor_id") or None
    if not nombre:
        flash("El nombre es obligatorio.", "danger")
        return redirect(url_for("ingredientes"))
    existente = Ingrediente.query.filter_by(nombre=nombre).first()
    if existente and existente.id != id:
        flash(f"Ya existe otro ingrediente con el nombre '{nombre}'.", "danger")
        return redirect(url_for("ingredientes"))
    ing.nombre = nombre
    ing.stock_actual = stock
    ing.stock_minimo = minimo
    ing.unidad = unidad
    ing.proveedor_id = prov_id
    db.session.commit()
    flash(f"Ingrediente '{nombre}' actualizado. ✅", "success")
    return redirect(url_for("ingredientes"))


@app.route("/ingredientes/<int:id>/ajustar", methods=["POST"])
def ajustar_stock(id):
    ing = Ingrediente.query.get_or_404(id)
    cantidad = request.form.get("cantidad", 0, type=float)
    ing.stock_actual = max(0, ing.stock_actual + cantidad)
    db.session.commit()
    accion = "aumentado" if cantidad >= 0 else "reducido"
    flash(f"Stock de '{ing.nombre}' {accion}. Nuevo stock: {ing.stock_actual} {ing.unidad}", "success")
    return redirect(url_for("ingredientes"))


@app.route("/ingredientes/<int:id>/eliminar", methods=["POST"])
def eliminar_ingrediente(id):
    ing = Ingrediente.query.get_or_404(id)
    nombre = ing.nombre
    en_recetas = RecetaIngrediente.query.filter_by(ingrediente_id=id).count()
    if en_recetas > 0:
        flash(f"No se puede eliminar '{nombre}': está en {en_recetas} receta(s).", "danger")
        return redirect(url_for("ingredientes"))
    db.session.delete(ing)
    db.session.commit()
    flash(f"Ingrediente '{nombre}' eliminado. ✅", "success")
    return redirect(url_for("ingredientes"))


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
                    receta_id=receta.id, ingrediente_id=int(ing_id), cantidad=float(cant)
                ))
        db.session.commit()
        flash(f"Receta '{nombre}' creada. ✅", "success")
        return redirect(url_for("recetas"))

    recetas_ = Receta.query.order_by(Receta.nombre).all()
    ings  = Ingrediente.query.order_by(Ingrediente.nombre).all()
    provs = Proveedor.query.order_by(Proveedor.nombre).all()
    return render_template("recetas.html", recetas=recetas_, ingredientes=ings, proveedores=provs)


@app.route("/recetas/<int:id>/editar", methods=["POST"])
def editar_receta(id):
    receta = Receta.query.get_or_404(id)
    nombre = request.form.get("nombre", "").strip()
    desc   = request.form.get("descripcion", "").strip()
    ids_   = request.form.getlist("ingrediente_id[]")
    cants  = request.form.getlist("cantidad[]")
    if not nombre:
        flash("El nombre es obligatorio.", "danger")
        return redirect(url_for("recetas"))
    existente = Receta.query.filter_by(nombre=nombre).first()
    if existente and existente.id != id:
        flash(f"Ya existe otra receta con el nombre '{nombre}'.", "danger")
        return redirect(url_for("recetas"))
    receta.nombre = nombre
    receta.descripcion = desc or None
    # Reemplazar todos los ingredientes
    RecetaIngrediente.query.filter_by(receta_id=id).delete()
    for ing_id, cant in zip(ids_, cants):
        if ing_id and cant:
            db.session.add(RecetaIngrediente(
                receta_id=id, ingrediente_id=int(ing_id), cantidad=float(cant)
            ))
    db.session.commit()
    flash(f"Receta '{nombre}' actualizada. ✅", "success")
    return redirect(url_for("recetas"))


@app.route("/recetas/<int:id>/eliminar", methods=["POST"])
def eliminar_receta(id):
    receta = Receta.query.get_or_404(id)
    nombre = receta.nombre
    en_produccion = Produccion.query.filter_by(receta_id=id).count()
    if en_produccion > 0:
        flash(f"No se puede eliminar '{nombre}': tiene {en_produccion} producción(es) registrada(s).", "danger")
        return redirect(url_for("recetas"))
    db.session.delete(receta)
    db.session.commit()
    flash(f"Receta '{nombre}' eliminada. ✅", "success")
    return redirect(url_for("recetas"))


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

        # ── Descontar stock automáticamente ──
        for rec_id, und in zip(rec_ids, unds):
            if rec_id and und:
                receta = Receta.query.get(int(rec_id))
                if receta:
                    for ri in receta.ingredientes:
                        ri.ingrediente.stock_actual = max(
                            0, ri.ingrediente.stock_actual - ri.cantidad * int(und)
                        )

        db.session.commit()
        flash(f"Producción registrada — {count} receta(s) para {fecha}. Stock descontado automáticamente. ✅", "success")
        return redirect(url_for("produccion"))

    # Filtro por fecha o rango
    fecha_ini = request.args.get("fecha_ini", "")
    fecha_fin = request.args.get("fecha_fin", "")
    query = Produccion.query.order_by(Produccion.fecha.desc())
    if fecha_ini:
        query = query.filter(Produccion.fecha >= fecha_ini)
    if fecha_fin:
        query = query.filter(Produccion.fecha <= fecha_fin)
    prods = query.limit(100).all()
    recetas_ = Receta.query.order_by(Receta.nombre).all()
    return render_template(
        "produccion.html",
        producciones=prods,
        recetas=recetas_,
        fecha_ini=fecha_ini,
        fecha_fin=fecha_fin,
    )


@app.route("/produccion/<int:id>/eliminar", methods=["POST"])
def eliminar_produccion(id):
    prod = Produccion.query.get_or_404(id)
    nombre_receta = prod.receta.nombre if prod.receta else "?"
    fecha = prod.fecha
    db.session.delete(prod)
    db.session.commit()
    flash(f"Producción de '{nombre_receta}' ({fecha}) eliminada. ✅", "success")
    return redirect(url_for("produccion"))


# ─── Orden de Compra ─────────────────────────
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
    elif fecha_sel is None:
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
        data   = request.get_json(force=True)
        nombre = (data.get("nombre") or "").strip()
        if not nombre:
            return jsonify({"error": "nombre es obligatorio"}), 400
        if Ingrediente.query.filter_by(nombre=nombre).first():
            return jsonify({"error": f"Ingrediente '{nombre}' ya existe"}), 409
        ing = Ingrediente(
            nombre=nombre,
            stock_actual=data.get("stock_actual", 0),
            stock_minimo=data.get("stock_minimo", 0),
            unidad=data.get("unidad", "unidad"),
            proveedor_id=data.get("proveedor_id"),
        )
        db.session.add(ing)
        db.session.commit()
        return jsonify(ing.to_dict()), 201
    return jsonify([i.to_dict() for i in Ingrediente.query.all()])

@app.route("/api/ingredientes/<int:id>/stock", methods=["POST"])
def api_update_stock(id):
    ing = Ingrediente.query.get_or_404(id)
    data = request.get_json(force=True)
    nuevo_stock = data.get("stock_actual")
    if nuevo_stock is not None:
        ing.stock_actual = float(nuevo_stock)
        db.session.commit()
    return jsonify(ing.to_dict())


@app.route("/api/proveedores", methods=["GET", "POST"])
def api_proveedores():
    if request.method == "POST":
        data   = request.get_json(force=True)
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
        data   = request.get_json(force=True)
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


@app.route("/api/recetas/<int:id>")
def api_receta_detail(id):
    r = Receta.query.get_or_404(id)
    return jsonify(r.to_dict())


@app.route("/api/produccion", methods=["GET", "POST"])
def api_produccion():
    if request.method == "POST":
        data  = request.get_json(force=True)
        fecha = data.get("fecha") or str(date.today())
        items = data.get("items", [])
        if not items:
            return jsonify({"error": "items es obligatorio"}), 400
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
    if request.method == "POST":
        data  = request.get_json(force=True)
        ids_  = data.get("produccion_ids")
        fecha = data.get("fecha")
        if ids_:
            prods = [p for p in (Produccion.query.get(i) for i in ids_) if p]
        elif fecha:
            prods = Produccion.query.filter_by(fecha=fecha).all()
        else:
            prods = Produccion.query.all()
    else:
        fecha = request.args.get("fecha")
        prods = Produccion.query.filter_by(fecha=fecha).all() if fecha else Produccion.query.all()

    if not prods:
        return jsonify({"error": "No hay producción para los criterios dados."}), 404
    return jsonify(calcular_orden(prods))


@app.route("/api/proyectar_orden", methods=["POST"])
def api_proyectar_orden():
    """Recibe items de producción hipotética y devuelve los faltantes."""
    data = request.get_json(force=True)
    items = data.get("items", [])
    
    from collections import defaultdict
    necesidades = defaultdict(float)
    
    # Calcular necesidades totales
    for item in items:
        rec_id = item.get("receta_id")
        unds = item.get("unidades")
        if not rec_id or not unds:
            continue
        receta = Receta.query.get(rec_id)
        if receta:
            for ri in receta.ingredientes:
                necesidades[ri.ingrediente_id] += ri.cantidad * int(unds)
                
    faltantes = []
    orden_por_proveedor = defaultdict(list)
    
    for ing_id, total_necesario in necesidades.items():
        ing = Ingrediente.query.get(ing_id)
        if not ing:
            continue
        diferencia = total_necesario - ing.stock_actual
        if diferencia > 0:
            proveedor_nombre = ing.proveedor.nombre if ing.proveedor else "Sin proveedor"
            faltante = {
                "ingrediente_id": ing.id,
                "ingrediente": ing.nombre,
                "stock_actual": ing.stock_actual,
                "necesario": total_necesario,
                "faltante": round(diferencia, 2),
                "unidad": ing.unidad,
                "proveedor": proveedor_nombre,
            }
            faltantes.append(faltante)
            orden_por_proveedor[proveedor_nombre].append({
                "ingrediente_id": ing.id,
                "ingrediente": ing.nombre,
                "cantidad_a_pedir": round(diferencia, 2),
                "unidad": ing.unidad,
            })
            
    return jsonify({
        "faltantes": faltantes,
        "orden_por_proveedor": dict(orden_por_proveedor)
    })


if __name__ == "__main__":
    import socket
    hostname = socket.gethostname()
    local_ip = "(no disponible)"
    try:
        local_ip = socket.gethostbyname(hostname)
    except Exception:
        pass
    print("\n" + "═" * 50)
    print("🍔  Kitchen Inventory — SERVIDOR CORRIENDO")
    print("═" * 50)
    print(f"  → Local:      http://127.0.0.1:8080")
    print(f"  → Red local:  http://{local_ip}:8080")
    print("═" * 50 + "\n")
    app.run(debug=False, host="0.0.0.0", port=8080)
