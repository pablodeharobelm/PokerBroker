"""Historial JSON versionado; migración conservadora y escritura atómica."""

import json
import os
from pathlib import Path
import tempfile
from datetime import datetime


class ErrorHistorial(Exception):
    pass


class BaseDatosLocal:
    def __init__(self, nombre_archivo="historial_entrenamiento.json"):
        self.ruta_archivo = str(Path(__file__).resolve().parent / nombre_archivo)

    def cargar_historial(self):
        ruta = Path(self.ruta_archivo)
        if not ruta.exists():
            return {"version": 2, "historial_anterior": None, "manos": [], "manos_totales": 0}
        try:
            datos = json.loads(ruta.read_text(encoding="utf-8-sig"))
            if not isinstance(datos, dict):
                raise ValueError("Se esperaba un objeto JSON.")
            if "version" not in datos:
                if type(datos.get("manos_totales")) is not int or datos["manos_totales"] < 0:
                    raise ValueError("El historial antiguo no tiene un contador válido.")
                return {"version": 2, "historial_anterior": datos, "manos": [], "manos_totales": 0}
            if datos["version"] != 2 or not isinstance(datos.get("manos"), list):
                raise ValueError("Versión de historial no compatible.")
            antiguo = datos.get("historial_anterior")
            if antiguo is not None and (not isinstance(antiguo, dict) or type(antiguo.get("manos_totales")) is not int):
                raise ValueError("Contadores anteriores inválidos.")
            datos["historial_anterior"] = antiguo
            ids = set()
            for mano in datos["manos"]:
                self._validar_mano(mano)
                if mano["id"] in ids:
                    raise ValueError("Hay manos duplicadas en el archivo.")
                ids.add(mano["id"])
            datos["manos_totales"] = len(datos["manos"])
            return datos
        except (OSError, ValueError, KeyError, TypeError, IndexError) as error:
            raise ErrorHistorial(f"No se pudo leer el historial. El archivo se conserva: {error}") from error

    @staticmethod
    def _validar_mano(mano):
        if not isinstance(mano["id"], str) or not mano["id"]:
            raise ValueError("Identificador de mano inválido.")
        jugadores = mano["jugadores"]
        if not 2 <= len(jugadores) <= 6 or type(mano["heroe"]) is not int or not 0 <= mano["heroe"] < len(jugadores):
            raise ValueError("Asientos inválidos.")
        for campo in ("inicio", "fin"):
            if not isinstance(mano[campo], str):
                raise ValueError("Fecha inválida.")
            datetime.fromisoformat(mano[campo])
        for i, j in enumerate(jugadores):
            if j["asiento"] != i:
                raise ValueError("Orden de asientos inválido.")
            for campo in ("fichas_iniciales", "fichas_finales", "aportado", "premio", "devuelto"):
                if type(j[campo]) is not int or j[campo] < 0:
                    raise ValueError("Importe de fichas inválido.")
            if j["fichas_finales"] != j["fichas_iniciales"] - j["aportado"] + j["premio"] + j["devuelto"]:
                raise ValueError("El balance de la mano no cuadra.")
            for campo in ("nombre", "posicion", "cartas", "participando", "retirado"):
                j[campo]
            if not isinstance(j["nombre"], str) or not isinstance(j["posicion"], str):
                raise ValueError("Perfil inválido.")
            if type(j["participando"]) is not bool or type(j["retirado"]) is not bool:
                raise ValueError("Estado de jugador inválido.")
            if not isinstance(j["cartas"], list) or len(j["cartas"]) != (2 if j["participando"] else 0):
                raise ValueError("Cartas de jugador inválidas.")
        if sum(j["fichas_iniciales"] for j in jugadores) != sum(j["fichas_finales"] for j in jugadores):
            raise ValueError("No se conservan las fichas.")
        for e in mano["acciones"]:
            if e["accion"] not in ("fold", "check", "call", "raise") or not 0 <= e["fase"] <= 3:
                raise ValueError("Acción inválida.")
            if not 0 <= e["jugador"] < len(jugadores):
                raise ValueError("Jugador de acción inválido.")
            for campo in ("cantidad", "subidas_previas", "por_pagar", "podia_subir", "bote_previo", "bote_despues", "total_calle", "fichas_restantes", "all_in"):
                e[campo]
            for campo in ("cantidad", "subidas_previas", "por_pagar", "bote_previo", "bote_despues", "total_calle", "fichas_restantes"):
                if type(e[campo]) is not int or e[campo] < 0:
                    raise ValueError("Importe de acción inválido.")
            if type(e["podia_subir"]) is not bool or type(e["all_in"]) is not bool:
                raise ValueError("Oportunidad de acción inválida.")
        for campo in ("mesa", "ciegas", "showdown", "vieron_flop", "botes", "dealer", "sb", "bb"):
            mano[campo]
        if not isinstance(mano["mesa"], list) or len(mano["mesa"]) not in (0, 3, 4, 5):
            raise ValueError("Mesa inválida.")
        baraja = {f"{v}{p}" for v in ("2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A") for p in "SHDC"}
        cartas = mano["mesa"] + [c for j in jugadores for c in j["cartas"]]
        if any(not isinstance(c, str) or c not in baraja for c in cartas) or len(set(cartas)) != len(cartas):
            raise ValueError("Cartas duplicadas o desconocidas.")
        for ciega in mano["ciegas"]:
            if not 0 <= ciega["jugador"] < len(jugadores) or type(ciega["cantidad"]) is not int or ciega["cantidad"] < 0 or ciega["tipo"] not in ("SB", "BB"):
                raise ValueError("Ciega inválida.")
        for bote in mano["botes"]:
            if type(bote["cantidad"]) is not int or bote["cantidad"] <= 0 or not bote["ganadores"]:
                raise ValueError("Bote inválido.")
            if any(type(i) is not int or not 0 <= i < len(jugadores) for i in bote["ganadores"]):
                raise ValueError("Ganador inválido.")

    def registrar_mano(self, mano):
        try:
            self._validar_mano(mano)
            datos = self.cargar_historial()
            for existente in datos["manos"]:
                if existente["id"] == mano["id"]:
                    if existente != mano:
                        raise ValueError("El identificador ya existe con datos diferentes.")
                    return False
            datos["manos"].append(mano)
            datos["manos_totales"] = len(datos["manos"])
            ruta = Path(self.ruta_archivo)
            if datos["historial_anterior"] is not None and ruta.exists():
                copia = ruta.with_name(ruta.stem + ".anterior.json")
                if not copia.exists():
                    with copia.open("xb") as f:
                        f.write(ruta.read_bytes())
            contenido = json.dumps(datos, indent=2, ensure_ascii=False)
            temporal = None
            try:
                with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=ruta.parent,
                                                 prefix=ruta.name + ".", suffix=".tmp", delete=False) as f:
                    temporal = f.name
                    f.write(contenido)
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(temporal, ruta)
            finally:
                if temporal and os.path.exists(temporal):
                    os.unlink(temporal)
            return True
        except (OSError, ValueError, KeyError, TypeError, IndexError) as error:
            raise ErrorHistorial(f"No se guardó la mano: {error}") from error
