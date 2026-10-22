# Estado y continuidad del proyecto

Última actualización: 2026-10-22

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
- El checkout tiene cambios locales sin commit y algunos archivos modificados vienen de trabajo anterior. Revisar `git status` y el diff antes de preparar un commit; no agregar todos los cambios a ciegas.
- GitHub CLI (`gh`) está instalado, pero todavía no hay una sesión autenticada. El remoto existe; falta autorizar una cuenta con permiso de escritura para poder preparar un commit/push.
- No hay commits nuevos ni push realizados. Antes de preparar el commit, revisar el diff y excluir `.taste-skill/` (archivos temporales) y cualquier configuración privada/local, en especial `renting_maquinaria/settings.py`.
- Para autorizar: ejecutar `gh auth login --hostname github.com --git-protocol https --web`, abrir `https://github.com/login/device`, ingresar el código temporal que muestre la terminal y aprobar el acceso en la cuenta con permiso de escritura al repositorio. No compartir PAT ni contraseña por chat.

## Cambios relacionados recientes

- Sesión persistente al recargar, carro separado, aprobación previa al pago y descuento de stock al completar el pago.
- Rediseño visual hacia una interfaz industrial sobria y textos directos; los flujos existentes se conservan.
- Marca renovada de MaquiRent a Terra Works en portada, modales, carro y 404.
- Activos CSS/JS usan rutas absolutas para que también carguen desde `/carrito/`.
- Referencia detallada del proyecto y operación: `README.md` y `DOCUMENTACION.md`.
