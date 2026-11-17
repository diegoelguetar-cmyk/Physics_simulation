"""Conservacion del momento angular: vara giratoria con dos masas deslizantes.

Una vara rigida gira libre (sin roce) alrededor de su centro. Dos masas
identicas pueden deslizar a lo largo de la vara, siempre a la misma distancia
del eje (se mueven "al mismo tiempo", una hacia cada lado).

Fisica:
- Momento de inercia respecto al eje:  I(d) = I_vara + 2 * m * d^2
- Momento angular:                      L = I * omega
- Sin torques externos, L se conserva. Si las masas se acercan al eje,
  I baja y omega sube (efecto "patinadora"); si se alejan, omega baja.
- La energia cinetica K = L^2 / (2 I) NO se conserva: la hace variar quien
  empuja o tira de las masas (trabajo contra la fuerza centrifuga).

Como lo resuelve pymunk:
- pymunk integra la rotacion del cuerpo (angle, angular_velocity).
- Cuando cambia d, recalculamos el momento de inercia del cuerpo y ajustamos
  omega para que L = I * omega quede igual que antes del cambio.

Controles:
- Mantener click izquierdo: las masas se ubican a la distancia del puntero.
- Flechas arriba/derecha (alejar) y abajo/izquierda (acercar), o rueda del mouse.
- Tecla R:        reinicia la simulacion.
- Tecla ESPACIO:  pausa.
- Tecla ESC:      cierra la ventana.
"""

import math
from collections import deque
from pathlib import Path

import click
import pyglet
import pymunk

# ---------------------------------------------------------------- parametros
# idea de hacer un diccionario, cosa que los parámetros se puedan modificar por eventos
M_VARA = 2.0  # masa de la vara
M_MASA = 5.0  # masa de cada pesa
RADIO_MASA = 18.0  # radio visual de cada pesa (px)
GROSOR_VARA = 10.0  # grosor visual de la vara (px)
V_MAX = 2600.0  # velocidad maxima de deslizamiento de las masas (px/s)
DT = 1.0 / 60.0  # paso fijo de integracion
MUESTRAS = 200  # puntos del grafico de omega (uno cada 3 pasos = ~10 s)


@click.command("momento_angular", short_help="Conservacion del momento angular")
@click.option("--width", type=int, default=900)
@click.option("--height", type=int, default=700)
@click.option("--omega0", type=float, default=4.0, help="velocidad angular inicial (rad/s)")
def momento_angular(width, height, omega0):
    window = pyglet.window.Window(width, height, caption="Conservacion del momento angular")

    fuente = None
    try:
        ruta = (
            Path(__file__).parent.parent.parent
            / "assets"
            / "FiraCode"
            / "FiraCode-Regular.ttf"
        )
        pyglet.font.add_file(str(ruta))
        fuente = "Fira Code"
    except Exception:
        pass  # si no esta la fuente usamos la del sistema

    # geometria: el eje esta en el centro de la ventana (algo mas arriba).
    centro = (width / 2, height * 0.6)
    mitad = min(width * 0.4, height * 0.37)  # semilongitud de la vara
    d_min = RADIO_MASA + 12.0
    d_max = mitad - RADIO_MASA - 4.0
    d_ini = d_max * 0.85

    i_vara = M_VARA * (2 * mitad) ** 2 / 12.0  # barra delgada por su centro
    i_min = i_vara + 2 * M_MASA * d_min**2  # para escalar grafico y medidor

    def inercia(d):
        return i_vara + 2 * M_MASA * d * d

    # 1) espacio fisico sin gravedad: solo importa la rotacion.
    space = pymunk.Space()
    space.gravity = (0.0, 0.0)

    # 2) cuerpo dinamico de la vara + masas. El centro de masa queda siempre
    #    en el eje (las masas se mueven simetricas), asi que fijamos el cuerpo
    #    al fondo con un pivote y solo puede rotar.
    #    masa y momento los fijamos a mano porque cambian al deslizar las pesas.
    cuerpo = pymunk.Body(M_VARA + 2 * M_MASA, inercia(d_ini))
    cuerpo.position = centro
    space.add(cuerpo)
    space.add(pymunk.PivotJoint(space.static_body, cuerpo, centro))

    estado = {
        "d": d_ini,  # distancia actual de cada masa al eje
        "objetivo": d_ini,  # distancia a la que quiere llegar el usuario
        "pausa": False,
        "arrastrando": False,
        "mouse": (0.0, 0.0),
        "paso": 0,
    }
    historial = deque(maxlen=MUESTRAS)  # muestras de omega

    # teclas actualmente presionadas (se llena en on_key_press / on_key_release).
    teclas = set()

    def reset():
        estado["d"] = estado["objetivo"] = d_ini
        estado["arrastrando"] = False
        estado["paso"] = 0
        cuerpo.angle = 0.0
        cuerpo.moment = inercia(d_ini)
        cuerpo.angular_velocity = omega0
        historial.clear()

    reset()

    def mover_masas(nuevo_d):
        """Cambia d conservando el momento angular L = I * omega."""
        momento_angular_L = cuerpo.moment * cuerpo.angular_velocity
        estado["d"] = nuevo_d
        cuerpo.moment = inercia(nuevo_d) #actualiza el momento sismico segun la nueva sistancia
        cuerpo.angular_velocity = momento_angular_L / cuerpo.moment

    def limitar(d):
        return max(d_min, min(d_max, d))

    # 3) eventos.
    def posiciones_masas():
        """
        calcula la posición de las masas segun la distancia del centro, usando coordenadas cartesianas.
        Para saber el estado de el cuerpo, usa los metodos dentro del objeto cuerpo. 

        """
        ux, uy = math.cos(cuerpo.angle), math.sin(cuerpo.angle)
        d = estado["d"]
        cx, cy = cuerpo.position
        return (cx + d * ux, cy + d * uy), (cx - d * ux, cy - d * uy)

    @window.event
    def on_mouse_press(x, y, button, modifiers):
        # mantener el click izquierdo en cualquier lugar: las masas se ubican
        # a la misma distancia del eje que el puntero.
        if button == pyglet.window.mouse.LEFT:
            estado["arrastrando"] = True
            estado["mouse"] = (x, y)

    @window.event
    def on_mouse_drag(x, y, dx, dy, buttons, modifiers):
        if estado["arrastrando"]:
            estado["mouse"] = (x, y)

    @window.event
    def on_mouse_release(x, y, button, modifiers):
        estado["arrastrando"] = False

    @window.event
    def on_mouse_scroll(x, y, scroll_x, scroll_y):
        estado["objetivo"] = limitar(estado["objetivo"] + 15.0 * scroll_y)

    @window.event
    def on_key_release(symbol, modifiers):
        teclas.discard(symbol)

    @window.event
    def on_key_press(symbol, modifiers):
        teclas.add(symbol)
        if symbol == pyglet.window.key.R:
            reset()
        elif symbol == pyglet.window.key.SPACE:
            estado["pausa"] = not estado["pausa"]
        elif symbol == pyglet.window.key.ESCAPE:
            window.close()

    # 4) integracion con paso fijo.
    def actualizar(_):
        if estado["pausa"]:
            return

        # el objetivo viene del teclado o del mouse.
        key = pyglet.window.key
        if key.UP in teclas or key.RIGHT in teclas:
            estado["objetivo"] += V_MAX * DT  # alejar
        if key.DOWN in teclas or key.LEFT in teclas:
            estado["objetivo"] -= V_MAX * DT  # acercar
        if estado["arrastrando"]:
            mx, my = estado["mouse"]
            cx, cy = cuerpo.position
            estado["objetivo"] = math.hypot(mx - cx, my - cy)
        estado["objetivo"] = limitar(estado["objetivo"])

        # las masas avanzan hacia el objetivo con velocidad acotada, y en
        # cada avance se reajusta omega para conservar L.
        paso = estado["objetivo"] - estado["d"]
        paso = max(-V_MAX * DT, min(V_MAX * DT, paso))
        if paso != 0.0:
            mover_masas(estado["d"] + paso)

        space.step(DT)

        estado["paso"] += 1
        if estado["paso"] % 3 == 0: #guardo cada tres
            historial.append(cuerpo.angular_velocity)

    pyglet.clock.schedule_interval(actualizar, DT)

    # 5) dibujo con pyglet.shapes dentro de un batch.
    @window.event
    def on_draw():
        window.clear()
        batch = pyglet.graphics.Batch()
        primitivas = []  # mantiene vivas las formas hasta batch.draw()

        cx, cy = cuerpo.position
        omega = cuerpo.angular_velocity
        inercia_actual = cuerpo.moment
        L = inercia_actual * omega
        energia = 0.5 * inercia_actual * omega**2
        d = estado["d"]

        # circunferencia guia por donde pasan las masas.
        primitivas.append(
            pyglet.shapes.Arc(cx, cy, d, color=(60, 60, 60), batch=batch)
        )

        # vara: rectangulo con ancla al centro. pyglet rota en sentido horario.
        vara = pyglet.shapes.Rectangle(
            cx, cy, 2 * mitad, GROSOR_VARA, color=(190, 190, 190), batch=batch
        )
        vara.anchor_x = mitad
        vara.anchor_y = GROSOR_VARA / 2
        vara.rotation = -math.degrees(cuerpo.angle)
        primitivas.append(vara)

        # masas (una roja, una azul para ver bien la rotacion).
        (ax, ay), (bx, by) = posiciones_masas()
        primitivas.append(
            pyglet.shapes.Circle(ax, ay, RADIO_MASA, color=(220, 70, 70), batch=batch)
        )
        primitivas.append(
            pyglet.shapes.Circle(bx, by, RADIO_MASA, color=(70, 130, 230), batch=batch)
        )

        # eje.
        primitivas.append(
            pyglet.shapes.Circle(cx, cy, 6, color=(30, 30, 30), batch=batch)
        )

        # ---- medidor de omega (barra con signo, centrada en cero).
        omega_max = max(abs(L) / i_min, 1e-6)
        gx, gy, mitad_g = width - 190, 70, 130
        primitivas.append(
            pyglet.shapes.Rectangle(gx - mitad_g, gy - 2, 2 * mitad_g, 4, color=(70, 70, 70), batch=batch)
        )
        largo = max(-mitad_g, min(mitad_g, omega / omega_max * mitad_g))
        primitivas.append(
            pyglet.shapes.Rectangle(
                min(gx, gx + largo), gy - 8, max(abs(largo), 1), 16,
                color=(255, 200, 60), batch=batch,
            )
        )
        primitivas.append(
            pyglet.shapes.Rectangle(gx - 1, gy - 14, 2, 28, color=(220, 220, 220), batch=batch)
        )
        primitivas.append(
            pyglet.text.Label(
                f"omega = {omega:+.2f} rad/s", font_name=fuente, font_size=12,
                x=gx - mitad_g, y=gy + 24, color=(255, 200, 60, 255), batch=batch,
            )
        )

        # ---- grafico de omega(t): cero al centro, escala = omega maxima posible.
        px, py, pw, ph = 30, 30, 330, 110
        primitivas.append(
            pyglet.shapes.Rectangle(px, py, pw, ph, color=(28, 28, 28), batch=batch)
        )
        primitivas.append(
            pyglet.shapes.Line(px, py + ph / 2, px + pw, py + ph / 2, thickness=1, color=(80, 80, 80), batch=batch)
        )
        puntos = list(historial)
        for i in range(1, len(puntos)):
            x0 = px + (i - 1) * pw / MUESTRAS
            x1 = px + i * pw / MUESTRAS
            y0 = py + ph / 2 + max(-1, min(1, puntos[i - 1] / omega_max)) * ph / 2
            y1 = py + ph / 2 + max(-1, min(1, puntos[i] / omega_max)) * ph / 2
            primitivas.append(
                pyglet.shapes.Line(x0, y0, x1, y1, thickness=2, color=(255, 200, 60), batch=batch)
            )
        primitivas.append(
            pyglet.text.Label(
                "omega(t)", font_name=fuente, font_size=10,
                x=px + 6, y=py + ph - 16, color=(180, 180, 180, 255), batch=batch,
            )
        )

        # ---- informacion numerica.
        lineas = [
            "mantener click izq / flechas / rueda: mover masas",
            "R: reset  |  ESPACIO: pausa  |  ESC: salir",
            "",
            f"omega     = {omega:+8.3f} rad/s  ({omega * 60 / (2 * math.pi):+7.1f} rpm)",
            f"distancia = {d:8.1f} px",
            f"I         = {inercia_actual:10.0f}",
            f"L = I*w   = {L:10.1f}   (se conserva)",
            f"K = L2/2I = {energia:10.1f}   (cambia: trabajo al mover masas)",
        ]
        for i, texto in enumerate(lineas):
            primitivas.append(
                pyglet.text.Label(
                    texto, font_name=fuente, font_size=11,
                    x=30, y=height - 25 - 22 * i, color=(220, 220, 220, 255), batch=batch,
                )
            )

        if estado["pausa"]:
            primitivas.append(
                pyglet.text.Label(
                    "PAUSA", font_name=fuente, font_size=16,
                    x=width - 110, y=height - 30, color=(255, 120, 120, 255), batch=batch,
                )
            )

        batch.draw()

    pyglet.app.run()


if __name__ == "__main__":
    momento_angular()