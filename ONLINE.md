# Multijugador: primera prueba local

## Probar con dos jugadores

Desde la carpeta del proyecto:

```powershell
python -B demo_online.py
```

Abre dos ventanas con apodos distintos y las une a la misma sala. Pulsa
«Iniciar mano» en Jugador 1. Alterna las ventanas para jugar; cada una tiene
sus cartas privadas. La demo no carga ni escribe tu historial de práctica.
Si ambas ventanas aparecen superpuestas, muévelas o alterna con Alt+Tab.

También puedes abrir dos instancias de la aplicación normal, entrar en
«Amigos · Local», iniciar el servidor en una sola, crear una sala y copiar su
código a la otra. El servidor independiente se ejecuta con:

```powershell
python -B servidor_local.py
```

## Alcance implementado

- WebSocket real en `127.0.0.1`, puerto 8765 (la demo elige uno libre).
- Salas de 2–6 jugadores, apodos únicos, 2.000 fichas y ciegas 20/40.
- El creador inicia las manos. Se mantiene el stack y rota el botón.
- El servidor valida turno, acción, importe, mano y revisión del estado.
- Las calles y el showdown avanzan mediante temporizadores del servidor.
- Cada conexión tiene un asiento asignado: un mensaje no puede elegir otro.
- La vista recibida incluye únicamente cartas propias y cartas rivales
  reveladas al showdown. No contiene semilla, baraja ni registro interno.
- Cambiar de pestaña no pausa la partida remota.

## Separación del código

`estado_mesa.py` define la vista filtrada, compartida con la actualización del
bote de práctica. `servidor_local.py` posee el motor y decide los cambios.
`VistaMesaRed` solo dibuja mensajes y emite intenciones; `PanelOnline` transporta
esas intenciones. La interfaz de práctica aún conserva su controlador local:
la migración de toda su presentación a la vista compartida es gradual.

## Límites de esta etapa

No es una versión para distribuir por Internet. La escucha está restringida
a loopback; no se abre el router ni se despliega ningún servicio externo.
Las salas viven en memoria. Salir o perder la conexión cierra la sala para
todos, sin reconexión ni recuperación. El servidor debe seguir abierto.
No hay reloj por turno, bots online, altas durante una partida, reposiciones,
cuentas ni historial online. Si queda solo un jugador con fichas, crea otra sala.
Las partidas de prueba no se mezclan con las estadísticas de práctica.

Siguientes etapas: reconexión e identidad de sesión, desconexiones y tiempo
de turno, persistencia y registro filtrado por jugador, confirmación de listo,
configuración de sala, servidor con TLS y límites de uso, prueba entre equipos
y empaquetado de la aplicación.

## Verificación

```powershell
python -B -m unittest discover -s tests -p test_online.py
```

Las pruebas abren conexiones de loopback reales y usan puertos efímeros.
