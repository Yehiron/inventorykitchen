from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Proveedor(db.Model):
    __tablename__ = "proveedores"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False, unique=True)
    contacto = db.Column(db.String(100))

    ingredientes = db.relationship("Ingrediente", backref="proveedor", lazy=True)

    def to_dict(self):
        return {
            "id": self.id,
            "nombre": self.nombre,
            "contacto": self.contacto,
        }


class Ingrediente(db.Model):
    __tablename__ = "ingredientes"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False, unique=True)
    stock_actual = db.Column(db.Float, nullable=False, default=0)
    stock_minimo = db.Column(db.Float, nullable=False, default=0)
    unidad = db.Column(db.String(20), nullable=False, default="unidad")
    proveedor_id = db.Column(db.Integer, db.ForeignKey("proveedores.id"), nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "nombre": self.nombre,
            "stock_actual": self.stock_actual,
            "stock_minimo": self.stock_minimo,
            "unidad": self.unidad,
            "proveedor_id": self.proveedor_id,
            "proveedor": self.proveedor.nombre if self.proveedor else None,
        }


class Receta(db.Model):
    __tablename__ = "recetas"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False, unique=True)
    descripcion = db.Column(db.String(255))

    ingredientes = db.relationship("RecetaIngrediente", backref="receta", lazy=True, cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "nombre": self.nombre,
            "descripcion": self.descripcion,
            "ingredientes": [ri.to_dict() for ri in self.ingredientes],
        }


class RecetaIngrediente(db.Model):
    __tablename__ = "receta_ingredientes"

    id = db.Column(db.Integer, primary_key=True)
    receta_id = db.Column(db.Integer, db.ForeignKey("recetas.id"), nullable=False)
    ingrediente_id = db.Column(db.Integer, db.ForeignKey("ingredientes.id"), nullable=False)
    cantidad = db.Column(db.Float, nullable=False)

    ingrediente = db.relationship("Ingrediente")

    def to_dict(self):
        return {
            "ingrediente_id": self.ingrediente_id,
            "ingrediente": self.ingrediente.nombre if self.ingrediente else None,
            "cantidad": self.cantidad,
            "unidad": self.ingrediente.unidad if self.ingrediente else None,
        }


class Produccion(db.Model):
    __tablename__ = "produccion"

    id = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.String(20), nullable=False)
    receta_id = db.Column(db.Integer, db.ForeignKey("recetas.id"), nullable=False)
    unidades = db.Column(db.Integer, nullable=False)

    receta = db.relationship("Receta")

    def to_dict(self):
        return {
            "id": self.id,
            "fecha": self.fecha,
            "receta_id": self.receta_id,
            "receta": self.receta.nombre if self.receta else None,
            "unidades": self.unidades,
        }
