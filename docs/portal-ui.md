# Interfaz visual del portal

## Objetivo

`portal-ui` ofrece una pantalla web para consultar afiliados sin cambiar el contrato del gateway ni modificar el cliente API original `portal-client`. El diseño FESC Orbit usa una paleta casi negra con grises y blancos, navegación horizontal compacta, tarjetas planas de alto contraste y una disposición adaptable a móvil. Es una dirección visual original inspirada en la referencia compartida, no reutiliza logotipos ni imágenes de terceros.

## Componentes y flujo

- `services/portal-ui/static/index.html` declara la navegación, el formulario, el perfil, la empresa y la lista de beneficiarios.
- `services/portal-ui/static/styles.css` contiene el tema visual, estados de interacción, accesibilidad y breakpoints responsivos.
- `services/portal-ui/static/app.js` consulta la API del servicio, representa los datos canónicos y controla la búsqueda.
- `services/portal-ui/app.py` sirve los recursos estáticos y actúa como intermediario para el gateway. El token `PORTAL_TOKEN` queda en el servidor; el navegador solo llama al mismo origen.

La pantalla inicial está en `http://localhost:8093`. El botón de búsqueda consulta `GET /api/member/{documento}` del servicio visual; este reúne afiliado, beneficiarios y empresa desde los endpoints autenticados del gateway. `GET /api/health` refleja la disponibilidad del gateway. El portal conserva su contrato original en `http://localhost:8092/portal/afiliados/{documento}`.

La navegación lateral reúne accesos directos a Afiliados, Empresas y Beneficiarios. La cabecera mantiene el estado del sistema, el selector de idioma y el perfil; también incluye un menú Recursos con enlaces organizados por categoría. El selector del globo ofrece Español e English y recuerda la elección en el navegador. El selector y el menú de recursos se pueden usar con teclado, se cierran con `Escape` o al pulsar fuera, y se adaptan a móvil.

## Privacidad y accesibilidad

El número de documento se muestra enmascarado por defecto y solo se revela al activar el botón «Mostrar». Al iniciar otra búsqueda, los datos de la consulta previa se ocultan; si no hay coincidencia, la ficha no queda visible. Los recursos se restringen a una lista de rutas conocidas y el servidor añade una política CSP, `nosniff` y `no-store`.

La búsqueda acepta dígitos, informa errores mediante una región accesible, permite navegación con teclado y tiene el atajo `/` para enfocar el campo cuando no se está escribiendo en otro control. Respeta `prefers-reduced-motion`; el diseño responde a móvil, tableta y escritorio.

## Pruebas

La suite `tests/test_portal_ui.py` valida la página, recursos locales, estado del gateway, consultas existentes y desconocidas. Se ejecuta junto con las pruebas del gateway mediante `docker compose --profile test run --rm tests`.
