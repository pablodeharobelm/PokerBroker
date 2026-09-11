# PokerBroker

Aplicación local de práctica de Texas Hold'em No-Limit, en Python y PySide6.

## Ejecutar

Probado con Python 3.13 y PySide6 6.9.2 en Windows.

```powershell
python -m pip install -r requirements.txt
python main.py
```

El jugador ocupa el asiento inferior. Las ciegas son 20/40 y los asientos
siguen el sentido horario. Los bots actúan mediante temporizadores para
mantener la ventana disponible. Una vez cerradas las apuestas, el flop,
turn y river se reparten automáticamente con una pausa de 850 ms entre calles.
Al cerrar las apuestas del river se muestra el resultado automáticamente.
La siguiente mano se inicia con el botón. Si te retiras, puedes seguir viendo
cómo termina la mano.

El bote muestra pilas de fichas cuyo tamaño crece de forma aproximada con el
importe, con un máximo de seis pilas de ocho fichas para no tapar las cartas.
La etiqueta del bote indica siempre la cantidad exacta.

`Subir a` indica el total aportado en esa calle, no un importe adicional.
Los calls descuentan solo lo pendiente, hasta las fichas disponibles.
Una nueva sesión de práctica repone las fichas de la mesa si el jugador
se queda sin ellas o queda un solo participante con fichas. No borra el historial.

## Organización

Las estadísticas usan barras de tres tramos descriptivos, con marcador del
porcentaje real. No representan una nota ni una estrategia óptima. Los cortes
son convenciones educativas; los folds por calle son frente a cualquier apuesta,
no fold-to-cbet. Se muestra «Poca muestra» por debajo de 100 oportunidades como
aviso de interfaz, no como umbral estadístico de fiabilidad. Al pulsar una tarjeta
se explican los intervalos y las limitaciones. Referencias conceptuales:
[guía de estadísticas de PokerStars](https://www.pokerstars.es/poker/news/news/estadisticas-hud-poker-perfilar-rivales/)
y [definiciones de PokerTracker](https://www.pokertracker.com/guides/PT3/general/statistical-reference-guide).

La aplicación abre en el menú Inicio, con accesos a la práctica, estadísticas
y al historial. Salir de la mesa pausa los turnos automáticos locales; volver
los reanuda. El acceso online está desactivado: el multijugador aún no está
implementado. Los datos y la sesión se guardan en el equipo actual.

- `main.py`: construcción de la ventana y sus controles.
- `control_mesa.py`: eventos de Qt, turnos automáticos de bots y actualización visual.
- `motor_mesa.py`: jugadores, ciegas, turnos, apuestas, all-in, botes y pagos.
- `evaluador_manos.py`: selección de las cinco mejores cartas y desempates.
- `logica_poker.py`: cartas, baraja, sesión y persistencia del historial.
- `componentes_visuales.py`, `componentes_dibujo.py`, `estilos.py`: presentación.
- `interfaz_estadisticas.py`, `constructor_tarjetas.py`, `ventana_ayuda.py`: estadísticas y ayudas.
- `estadisticas.py`: cálculos a partir de las acciones de cada mano.
- `persistencia.py`: historial versionado y guardado atómico.
- `interfaz_historial.py`: listado de manos y revisión de sus acciones.

El motor no depende de Qt. La comparación de manos usa tuplas numéricas,
no los textos de la interfaz. Las cartas de todos los jugadores se reparten
al inicio; los bots no consultan las cartas de otros jugadores ni cartas futuras.
Los empates se reparten por bote; la ficha indivisible comienza por el ganador
más próximo a la izquierda del botón. Se contemplan subidas all-in incompletas,
reapertura por subidas acumuladas y devolución de aportaciones sin igualar.
Referencia para apuestas y reparto: [reglas Poker TDA 2024](https://www.pokertda.com/view-poker-tda-rules/).

## Comprobaciones

```powershell
python -B -m unittest discover -s tests -v
```

Las pruebas cubren jugadas y desempates, orden de acción, apuestas legales,
all-in, botes secundarios, reparto y conservación de fichas. También ejecutan
partidas con Qt en modo `offscreen` y un historial temporal, sin tocar los datos
del usuario. La simulación del motor usa semillas reproducibles.

## Ayudas durante la partida

El interruptor «Mostrar ayudas de entrenamiento» permite ocultar el panel
de ayudas y el nombre de la jugada. La posición y los controles de juego
siguen disponibles; la elección se mantiene entre manos de esa ejecución.

En tu turno, el panel indica el coste real de pagar (limitado a tus fichas)
y el umbral orientativo calculado como coste / bote disputable tras pagar.
Ese umbral no es la equity de tus cartas: la estimación se muestra aparte.
El panel no recomienda automáticamente pagar.
No presupone futuras apuestas o aportaciones de jugadores pendientes de actuar.
Con botes secundarios, limita el bote a tu aportación y lo identifica como
referencia; si una parte del pago quedaría sin igualar, no muestra porcentaje.
Referencia: [pot odds de PokerStars Learn](https://www.pokerstars.com/poker/learn/lesson/pot-odds/).

En flop y turn muestra proyectos de color y de escalera abierta, interna o
doble interna que se completan con una carta. No incluye proyectos backdoor,
no cuenta outs ganadores y distingue proyectos compartidos en la mesa.
Completar un proyecto no garantiza ganar. En el river no muestra proyectos.

## Equity y recuperación de sesión

El panel de ayudas muestra equity Monte Carlo frente al número de rivales
activos, asignándoles manos uniformemente aleatorias. Solo conoce tus cartas
y las comunitarias visibles. Completa la mesa y simula 600 repartos, contando
los empates como fracciones de bote. Se calcula en segundo plano y descarta
resultados de situaciones anteriores. Al ocultar las ayudas, cancela el cálculo.

El margen mostrado es una cota conservadora del error de simulación al 95 %
para ese modelo (Hoeffding), no del error al predecir a los bots. No infiere
rangos a partir de sus apuestas ni pondera botes secundarios: no debe aplicarse
automáticamente a todos los botes ni interpretarse como consejo de pagar.

La sesión se guarda automáticamente después de cada acción, cambio de calle
y reparto, y al cerrar. `historial_entrenamiento.sesion.json` conserva las fichas,
el reparto, las acciones, el turno y la opción de mostrar ayudas. Al volver
a abrir se recupera automáticamente. La recuperación reproduce las acciones
legales y conserva el estado aleatorio para mantener el resto del reparto.

Si el programa se interrumpe mientras se registra un resultado, se conserva
el registro pendiente para reintentarlo sin duplicar el historial. El archivo
de sesión usa escritura atómica. Una sesión ilegible se conserva sin modificar
y se avisa en la barra de estado; en ese caso la partida nueva no sobrescribe
esa sesión. Esta función empieza a guardar desde esta versión, no recupera
partidas cerradas con versiones anteriores. Usa una sola instancia de la app.

## Estilos de los rivales

- peco246: conservador.
- Breta232: pagador.
- Davidkim y FAKEL382: agresivos.
- _Yurec0816: equilibrado.

Pasa el cursor sobre el nombre de un rival para consultar su estilo.
El perfil se conserva entre manos y se guarda en el historial de nuevas manos.
Los registros anteriores siguen siendo compatibles aunque no tengan perfil.

`estrategia_bots.py` recibe solo las cartas del propio bot, las comunitarias
visibles y datos públicos de las apuestas. No recibe el motor ni la baraja.
Preflop considera rangos, parejas, conectividad, mismo palo y posición.
Postflop distingue la jugada propia de combinaciones compartidas en la mesa,
tiene en cuenta proyectos, rivales, presión de apuestas y stack disponible.
Los tamaños de subida respetan los límites calculados por el motor.

Son rivales de práctica basados en reglas heurísticas y algo de variación
aleatoria, no un solver GTO ni una estimación de equity. Sus estilos describen
su comportamiento, no son recomendaciones sobre cómo debe jugar el usuario.

## Estadísticas e historial

La pestaña de estadísticas utiliza únicamente las nuevas manos completas.
Cada tarjeta muestra su porcentaje, casos y base del cálculo; al pulsarla
se explica la fórmula. Cuando no existen oportunidades, aparece «Sin datos».
VPIP y PFR se calculan sobre manos repartidas; ATS y 3-bet sobre oportunidades
legales; WTSD y WWSF sobre manos donde se vio el flop; WSD sobre showdowns.
PF-FOLD usa manos repartidas y los folds postflop cuentan decisiones frente
a apuestas. Los empates con premio cuentan para WSD/WWSF; las devoluciones
de apuestas sin igualar no son premios. No se asigna una nota de Poker IQ.
Referencia: [definiciones de PokerTracker](https://www.pokertracker.com/guides/PT3/general/statistical-reference-guide).

El historial permite seleccionar una mano y revisar cartas, posiciones,
ciegas, acciones por calle, botes, devoluciones y balance neto. Como herramienta
de práctica, revela las cartas de todos los participantes una vez terminada
la mano. El historial y las estadísticas solo incluyen manos completas;
las manos interrumpidas se recuperan mediante el archivo de sesión.

Al guardar la primera mano nueva, los contadores antiguos se conservan en
`historial_anterior` dentro del JSON y se crea una copia del archivo original
llamada `historial_entrenamiento.anterior.json`. También se pueden consultar
desde la pestaña de estadísticas. No se mezclan con las métricas nuevas:
faltan las acciones originales para recalcularlos.

El guardado usa un archivo temporal y reemplazo atómico. Si falla, se ofrece
reintentarlo antes de iniciar otra mano, sin duplicar registros. Los archivos
ilegibles o de versiones desconocidas no se sobrescriben.

## Pendiente de siguientes iteraciones

- Afinar los rangos y la adaptación de los bots al historial de sus oponentes.
- Equity frente a rangos estimados y análisis individual de botes secundarios.
- Revisión paso a paso del historial y ejercicios específicos de entrenamiento.

`historial_entrenamiento.json` contiene las manos detalladas y los contadores anteriores.
Las partidas de práctica no manejan dinero real.
