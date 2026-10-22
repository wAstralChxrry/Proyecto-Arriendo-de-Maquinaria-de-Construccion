# Estado y continuidad del proyecto

Última actualización: 2026-10-22

## Punto de continuación

- La rama `origin/master` quedó reemplazada intencionalmente por el contenido funcional de este checkout. HEAD publicado: `d548ed5` (`Complete Webpay demo flow and refresh frontend`). El push fue forzado por instrucción explícita del usuario. Los commits que antes estaban en `master` ya no forman parte de esa rama.
- El árbol de trabajo quedó limpio después del push. `master` y `respaldo-webpay` apuntan a `d548ed5`; `integrar-webpay` es una rama local antigua y divergente: no trabajar desde ella ni publicarla sin revisar su historial.
- El servidor `http://100.61.233.219/` fue consultado después del push: devolvió el título Terra Works y el HTML del hero nuevo. Gunicorn y Nginx figuraban activos. El CSS público respondió HTTP 200 y coincidió con el archivo local.
- No se completó el flujo de pago manual en navegador. La creación de transacción Webpay en integración sí respondió con URL y token; no se usó una tarjeta ni hubo cargo.
- El cambio a `master` no significa que se haya completado un pago de prueba ni valida todo el recorrido del cliente. Para verificarlo, usar una cuenta de prueba y las tarjetas/documentación vigentes de Transbank.
- No incluir claves, contraseñas, JWT ni archivos de configuración de la instancia en Git. `renting_maquinaria/settings.py` versionado lee secretos desde variables de entorno; revisar `git diff` antes de añadir cambios locales.

## Producto

- Marca visible: **Terra Works**.
- Frontend servido por Django desde `frontend/index.html`; el carro tiene una vista propia en `/carrito/` y la página de error usa `frontend/404.html`.
- El catálogo consulta la API y muestra equipos, precios y stock. La cuenta del cliente persiste entre recargas; cada carro y contrato pertenece a su cuenta.
- Flujo de arriendo: el cliente arma el carro y envía una solicitud; el ejecutivo la aprueba; el cliente paga en Webpay Plus de integración; el servidor confirma el resultado con Transbank y solo entonces descuenta stock.

## Webpay

- SDK oficial Python: `transbank-sdk==6.1.0`, en ambiente `TEST` con credenciales de integración que incluye el SDK.
- Inicio autenticado: `POST /api/contratos/{id}/pago-demo/`. El nombre `pago-demo` se mantiene por compatibilidad; ahora crea la transacción y devuelve `url` y `token`.
- El navegador envía `token_ws` a la URL de Webpay. Transbank vuelve por `POST /webpay/retorno/`; Django confirma el token mediante el SDK y valida orden, monto y autorización.
- Los pagos rechazados o cancelados no descuentan inventario. La ruta de retorno es pública para recibir la respuesta del proveedor y está exenta de CSRF; la operación se valida con el token firmado/emitido por Transbank y el token guardado en el contrato.
- La migración `0006_contrato_webpay_token_and_more` ya fue aplicada en la instancia de producción.
- Se verificó una creación de transacción contra el ambiente real de integración: Transbank respondió con la URL de Webpay y un token. No se envió una tarjeta ni se hizo un cargo.
- Falta completar una compra manual de integración en el navegador para comprobar el ciclo extremo a extremo con una tarjeta de prueba de Transbank. No se procesan cargos reales.

## Operación y entrega

- Instancia actual: Ubuntu, aplicación en `/home/ubuntu/ProyectoMaquinaria`, servida por Gunicorn y Nginx. IP conocida: `100.61.233.219`.
- Después de cambios backend, reiniciar `sudo systemctl restart gunicorn`; comprobar con `systemctl is-active gunicorn`.
- Repositorio configurado como `origin`: `https://github.com/wAstralChxrry/Proyecto-Arriendo-de-Maquinaria-de-Construccion`.
- Remoto: `https://github.com/wAstralChxrry/Proyecto-Arriendo-de-Maquinaria-de-Construccion`, rama principal `master`.
- GitHub CLI (`gh`) está instalado y se autenticó con la cuenta `wAstralChxrry`. No solicitar ni copiar tokens o contraseñas por chat.
- Para cambios siguientes: empezar con `git status -sb`, trabajar desde `master`, revisar `git diff`, crear un commit y hacer push normal. No hace falta otro force push para el estado actual.
- La carpeta del checkout es también la ruta de la aplicación en la instancia. Después de cambios backend, reiniciar `sudo systemctl restart gunicorn` y verificar con `systemctl is-active gunicorn`; Nginx sirve los activos y normalmente no requiere reinicio para cambios de HTML/CSS.

## Cambios relacionados recientes

- Sesión persistente al recargar, carro separado, aprobación previa al pago y descuento de stock al completar el pago.
- Rediseño visual hacia una interfaz industrial sobria y textos directos; los flujos existentes se conservan.
- Marca renovada de MaquiRent a Terra Works en portada, modales, carro y 404.
- Activos CSS/JS usan rutas absolutas para que también carguen desde `/carrito/`.
- Referencia detallada del proyecto y operación: `README.md` y `DOCUMENTACION.md`.
- Preferencia del usuario para el producto: textos naturales y profesionales, sin frases de marketing genéricas ni apariencia de plantilla de IA; la marca es Terra Works.
