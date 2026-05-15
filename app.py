from flask import (
    Flask,
    render_template,
    request,
    redirect,
    session
)

import sqlite3

app = Flask(__name__)

app.secret_key = "super_secret_key"

# -------------------------
# SQLITE
# -------------------------

conexion = sqlite3.connect(
    "figuritas.db",
    check_same_thread=False
)

cursor = conexion.cursor()

# TABLA USUARIOS
cursor.execute("""
CREATE TABLE IF NOT EXISTS usuarios (

    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT UNIQUE,
    password TEXT

)
""")

# TABLA INVENTARIO
cursor.execute("""
CREATE TABLE IF NOT EXISTS inventario (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    usuario TEXT,
    figurita TEXT,

    tipo TEXT,
    cantidad INTEGER

)
""")

# TABLA INTERCAMBIOS
cursor.execute("""
CREATE TABLE IF NOT EXISTS intercambios (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    usuario1 TEXT,
    usuario2 TEXT,

    da1 TEXT,
    da2 TEXT,

    acepto1 INTEGER,
    acepto2 INTEGER,

    realizado INTEGER

)
""")

conexion.commit()

# -------------------------
# LOGIN
# -------------------------

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        nombre = request.form["nombre"].lower()
        password = request.form["password"]

        cursor.execute(
            "SELECT * FROM usuarios WHERE nombre = ?",
            (nombre,)
        )

        usuario = cursor.fetchone()

        if usuario is None:

            cursor.execute(
                """
                INSERT INTO usuarios
                (nombre, password)

                VALUES (?, ?)
                """,
                (nombre, password)
            )

            conexion.commit()

        else:

            if usuario[2] != password:

                return """
                <h1>Contraseña incorrecta</h1>
                <a href='/login'>Volver</a>
                """

        session["usuario"] = nombre

        return redirect("/")

    return render_template("login.html")

# -------------------------
# LOGOUT
# -------------------------

@app.route("/logout")
def logout():

    session.clear()

    return redirect("/login")

# -------------------------
# OBTENER INVENTARIO
# -------------------------

def obtener_inventario(usuario):

    cursor.execute(
        """
        SELECT figurita, tipo, cantidad
        FROM inventario
        WHERE usuario = ?
        """,
        (usuario,)
    )

    datos = cursor.fetchall()

    faltantes = {}
    repetidas = {}

    for figurita, tipo, cantidad in datos:

        if tipo == "faltante":
            faltantes[figurita] = cantidad

        if tipo == "repetida":
            repetidas[figurita] = cantidad

    return faltantes, repetidas

# -------------------------
# AGREGAR FIGURITA
# -------------------------

@app.route("/agregar", methods=["POST"])
def agregar():

    if "usuario" not in session:
        return redirect("/login")

    usuario = session["usuario"]

    figurita = request.form["figurita"].strip().lower()
    tipo = request.form["tipo"]

    if figurita == "":
        return redirect("/")

    cursor.execute(
        """
        SELECT id, cantidad
        FROM inventario

        WHERE
            usuario = ?
            AND figurita = ?
            AND tipo = ?
        """,
        (
            usuario,
            figurita,
            tipo
        )
    )

    existe = cursor.fetchone()

    if existe:

        id_item = existe[0]
        cantidad = existe[1] + 1

        cursor.execute(
            """
            UPDATE inventario
            SET cantidad = ?
            WHERE id = ?
            """,
            (
                cantidad,
                id_item
            )
        )

    else:

        cursor.execute(
            """
            INSERT INTO inventario
            (usuario, figurita, tipo, cantidad)

            VALUES (?, ?, ?, 1)
            """,
            (
                usuario,
                figurita,
                tipo
            )
        )

    conexion.commit()

    return redirect("/")

# -------------------------
# SUMAR CANTIDAD
# -------------------------

@app.route("/sumar/<int:id_item>")
def sumar(id_item):

    cursor.execute(
        """
        UPDATE inventario
        SET cantidad = cantidad + 1
        WHERE id = ?
        """,
        (id_item,)
    )

    conexion.commit()

    return redirect("/")

# -------------------------
# RESTAR CANTIDAD
# -------------------------

@app.route("/restar/<int:id_item>")
def restar(id_item):

    cursor.execute(
        """
        SELECT cantidad
        FROM inventario
        WHERE id = ?
        """,
        (id_item,)
    )

    item = cursor.fetchone()

    if item:

        cantidad = item[0]

        if cantidad > 1:

            cursor.execute(
                """
                UPDATE inventario
                SET cantidad = cantidad - 1
                WHERE id = ?
                """,
                (id_item,)
            )

        else:

            cursor.execute(
                """
                DELETE FROM inventario
                WHERE id = ?
                """,
                (id_item,)
            )

    conexion.commit()

    return redirect("/")

# -------------------------
# CREAR INTERCAMBIOS
# -------------------------

def crear_intercambios(usuarios):

    nombres = list(usuarios.keys())

    for i in range(len(nombres)):

        for j in range(i + 1, len(nombres)):

            usuario1 = nombres[i]
            usuario2 = nombres[j]

            faltantes1, repetidas1 = usuarios[usuario1]
            faltantes2, repetidas2 = usuarios[usuario2]

            for fig1 in repetidas1:

                if fig1 in faltantes2:

                    for fig2 in repetidas2:

                        if fig2 in faltantes1:

                            cursor.execute(
                                """
                                SELECT * FROM intercambios

                                WHERE
                                    usuario1 = ?
                                    AND usuario2 = ?
                                    AND da1 = ?
                                    AND da2 = ?
                                    AND realizado = 0
                                """,
                                (
                                    usuario1,
                                    usuario2,
                                    fig1,
                                    fig2
                                )
                            )

                            existe = cursor.fetchone()

                            if existe is None:

                                cursor.execute(
                                    """
                                    INSERT INTO intercambios

                                    (
                                        usuario1,
                                        usuario2,
                                        da1,
                                        da2,
                                        acepto1,
                                        acepto2,
                                        realizado
                                    )

                                    VALUES (?, ?, ?, ?, 0, 0, 0)
                                    """,
                                    (
                                        usuario1,
                                        usuario2,
                                        fig1,
                                        fig2
                                    )
                                )

    conexion.commit()

# -------------------------
# ACEPTAR INTERCAMBIO
# -------------------------

@app.route("/aceptar/<int:id_intercambio>")
def aceptar(id_intercambio):

    if "usuario" not in session:
        return redirect("/login")

    usuario_actual = session["usuario"]

    cursor.execute(
        """
        SELECT * FROM intercambios
        WHERE id = ?
        """,
        (id_intercambio,)
    )

    intercambio = cursor.fetchone()

    if intercambio is None:
        return redirect("/")

    usuario1 = intercambio[1]
    usuario2 = intercambio[2]

    da1 = intercambio[3]
    da2 = intercambio[4]

    if usuario_actual == usuario1:

        cursor.execute(
            """
            UPDATE intercambios
            SET acepto1 = 1
            WHERE id = ?
            """,
            (id_intercambio,)
        )

    if usuario_actual == usuario2:

        cursor.execute(
            """
            UPDATE intercambios
            SET acepto2 = 1
            WHERE id = ?
            """,
            (id_intercambio,)
        )

    conexion.commit()

    cursor.execute(
        """
        SELECT * FROM intercambios
        WHERE id = ?
        """,
        (id_intercambio,)
    )

    intercambio = cursor.fetchone()

    if intercambio[5] == 1 and intercambio[6] == 1:

        # REMOVER FIGURITAS
        cursor.execute(
            """
            DELETE FROM inventario

            WHERE
                usuario = ?
                AND figurita = ?
                AND tipo = 'repetida'
            """,
            (
                usuario1,
                da1
            )
        )

        cursor.execute(
            """
            DELETE FROM inventario

            WHERE
                usuario = ?
                AND figurita = ?
                AND tipo = 'faltante'
            """,
            (
                usuario1,
                da2
            )
        )

        cursor.execute(
            """
            DELETE FROM inventario

            WHERE
                usuario = ?
                AND figurita = ?
                AND tipo = 'repetida'
            """,
            (
                usuario2,
                da2
            )
        )

        cursor.execute(
            """
            DELETE FROM inventario

            WHERE
                usuario = ?
                AND figurita = ?
                AND tipo = 'faltante'
            """,
            (
                usuario2,
                da1
            )
        )

        cursor.execute(
            """
            UPDATE intercambios
            SET realizado = 1
            WHERE id = ?
            """,
            (id_intercambio,)
        )

        conexion.commit()

    return redirect("/")

# -------------------------
# PAGINA PRINCIPAL
# -------------------------

@app.route("/")
def inicio():

    if "usuario" not in session:
        return redirect("/login")

    usuario_actual = session["usuario"]

    usuarios = {}

    cursor.execute("SELECT nombre FROM usuarios")

    lista_usuarios = cursor.fetchall()

    for usuario in lista_usuarios:

        nombre = usuario[0]

        usuarios[nombre] = obtener_inventario(nombre)

    crear_intercambios(usuarios)

    cursor.execute("""
    SELECT * FROM intercambios
    WHERE realizado = 0
    """)

    datos_intercambios = cursor.fetchall()

    intercambios = []

    for inter in datos_intercambios:

        intercambios.append({
            "id": inter[0],
            "usuario1": inter[1],
            "usuario2": inter[2],
            "da1": inter[3],
            "da2": inter[4],
            "acepto1": inter[5],
            "acepto2": inter[6]
        })

    faltantes_actuales, repetidas_actuales = obtener_inventario(
        usuario_actual
    )

    cursor.execute(
        """
        SELECT *
        FROM inventario
        WHERE usuario = ?
        """,
        (usuario_actual,)
    )

    inventario = cursor.fetchall()

    return render_template(
        "index.html",
        usuario_actual=usuario_actual,
        inventario=inventario,
        intercambios=intercambios
    )

# -------------------------
# INICIAR APP
# -------------------------

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)