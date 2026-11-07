# Post del render 3D en r/ClaudeCode (2026-11-07)

Pendiente. Se sigue en una sesión en la PC del dueño: el proyecto del video
(`videos/cs2-osm-toolkit-3d/`, sin versionar) y la GPU con la que se renderiza
están ahí, y desde la nube Reddit no abre. Lo hizo la sesión del render
("Render 3D para r/claudecodeai", 2026-11-02 y 03), que también corre en la PC.

## Qué pasó en r/ClaudeAI

- El modbot retiró la primera versión a los minutos: no contaba cómo ayudó Claude,
  y los links de apoyo contaron como promoción (las reglas del Showcase están en la
  memoria local, `claudeai-showcase-reglas.md`). La segunda versión salió bien,
  republicada el lunes 2026-11-02 cerca de las 22 h (la misma hora en Nueva York).
- A los tres días tenía 11 mil vistas, 36 votos (un 0,3 % de las vistas) y 11
  comentarios, contando el del bot y las respuestas propias. Las estrellas pasaron de
  44 a 52, y entró un solo pedido de ciudad (Ottawa, #138). Del 20 al 22 de octubre
  habían entrado 23.
- Los comentarios fueron todos positivos pero cortos ("very nice", "pretty cool"), y
  nadie preguntó cómo se hizo. Uno pidió "non-NA cities", cuando 51 de las 77
  ciudades están fuera de Norteamérica: el video solo muestra Nueva York y
  Minneapolis. El bot fijó arriba un comentario que manda a r/ClaudeGameDev. El único
  comentario largo (thongjesus, con un caso de uso para la industria) quedó sin
  respuesta.
- Por qué rindió poco: el post vendía el mapa en un sub que busca cómo trabajó
  Claude; el video arranca con su cuadro más flojo; el título explicaba en vez de
  enganchar; y salió de noche.

## Cambios al video

No hace falta un video nuevo: se reusan la escena, los datos y el render, y cambia
el montaje. Los tres primeros cambios los propuso la sesión del render el
2026-11-03, que calculó unas 2 h 30 m con dos renders completos:

1. **Arranque fuerte, unos 2 s:** dos cortes rápidos, el vuelo entre las torres de
   Midtown y las capas encendidas de Minneapolis, sin textos y con un golpe de
   sonido; recién después, el título. El primer cuadro pasa a ser Midtown, que sirve
   de miniatura.
2. **Brooklyn más corto, de 7,5 a unos 4,5 s:** sacar el antes y después de las casas
   en hilera y dejar la tarjeta de precisión (81 % y 67 %). La narración queda en
   "Checked against property records, most homes land in the right zone."
3. **"The whole world" con un globo:** un planeta oscuro girando, con brillo de
   atmósfera y los 77 puntos de las ciudades encendiéndose mientras la narración dice
   "the whole world". Con "choose any city" corta al recuadro sobre Brooklyn, como
   ahora. Responde la duda de que sea solo de Norteamérica.

Los otros tres, para que en r/ClaudeCode se vea qué hizo Claude Code (2026-11-07):

4. **Decir que lo hizo Claude Code:** el arranque sigue sin textos, pero el título que
   viene después cuenta que el render lo hizo Claude Code, cuadro por cuadro; por
   ejemplo, "Claude Code rendered this, frame by frame".
5. **El bug de la Bolsa, antes y después (unos 4 s, en el lugar que libera
   Brooklyn):** el Distrito Financiero con la Bolsa, el Woolworth Building y la
   Reserva Federal en el color de industria, y después en el de oficinas, con un texto
   tipo "Making this video, Claude Code found a bug in my map". Es el arreglo del PR
   #137: los edificios grandes con solo `building=yes` y fuera de toda zona de uso del
   suelo salían como industria, sin mirar la altura. La zonificación de antes está en
   git, como la vieja de Brooklyn, en `700ec24a` (el commit anterior al arreglo); la
   de después, en `e009ad06`:

   ```bash
   git show 700ec24a:visualizer/cities/new_york/datos_zonificacion.json
   ```

   Verificado en esos datos: la Bolsa (vía OSM 278053530), el Woolworth Building
   (75363809) y la Reserva Federal (278042228) pasan de `industrial` a
   `office_high`. Las alturas del render no cambian, solo el color.
6. **La narración:** cambiar dos o tres frases sobre para quién es el mapa por otras
   sobre cómo se hizo: que Claude Code escribió el render y que encontró el bug.

Con todo, el video queda en alrededor de un minuto. A las 2 h 30 m calculadas hay
que sumarles, a ojo, una hora más por el bug y la narración.

## Texto del post

- Antes de escribir, leer las reglas y los flairs de r/ClaudeCode en la barra
  lateral. Como referencia, las del Showcase de r/ClaudeAI: decir que lo hiciste vos
  y que se hizo con Claude Code, contar qué hace y cómo ayudó Claude Code, que es
  gratis y cómo probarlo, poco marketing y ningún link de afiliado.
- **El enfoque:** qué hizo Claude Code y cómo, en concreto. Por ejemplo, el render
  cuadro por cuadro, los fallos que encontró y arregló y el bug real del mapa que salió
  al hacerlo. También cómo se trabaja el proyecto: el CLAUDE.md en español, el
  AGENTS.md para Codex, los planes antes del código, el debate entre Claude y Codex
  sobre el layout, los tests con Playwright y los workflows de varios agentes. El valor
  del mapa va en una o dos líneas.
- **El título:** que cuente algo sorprendente que hizo Claude Code, con Claude Code
  al principio y no al final.
- Sin links de apoyo, sin rayas largas y sin palabras de marketing. Al final, una
  pregunta que invite a contar la práctica propia.
- **Links:** el mapa con la marca para medir,
  https://osyanne.github.io/CitiesSkylines2-osm-toolkit/?ref=r-claudecode (así figura
  en GoatCounter), y el código, https://github.com/Osyanne/CitiesSkylines2-osm-toolkit.
  Si suman, también el CLAUDE.md y `docs/plans/2026-09-26-layout-visor/`.
- **Primer comentario:** la imagen 4K, el link a Minneapolis, que tiene todas las
  capas, y el prompt que arrancó el video, sin el "and support me" del final.

Datos verificados el 2026-11-07:

- **El proyecto:** 448 commits desde el 2026-04-19, 57 PR fusionados, 19 releases y
  742 tests.
- **El mapa:** 77 ciudades en 31 países, 51 de ellas fuera de Norteamérica; 79 issues
  y 53 estrellas.
- **La precisión:** la zona coincide con el catastro en el 81 % de las viviendas de
  Filadelfia y en el 67 % de las de Nueva York.
- **El arreglo de las torres:** sacó 958 edificios de la industria en Nueva York.

Una anécdota de esta semana, si suma: al contador de visitas (GoatCounter, PR #140)
lo revisó un workflow de tres agentes. Encontró que una recarga le acreditaba la
visita al propio sitio y que el texto de privacidad no decía todo lo que se registra;
los dos se arreglaron antes de fusionar.

## Publicación y medición

- Publicar un día de semana entre las 9 y las 11 de la mañana de Nueva York, que suele
  rendir más; es la misma hora que en la PC del dueño. Quedarse la primera hora
  contestando con contenido, y corregir enseguida los malentendidos, como el de "solo
  Norteamérica".
- Subir solo el video, desde la pestaña Multimedia, y pegar el cuerpo con el editor en
  Markdown.
- Medir en https://cs2-osm-toolkit.goatcounter.com: las visitas con `r-claudecode` en
  Referrers, las estrellas (la base es 53) y los pedidos de ciudades.

## Archivos en la PC

En `videos/cs2-osm-toolkit-3d/`: `REDDIT-POST.md` (los borradores anteriores),
`out/nyc-3d.mp4`, `out/thumb-layers.png`, `out/thumb-midtown.png` y
`out/nyc-3d-4k.png`. En la memoria local del proyecto, `claudeai-showcase-reglas.md`
y `cs2-render-3d-nyc.md`.
