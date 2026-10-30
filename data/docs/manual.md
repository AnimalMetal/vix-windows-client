# ViX Client

## Ventana principal

La ventana tiene solo dos pestañas: Catálogo accesible y Reproductor accesible. La carga de datos y reproducción funciona internamente; no necesita recorrer un navegador ni un reproductor de sitio para las acciones habituales. Se han retirado la pestaña del sitio, el acceso general al navegador y el botón de abrir el reproductor web.

Cuenta y perfil de ViX permanece visible sobre las pestañas, en un campo de solo lectura que puede enfocar y copiar. Se actualiza en silencio cuando ViX confirma un cambio. No se anuncia automáticamente al cambiar de pestaña. Durante una carga se conserva la última confirmación; si aún no se ha confirmado una sesión o perfil, se indica. F9 permite consultarlo expresamente.

## Inicio y grupos de contenido

El selector Grupo de contenido distingue las filas de Inicio, según lo que ViX ofrezca para su sesión, perfil y región. Qué contiene esta sección explica la diferencia. Todas las secciones reúne los grupos; la columna Secciones indica dónde aparece cada título y se lee con Ctrl+6.

Continuar viendo o Seguir viendo reúne títulos empezados con su perfil, cuando ViX ofrece esa fila. Recomendado para ti contiene sugerencias y no indica que haya empezado a verlas. Mi lista pertenece a su cuenta de ViX y es distinta de los Favoritos locales. Top, Más vistos o Más buscados conserva el nombre y orden de ViX. Una fila vacía o ausente puede depender de su sesión o de la carga; el cliente no inventa su contenido.

## Navegación y búsqueda

Elija una categoría en Sección. Ctrl+F lleva a Buscar en todo ViX: escriba y pulse Intro o Buscar en ViX. El filtro separado reduce solo los títulos cargados. Ctrl+M inicia o detiene la carga continua. Puede explorar otras colecciones, grupos y búsquedas cuando no aparezcan más títulos; no se garantiza haber enumerado todo el catálogo.

Intro abre un título y sus episodios. F4 muestra su información completa. Las opciones se consultan automáticamente: Temporada permite cambiar de temporada y Grupo de episodios permite elegir un rango cuando ViX divide la lista. Las otras temporadas y grupos siguen disponibles después de elegir. Actualizar temporadas y grupos vuelve a consultar las opciones si hace falta. Al cambiar se espera la carga de los episodios correspondientes, se reemplazan los anteriores y se limpia el filtro local. Una selección fallida muestra un error y no bloquea las actualizaciones. Las filas nuevas conservan foco. Tab recorre los controles y desplaza la vista si hace falta.

## En vivo

Elija En vivo en Sección. La lista muestra Número, Canal, Ahora, Horario local, A continuación, Categorías y Favorito. Ctrl+1 a Ctrl+7 consulta esas columnas. Grupo de canales permite elegir las categorías ofrecidas por ViX. El filtro local busca nombres, números y programas de los canales cargados. F4 abre la programación disponible con horarios locales; Intro reproduce el canal seleccionado.

La guía conserva selección y filtros al recibir datos nuevos. Indica cuándo falta información. Los canales y sus restricciones dependen de región y sesión. Explorar no inicia reproducción automática. F5 vuelve a cargar la guía si no hay reproducción; durante una emisión conserva el canal y utiliza los últimos datos recibidos para evitar interrumpirlo. Los favoritos guardan el canal; consulte En vivo para su programación actual.

El reproductor indica En directo o Retraso aproximado. Ir al directo vuelve al extremo disponible cuando ViX permite desplazarse. La posición absoluta permanece desactivada en directo.

## Reproductor accesible

Intro en un episodio o el botón Reproducir abre la pantalla de controles nativos. Tab recorre título, estado, reproducir/pausar, detener, saltos de diez segundos, volumen, silencio, posición en segundos, audio y subtítulos disponibles. Consultar estado anuncia tiempo y estado solo a petición.

F6, Escape desde el reproductor o Volver al catálogo regresan sin perder la selección. F8 vuelve al reproductor. Esto no detiene el vídeo: use Detener reproducción para ello. ViX puede restringir los saltos durante anuncios o emisiones en directo. Los selectores de pistas permanecen desactivados si el vídeo no las ofrece al cliente.

## Cuenta e inicio de sesión

Mi cuenta abre únicamente el flujo necesario de ViX para iniciar sesión o gestionar su cuenta. Se presenta en un diálogo separado con Volver al cliente; F6 y Escape también permiten regresar. No forma parte de las pestañas ni de la tabulación normal del cliente. Cerrar ese diálogo conserva su sesión. La gestión de cuenta interrumpe el vídeo actual porque utiliza la misma sesión interna.

Las operaciones de cuenta y suscripción las realiza usted en ese diálogo. Premium requiere acceso autorizado y algunos proveedores de autenticación pueden imponer restricciones. El cliente no recoge contraseñas ni copia los formularios a las listas. La detección del perfil utiliza la información confirmada por ViX; no se deduce del hecho de poder reproducir.

## Sonidos y opciones

Las campanitas de inicio, apertura, regreso, resultados y límites de lista son breves y suaves. Arriba y abajo tienen sonidos diferentes. Ctrl+coma abre Opciones para desactivarlos, cambiar su volumen y probarlos, independientemente del volumen del vídeo. Aceptar guarda; Cancelar conserva los valores anteriores.

Izquierda/derecha y Ctrl+1 a Ctrl+6 consultan columnas. Ctrl+D guarda o quita un favorito local. Ctrl+H explica el control enfocado; F1 abre este manual. Se mantienen las opciones de lectura de columnas y bandeja.

## Actualización y datos

Cierre la versión anterior antes de abrir 1.2.2. Si sus carpetas están juntas, la primera apertura normal importa configuración y sesión cerrada desde la versión anterior más reciente con datos de uso. No modifica esa versión ni copia un perfil abierto. Windows o ViX pueden solicitar autenticación de nuevo.

Configuración y favoritos están en data/config, sesión en data/sessions, sonidos ajustados en data/cache y registros en data/logs. No comparta esas carpetas personales. El motor Microsoft Edge WebView2 Runtime sigue siendo necesario para el funcionamiento interno.

ViX controla disponibilidad, suscripciones y formatos. Los cambios de ViX pueden requerir actualizar el cliente. La detección del perfil con una cuenta iniciada y la comprobación de los flujos nuevos con NVDA, JAWS o Narrador siguen necesitando revisión manual.

