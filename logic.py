from collections import defaultdict
from models import Produccion, Receta, Ingrediente, RecetaIngrediente


def calcular_orden(producciones_ids: list[int]) -> dict:
    """
    Recibe una lista de IDs de registros Produccion ya guardados,
    calcula faltantes y genera la orden agrupada por proveedor.
    """
    resumen_produccion = []
    necesidades: dict[int, float] = defaultdict(float)  # ingrediente_id  total necesario

    for prod in producciones_ids:
        if isinstance(prod, Produccion):
            p = prod
        else:
            p = Produccion.query.get(prod)
        if not p:
            continue

        receta = Receta.query.get(p.receta_id)
        if not receta:
            continue

        resumen_produccion.append({
            "receta": receta.nombre,
            "unidades": p.unidades,
        })

        for ri in receta.ingredientes:
            necesidades[ri.ingrediente_id] += ri.cantidad * p.unidades

    faltantes = []
    orden_por_proveedor: dict[str, list] = defaultdict(list)

    for ing_id, total_necesario in necesidades.items():
        ing = Ingrediente.query.get(ing_id)
        if not ing:
            continue

        diferencia = total_necesario - ing.stock_actual
        if diferencia > 0:
            faltante = {
                "ingrediente_id": ing.id,
                "ingrediente": ing.nombre,
                "stock_actual": ing.stock_actual,
                "necesario": total_necesario,
                "faltante": diferencia,
                "unidad": ing.unidad,
                "proveedor": ing.proveedor.nombre if ing.proveedor else "Sin proveedor",
            }
            faltantes.append(faltante)

            proveedor_nombre = ing.proveedor.nombre if ing.proveedor else "Sin proveedor"
            orden_por_proveedor[proveedor_nombre].append({
                "ingrediente": ing.nombre,
                "cantidad_a_pedir": round(diferencia, 2),
                "unidad": ing.unidad,
            })

    return {
        "produccion": resumen_produccion,
        "faltantes": faltantes,
        "orden_por_proveedor": dict(orden_por_proveedor),
    }
