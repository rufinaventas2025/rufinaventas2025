# app.py
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_mail import Mail, Message
import json
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "mi_clave_segura"

# --- CONFIGURACIÓN CORREO ---
app.config["MAIL_SERVER"] = "smtp.gmail.com"
app.config["MAIL_PORT"] = 587
app.config["MAIL_USE_TLS"] = True
app.config["MAIL_USE_SSL"] = False
app.config["MAIL_USERNAME"] = "rufina.ventas2025@gmail.com"
app.config["MAIL_PASSWORD"] = "hkgl ebhd bsop pozg"
app.config["MAIL_DEFAULT_SENDER"] = "rufina.ventas2025@gmail.com"

mail = Mail(app)

# --- ARCHIVOS E IMÁGENES ---
ARTICULOS_FILE = "data/articulos.json"
UPLOAD_FOLDER = "static/images"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

os.makedirs("data", exist_ok=True)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# --- FUNCIONES AUXILIARES ---
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

# --- RUTAS ---
@app.route("/")
def index():
    articulos = leer_articulos()
    return render_template("index.html", articulos=articulos)

@app.route("/agregar", methods=["GET", "POST"])
def agregar():
    if request.method == "POST":
        nombre = request.form.get("nombre")
        precio = request.form.get("precio")
        stock = request.form.get("stock")
        archivos = request.files.getlist("imagenes")  # ahora múltiples archivos

        if not nombre or not precio or not stock or not archivos:
            flash("Todos los campos son obligatorios")
            return redirect(url_for("agregar"))

        try:
            precio = float(precio)
            stock = int(stock)
        except ValueError:
            flash("Precio o stock inválidos")
            return redirect(url_for("agregar"))

        imagenes_guardadas = []
        for archivo in archivos:
            if archivo and allowed_file(archivo.filename):
                filename = secure_filename(archivo.filename)
                filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
                archivo.save(filepath)
                imagenes_guardadas.append(filename)

        if not imagenes_guardadas:
            flash("Debe subir al menos una imagen válida.")
            return redirect(url_for("agregar"))

        articulos = leer_articulos()
        articulos.append({
            "nombre": nombre,
            "precio": precio,
            "stock": stock,
            "imagenes": imagenes_guardadas
        })
        guardar_articulos(articulos)

        flash("Artículo agregado correctamente con múltiples imágenes.")
        return redirect(url_for("index"))

    return render_template("agregar_articulo.html")

@app.route("/comprar/<nombre_articulo>", methods=["GET", "POST"])
def comprar(nombre_articulo):
    articulos = leer_articulos()
    articulo = next((a for a in articulos if a["nombre"] == nombre_articulo), None)
    if not articulo:
        flash("Artículo no encontrado")
        return redirect(url_for("index"))

    if request.method == "POST":
        cliente = request.form.get("cliente")
        email_cliente = request.form.get("email")
        celular = request.form.get("celular")
        cantidad = request.form.get("cantidad")

        if not cliente or not email_cliente or not celular or not cantidad:
            flash("Todos los campos son obligatorios (nombre, correo, celular, cantidad)")
            return redirect(url_for("comprar", nombre_articulo=nombre_articulo))

        if not celular.isdigit() or len(celular) < 8:
            flash("Debe ingresar un número de celular válido.")
            return redirect(url_for("comprar", nombre_articulo=nombre_articulo))

        try:
            cantidad = int(cantidad)
        except ValueError:
            flash("La cantidad debe ser un número entero")
            return redirect(url_for("comprar", nombre_articulo=nombre_articulo))

        if cantidad > articulo["stock"]:
            flash(f"No hay stock suficiente. Disponible: {articulo['stock']}")
            return redirect(url_for("comprar", nombre_articulo=nombre_articulo))

        articulo["stock"] -= cantidad
        guardar_articulos(articulos)

        msg = Message(
            subject=f"Solicitud de compra: {articulo['nombre']}",
            recipients=["hjsilva33@gmail.com"]
        )
        msg.charset = "utf-8"
        msg.body = f"""Solicitud de compra

Cliente: {cliente}
Email: {email_cliente}
Celular: {celular}
Producto: {articulo['nombre']}
Precio unitario: ${articulo['precio']}
Cantidad: {cantidad}
Total: ${articulo['precio'] * cantidad:.2f}
Stock restante: {articulo['stock']}
"""

        try:
            mail.send(msg)
            flash("Solicitud enviada correctamente y stock actualizado.")
        except Exception as e:
            flash(f"No se pudo enviar el correo: {str(e)}")
            app.logger.exception("Error enviando correo")

        return redirect(url_for("index"))

    return render_template("comprar.html", articulo=articulo)
    
if __name__ == "__main__":
    app.run(debug=True)
