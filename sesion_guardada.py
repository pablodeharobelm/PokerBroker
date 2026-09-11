"""Sesión recuperable por reproducción de acciones legales, sin pickle."""

from copy import deepcopy
from datetime import datetime
import json
import os
from pathlib import Path
import random
import tempfile

from motor_mesa import MotorMesa, JugadorMesa
from estrategia_bots import PERFILES


class ErrorSesion(Exception):
    pass


def instantanea(motor, registrada, ayudas, pendiente=None):
    return deepcopy({
        "version": 1, "id": motor.id_mano, "inicio": motor.inicio_mano,
        "jugadores": [{"nombre": j.nombre, "fichas": motor.fichas_iniciales[i], "perfil": j.perfil}
                      for i, j in enumerate(motor.jugadores)],
        "sb": motor.sb, "bb": motor.bb, "dealer_anterior": motor.dealer_anterior,
        "rng_inicio": motor.rng_inicio, "rng_actual": motor.rng.getstate(),
        "acciones": motor.eventos, "fase": motor.fase, "terminada": motor.terminada,
        "registrada": registrada, "ayudas": ayudas, "pendiente": pendiente,
    })


def _estado_rng(valor):
    return (valor[0], tuple(valor[1]), valor[2])


def recuperar(datos):
    if datos["version"] != 1:
        raise ValueError("Versión de sesión no compatible.")
    if not isinstance(datos["id"], str) or not datos["id"]:
        raise ValueError("Identificador inválido.")
    datetime.fromisoformat(datos["inicio"])
    if type(datos["fase"]) is not int or not 0 <= datos["fase"] <= 3:
        raise ValueError("Calle inválida.")
    for clave in ("terminada", "registrada", "ayudas"):
        if type(datos[clave]) is not bool:
            raise ValueError("Estado inválido.")
    if datos["registrada"] and not datos["terminada"]:
        raise ValueError("Una mano en curso no puede estar registrada.")
    jugadores = [JugadorMesa(j["nombre"], j["fichas"], perfil=j["perfil"]) for j in datos["jugadores"]]
    if len(jugadores) != 6 or any(not isinstance(j.nombre, str) or j.perfil not in PERFILES for j in jugadores):
        raise ValueError("Configuración de mesa no compatible.")
    rng = random.Random()
    rng.setstate(_estado_rng(datos["rng_inicio"]))
    motor = MotorMesa(jugadores, datos["sb"], datos["bb"], rng)
    if type(datos["dealer_anterior"]) is not int or not -1 <= datos["dealer_anterior"] < len(jugadores):
        raise ValueError("Botón inválido.")
    motor.dealer = datos["dealer_anterior"]
    motor.iniciar_mano()
    motor.id_mano = datos["id"]
    motor.inicio_mano = datos["inicio"]
    for accion in datos["acciones"]:
        if type(accion["fase"]) is not int or not motor.fase <= accion["fase"] <= 3:
            raise ValueError("Orden de calles inválido.")
        while motor.fase < accion["fase"]:
            motor.avanzar_calle()
        motor.actuar(accion["jugador"], accion["accion"], accion["total_calle"] if accion["accion"] == "raise" else None)
        if motor.eventos[-1] != accion:
            raise ValueError("Las acciones guardadas no cuadran con la mesa.")
    if motor.fase > datos["fase"]:
        raise ValueError("Calle final incoherente.")
    while motor.fase < datos["fase"]:
        motor.avanzar_calle()
    if datos["terminada"] and not motor.terminada:
        if motor.fase != 3:
            raise ValueError("Falta completar la mano.")
        motor.avanzar_calle()
    if motor.terminada != datos["terminada"]:
        raise ValueError("Final de mano incoherente.")
    pendiente = datos.get("pendiente")
    if pendiente is not None:
        from persistencia import BaseDatosLocal
        from estadisticas import construir_registro
        BaseDatosLocal._validar_mano(pendiente)
        esperado = construir_registro(motor, 3)
        esperado["fin"] = pendiente["fin"]
        if esperado != pendiente:
            raise ValueError("El registro pendiente no coincide con la sesión.")
    rng.setstate(_estado_rng(datos["rng_actual"]))
    return motor


class ArchivoSesion:
    def __init__(self, ruta):
        self.ruta = Path(ruta)

    def cargar(self):
        if not self.ruta.exists():
            return None
        try:
            datos = json.loads(self.ruta.read_text(encoding="utf-8"))
            return recuperar(datos), datos
        except (OSError, ValueError, KeyError, TypeError, IndexError, AttributeError) as error:
            raise ErrorSesion(f"No se pudo recuperar la sesión: {error}") from error

    def guardar(self, datos):
        temporal = None
        try:
            contenido = json.dumps(datos, ensure_ascii=False)
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=self.ruta.parent,
                                             prefix=self.ruta.name + ".", suffix=".tmp", delete=False) as f:
                temporal = f.name
                f.write(contenido)
                f.flush()
                os.fsync(f.fileno())
            os.replace(temporal, self.ruta)
        except (OSError, ValueError, TypeError) as error:
            raise ErrorSesion(f"No se pudo guardar la sesión: {error}") from error
        finally:
            if temporal and os.path.exists(temporal):
                os.unlink(temporal)
