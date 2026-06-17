from datetime import date
from models import db, Proveedor, Ingrediente, Receta, RecetaIngrediente, Produccion


def init_db(app):
    """Crea las tablas si no existen e inserta datos de prueba."""
    with app.app_context():
        db.create_all()
        _migrate(app)
        _seed_data()


def _migrate(app):
    """Migraciones ligeras para columnas nuevas."""
    from sqlalchemy import text
    with app.app_context():
        try:
            db.session.execute(text("ALTER TABLE ingredientes ADD COLUMN stock_minimo FLOAT NOT NULL DEFAULT 0"))
            db.session.commit()
        except Exception:
            db.session.rollback()  # columna ya existe, ignorar


def _seed_data():
    """Inserta datos de prueba solo si la BD está vacía."""
    if Proveedor.query.first():
        return  # ya tiene datos

    # Proveedores 
    p1 = Proveedor(nombre="Distribuidora FrescoMar", contacto="frescoMar@gmail.com")
    p2 = Proveedor(nombre="Carnicos Premium S.A.", contacto="carnicos@premium.com")
    db.session.add_all([p1, p2])
    db.session.flush()  # para obtener IDs

    #  Ingredientes 
    i1 = Ingrediente(nombre="Pan de hamburguesa", stock_actual=50, unidad="piezas", proveedor_id=p1.id)
    i2 = Ingrediente(nombre="Carne molida 150g", stock_actual=30, unidad="porciones", proveedor_id=p2.id)
    i3 = Ingrediente(nombre="Queso cheddar", stock_actual=20, unidad="rebanadas", proveedor_id=p1.id)
    i4 = Ingrediente(nombre="Lechuga", stock_actual=40, unidad="hojas", proveedor_id=p1.id)
    i5 = Ingrediente(nombre="Tocino", stock_actual=15, unidad="tiras", proveedor_id=p2.id)
    db.session.add_all([i1, i2, i3, i4, i5])
    db.session.flush()

    # Recetas 
    r1 = Receta(nombre="Hamburguesa Clásica", descripcion="Pan, carne y lechuga")
    r2 = Receta(nombre="Hamburguesa BBQ", descripcion="Pan, carne, queso y tocino")
    db.session.add_all([r1, r2])
    db.session.flush()

    # Receta Ingredientes
    db.session.add_all([
        RecetaIngrediente(receta_id=r1.id, ingrediente_id=i1.id, cantidad=1),
        RecetaIngrediente(receta_id=r1.id, ingrediente_id=i2.id, cantidad=1),
        RecetaIngrediente(receta_id=r1.id, ingrediente_id=i4.id, cantidad=2),
        RecetaIngrediente(receta_id=r2.id, ingrediente_id=i1.id, cantidad=1),
        RecetaIngrediente(receta_id=r2.id, ingrediente_id=i2.id, cantidad=1),
        RecetaIngrediente(receta_id=r2.id, ingrediente_id=i3.id, cantidad=2),
        RecetaIngrediente(receta_id=r2.id, ingrediente_id=i5.id, cantidad=3),
    ])

    db.session.commit()
    print("Datos de prueba insertados correctamente.")
