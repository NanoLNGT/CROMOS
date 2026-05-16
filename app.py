from flask import (
    Flask,
    render_template,
    request,
    redirect,
    session
)

import psycopg2

app = Flask(__name__)

app.secret_key = "super_secret_key"

# -------------------------
# POSTGRESQL
# -------------------------

conexion = psycopg2.connect(
    "postgresql://postgres.cedwdsoaiuzgrwmvdsus:dYbWuwdgQIeCDhv8@aws-1-us-east-2.pooler.supabase.com:6543/postgres",
    sslmode="require"
)


cursor = conexion.cursor()

# -------------------------
# TABLA USUARIOS
# -------------------------

cursor.execute("""
CREATE TABLE IF NOT EXISTS usuarios (

    id SERIAL PRIMARY KEY,
    nombre TEXT UNIQUE,
    password TEXT

)
""")

# -------------------------
# TABLA INVENTARIO
# -------------------------

cursor.execute("""
CREATE TABLE IF NOT EXISTS inventario (

    id SERIAL PRIMARY KEY,

    usuario TEXT,
    figurita TEXT,

    tipo TEXT,
    cantidad INTEGER

)
""")

conexion.commit()

# -------------------------
# TABLA PROPUESTAS
# -------------------------

cursor.execute("""
CREATE TABLE IF NOT EXISTS propuestas (

    id SERIAL PRIMARY KEY,

    usuario1 TEXT,
    usuario2 TEXT,

    da1 TEXT,
    da2 TEXT

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
            """
            SELECT *
            FROM usuarios
            WHERE nombre = %s
            """,
            (nombre,)
        )

        usuario = cursor.fetchone()

        # CREAR USUARIO
        if usuario is None:

            cursor.execute(
                """
                INSERT INTO usuarios
                (nombre, password)

                VALUES (%s, %s)
                """,
                (nombre, password)
            )

            conexion.commit()

        else:

            # PASSWORD INCORRECTA
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
        WHERE usuario = %s
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
            usuario = %s
            AND figurita = %s
            AND tipo = %s
        """,
        (
            usuario,
            figurita,
            tipo
        )
    )

    existe = cursor.fetchone()

    # YA EXISTE
    if existe:

        id_item = existe[0]
        cantidad = existe[1] + 1

        cursor.execute(
            """
            UPDATE inventario
            SET cantidad = %s
            WHERE id = %s
            """,
            (
                cantidad,
                id_item
            )
        )

    # NUEVA FIGURITA
    else:

        cursor.execute(
            """
            INSERT INTO inventario
            (usuario, figurita, tipo, cantidad)

            VALUES (%s, %s, %s, 1)
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
# SUMAR
# -------------------------

@app.route("/sumar/<int:id_item>")
def sumar(id_item):

    cursor.execute(
        """
        UPDATE inventario
        SET cantidad = cantidad + 1
        WHERE id = %s
        """,
        (id_item,)
    )

    conexion.commit()

    return redirect("/")

# -------------------------
# RESTAR
# -------------------------

@app.route("/restar/<int:id_item>")
def restar(id_item):

    cursor.execute(
        """
        SELECT cantidad
        FROM inventario
        WHERE id = %s
        """,
        (id_item,)
    )

    item = cursor.fetchone()

    if item:

        cantidad = item[0]

        # BAJAR CANTIDAD
        if cantidad > 1:

            cursor.execute(
                """
                UPDATE inventario
                SET cantidad = cantidad - 1
                WHERE id = %s
                """,
                (id_item,)
            )

        # ELIMINAR
        else:

            cursor.execute(
                """
                DELETE FROM inventario
                WHERE id = %s
                """,
                (id_item,)
            )

    conexion.commit()

    return redirect("/")
# -------------------------
# REALIZAR INTERCAMBIO
# -------------------------

@app.route("/intercambiar")
def intercambiar():

    if "usuario" not in session:
        return redirect("/login")

    usuario1 = request.args.get("u1")
    usuario2 = request.args.get("u2")

    da1 = request.args.get("d1")
    da2 = request.args.get("d2")

    # INVENTARIOS ACTUALES
    faltantes1, repetidas1 = obtener_inventario(usuario1)
    faltantes2, repetidas2 = obtener_inventario(usuario2)

    # VALIDAR
    valido = (

        da1 in repetidas1
        and da1 in faltantes2

        and

        da2 in repetidas2
        and da2 in faltantes1

    )

    if not valido:

        return redirect("/")

    # ELIMINAR REPETIDA USUARIO 1
    cursor.execute(
        """
        DELETE FROM inventario

        WHERE
            usuario = %s
            AND figurita = %s
            AND tipo = 'repetida'
        """,
        (
            usuario1,
            da1
        )
    )

    # ELIMINAR FALTANTE USUARIO 1
    cursor.execute(
        """
        DELETE FROM inventario

        WHERE
            usuario = %s
            AND figurita = %s
            AND tipo = 'faltante'
        """,
        (
            usuario1,
            da2
        )
    )

    # ELIMINAR REPETIDA USUARIO 2
    cursor.execute(
        """
        DELETE FROM inventario

        WHERE
            usuario = %s
            AND figurita = %s
            AND tipo = 'repetida'
        """,
        (
            usuario2,
            da2
        )
    )

    # ELIMINAR FALTANTE USUARIO 2
    cursor.execute(
        """
        DELETE FROM inventario

        WHERE
            usuario = %s
            AND figurita = %s
            AND tipo = 'faltante'
        """,
        (
            usuario2,
            da1
        )
    )

    conexion.commit()

    return redirect("/")
# -------------------------
# PROPONER INTERCAMBIO
# -------------------------

@app.route("/proponer")
def proponer():

    if "usuario" not in session:
        return redirect("/login")

    usuario1 = request.args.get("u1")
    usuario2 = request.args.get("u2")

    da1 = request.args.get("d1")
    da2 = request.args.get("d2")

    # EVITAR DUPLICADOS
    cursor.execute(
        """
        SELECT *
        FROM propuestas

        WHERE
            usuario1 = %s
            AND usuario2 = %s
            AND da1 = %s
            AND da2 = %s
        """,
        (
            usuario1,
            usuario2,
            da1,
            da2
        )
    )

    existe = cursor.fetchone()

    if existe is None:

        cursor.execute(
            """
            INSERT INTO propuestas
            (
                usuario1,
                usuario2,
                da1,
                da2
            )

            VALUES (%s, %s, %s, %s)
            """,
            (
                usuario1,
                usuario2,
                da1,
                da2
            )
        )

        conexion.commit()

    return redirect("/")

# -------------------------
# ACEPTAR INTERCAMBIO
# -------------------------

@app.route("/aceptar/<int:id_propuesta>")
def aceptar(id_propuesta):

    if "usuario" not in session:
        return redirect("/login")

    cursor.execute(
        """
        SELECT *
        FROM propuestas
        WHERE id = %s
        """,
        (id_propuesta,)
    )

    propuesta = cursor.fetchone()

    if propuesta is None:
        return redirect("/")

    usuario1 = propuesta[1]
    usuario2 = propuesta[2]

    da1 = propuesta[3]
    da2 = propuesta[4]

    # INVENTARIOS ACTUALES
    faltantes1, repetidas1 = obtener_inventario(usuario1)
    faltantes2, repetidas2 = obtener_inventario(usuario2)

    valido = (

        da1 in repetidas1
        and da1 in faltantes2

        and

        da2 in repetidas2
        and da2 in faltantes1

    )

    if not valido:

        cursor.execute(
            """
            DELETE FROM propuestas
            WHERE id = %s
            """,
            (id_propuesta,)
        )

        conexion.commit()

        return redirect("/")

    # ELIMINAR REPETIDAS/FALTANTES

    cursor.execute(
        """
        DELETE FROM inventario

        WHERE
            usuario = %s
            AND figurita = %s
            AND tipo = 'repetida'
        """,
        (usuario1, da1)
    )

    cursor.execute(
        """
        DELETE FROM inventario

        WHERE
            usuario = %s
            AND figurita = %s
            AND tipo = 'faltante'
        """,
        (usuario1, da2)
    )

    cursor.execute(
        """
        DELETE FROM inventario

        WHERE
            usuario = %s
            AND figurita = %s
            AND tipo = 'repetida'
        """,
        (usuario2, da2)
    )

    cursor.execute(
        """
        DELETE FROM inventario

        WHERE
            usuario = %s
            AND figurita = %s
            AND tipo = 'faltante'
        """,
        (usuario2, da1)
    )

    # BORRAR PROPUESTA
    cursor.execute(
        """
        DELETE FROM propuestas
        WHERE id = %s
        """,
        (id_propuesta,)
    )

    conexion.commit()

    return redirect("/")

# -------------------------
# RECHAZAR PROPUESTA
# -------------------------

@app.route("/rechazar/<int:id_propuesta>")
def rechazar(id_propuesta):

    if "usuario" not in session:
        return redirect("/login")

    cursor.execute(
        """
        DELETE FROM propuestas
        WHERE id = %s
        """,
        (id_propuesta,)
    )

    conexion.commit()

    return redirect("/")

# -------------------------
# HOME
# -------------------------

@app.route("/")
def inicio():

    if "usuario" not in session:
        return redirect("/login")

    usuario_actual = session["usuario"]

    usuarios = {}

    cursor.execute("""
    SELECT nombre
    FROM usuarios
    """)

    lista_usuarios = cursor.fetchall()

    for usuario in lista_usuarios:

        nombre = usuario[0]

        usuarios[nombre] = obtener_inventario(nombre)

    # -------------------------
    # INTERCAMBIOS DINAMICOS
    # -------------------------

    intercambios = []

    nombres = list(usuarios.keys())

    for i in range(len(nombres)):

        for j in range(i + 1, len(nombres)):

            usuario1 = nombres[i]
            usuario2 = nombres[j]
            # SOLO MOSTRAR MIS INTERCAMBIOS
            if (
                usuario_actual != usuario1
                
                and
                
                usuario_actual != usuario2
                
                ):
                
                continue

            faltantes1, repetidas1 = usuarios[usuario1]
            faltantes2, repetidas2 = usuarios[usuario2]

            for fig1 in repetidas1.keys():

                if fig1 in faltantes2:

                    for fig2 in repetidas2.keys():

                        if fig2 in faltantes1:

                            intercambios.append({

                                "usuario1": usuario1,
                                "usuario2": usuario2,

                                "da1": fig1,
                                "da2": fig2

                            })

    # INVENTARIO ACTUAL
    cursor.execute(
        """
        SELECT *
        FROM inventario
        WHERE usuario = %s
        """,
        (usuario_actual,)
    )

    inventario = cursor.fetchall()
    cursor.execute("""
                   SELECT *
                   FROM propuestas
                   """)
    
    propuestas = cursor.fetchall()
    
    return render_template(
        "index.html",
        usuario_actual=usuario_actual,
        inventario=inventario,
        propuestas=propuestas,
        intercambios=intercambios
    )

# -------------------------
# INICIAR APP
# -------------------------

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5000
    )