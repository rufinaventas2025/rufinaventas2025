from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_mail import Mail, Message
import json
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "mi_clave_segura"

# --- Configuración Flask-Mail ---
app.config["MAIL_SERVER"] = "smtp.gmail.com"
app.config["MAIL_PORT"] = 587
app.config["MAIL_USE_TLS"] = True
app.config["MAIL_USE_SSL"] = False
app.config["MAIL_USERNAME"] = "rufina.ventas2025@gmail.com"
app.config["MAIL_PASSWORD"] = "hkgl ebhd bsop pozg"  # Contraseña de aplicación
app.config["MAIL_DEFAULT_SENDER"] = "rufina.ventas2025@gmail.com"

mail = Mail(app)

# --- Archivos e imágenes ---
ARTICULOS_FILE = "data/articulos.json"
UPLOAD_FOLDER = "static/images"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

os.makedirs("data", exist_ok=True)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# --- Funciones auxiliares ---
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def leer_articulos():
    if os.path.exists(ARTICULOS_FILE):
        with open(ARTICULOS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def guardar_articulos(articulos):
    with open(ARTICULOS_FILE, "w", encoding="utf-8") as f:
        json.dump(articulos, f, indent=4, ensure_ascii=False)

# --- Rutas ---
@app.route("/")
def index():
    articulos = leer_articulos()
    carrito = session.get("carrito", [])
    total = sum(item["precio"] * item["cantidad"] for item in carrito)
    return render_template("index.html", articulos=articulos, carrito=carrito, total=total)

# Agregar al carrito (verifica stock)
@app.route("/agregar/<nombre>")
def agregar(nombre):
    articulos = leer_articulos()
    articulo = next((a for a in articulos if a["nombre"] == nombre), None)
    if not articulo:
        flash("Artículo no encontrado")
        return redirect(url_for("index"))

    carrito = session.get("carrito", [])
    existente = next((i for i in carrito if i["nombre"] == nombre), None)
    cantidad_en_carrito = existente["cantidad"] if existente else 0

    if articulo.get("stock", 0) <= cantidad_en_carrito:
        flash(f"No hay más stock disponible de '{nombre}'. Disponible: {articulo.get('stock',0)}")
        return redirect(url_for("index"))

    if existente:
        existente["cantidad"] += 1
    else:
        carrito.append({
            "nombre": articulo["nombre"],
            "precio": articulo["precio"],
            "cantidad": 1
        })

    session["carrito"] = carrito
    flash(f"{nombre} agregado al carrito.")
    return redirect(url_for("index"))

# Vaciar carrito
@app.route("/vaciar")
def vaciar():
    session.pop("carrito", None)
    flash("Carrito vaciado.")
    return redirect(url_for("index"))

# Finalizar compra (verifica stock y descuenta)
@app.route("/finalizar", methods=["POST"])
def finalizar():
    nombre = request.form.get("nombre")
    correo = request.form.get("correo")
    telefono = request.form.get("telefono")
    carrito = session.get("carrito", [])

    if not carrito:
        flash("El carrito está vacío.")
        return redirect(url_for("index"))

    if not nombre or not correo or not telefono:
        flash("Por favor, complete todos los campos.")
        return redirect(url_for("index"))

    articulos = leer_articulos()
    faltantes = []

    for item in carrito:
        art = next((a for a in articulos if a["nombre"] == item["nombre"]), None)
        if not art:
            faltantes.append(f"{item['nombre']} (no existe)")
            continue
        if art["stock"] < item["cantidad"]:
            faltantes.append(f"{item['nombre']} (disponible: {art['stock']}, pedido: {item['cantidad']})")

    if faltantes:
        flash("No se puede completar la compra. Problemas con stock: " + "; ".join(faltantes))
        return redirect(url_for("index"))

    # Descontar stock
    for item in carrito:
        art = next((a for a in articulos if a["nombre"] == item["nombre"]), None)
        if art:
            art["stock"] -= item["cantidad"]
            if art["stock"] < 0:
                art["stock"] = 0
    guardar_articulos(articulos)

    # Enviar correo
    total = sum(item["precio"] * item["cantidad"] for item in carrito)
    productos = "\n".join([f"{i['nombre']} x{i['cantidad']} = ${i['precio']*i['cantidad']}" for i in carrito])
    try:
        msg = Message(
            subject=f"Pedido de {nombre}",
            recipients=["rufina.ventas2025@gmail.com"]
        )
        msg.body = f"""
Nueva compra desde la tienda:

Nombre: {nombre}
Correo: {correo}
Teléfono: {telefono}

Productos:
{productos}

Total: ${total:.2f}
"""
        mail.send(msg)
        flash("Compra finalizada. Te contactaremos pronto 💌")
    except Exception as e:
        flash(f"No se pudo enviar el correo: {str(e)}")

    session.pop("carrito", None)
    return redirect(url_for("index"))

# --- Administración ---
@app.route("/clave")
def clave():
    return render_template("clave.html")

@app.route("/admin", methods=["GET", "POST"])
def admin():
    articulos = leer_articulos()
    if request.method == "POST":
        nombre = request.form.get("nombre")
        precio = request.form.get("precio")
        stock = request.form.get("stock")
        archivos = request.files.getlist("imagenes")

        if not nombre or not precio or not stock or not archivos:
            flash("Todos los campos son obligatorios")
            return redirect(url_for("admin"))

        try:
            precio = float(precio)
            stock = int(stock)
        except ValueError:
            flash("Precio o stock inválidos")
            return redirect(url_for("admin"))

        imagenes_guardadas = []
        for archivo in archivos:
            if archivo and allowed_file(archivo.filename):
                filename = secure_filename(archivo.filename)
                archivo.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
                imagenes_guardadas.append(filename)

        if not imagenes_guardadas:
            flash("Debe subir al menos una imagen válida")
            return redirect(url_for("admin"))

        articulos.append({
            "nombre": nombre,
            "precio": precio,
            "stock": stock,
            "imagenes": imagenes_guardadas
        })
        guardar_articulos(articulos)
        flash("Artículo agregado correctamente")
        return redirect(url_for("admin"))

    return render_template("admin.html", articulos=articulos)

@app.route("/eliminar/<nombre_articulo>")
def eliminar(nombre_articulo):
    articulos = leer_articulos()
    articulos = [a for a in articulos if a["nombre"] != nombre_articulo]
    guardar_articulos(articulos)
    flash(f"Artículo {nombre_articulo} eliminado")
    return redirect(url_for("admin"))

if __name__ == "__main__":
    app.run(debug=True)
