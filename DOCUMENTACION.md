# Documentación del Proyecto: API Arriendo de Maquinaria

El objetivo de este sistema es permitir que **Empresas Constructoras** (Clientes) arrienden **Maquinaria**, y que los **Ejecutivos** (Administradores) gestionen el inventario y las transacciones.

**Desarrollador:** Máximo Agusto Aldea Garrido  
**Sección:** IEC-N4-C1  
**Año:** 2 año  

---

## 1. Arquitectura de Base de Datos y Roles
El proyecto utiliza **PostgreSQL** como motor de base de datos relacional. El sistema contempla dos tipos de usuarios (roles) principales:
- **Cliente (Empresa Constructora):** Tiene permisos para visualizar maquinarias, gestionar su carro de compras y generar contratos (checkout).
- **Administrador (Ejecutivo de Arriendos):** Tiene privilegios para crear maquinarias nuevas, editar su precio o stock, y actualizar el estado de los contratos generados.

`Usuario.rol` y `Contrato.estado` usan opciones (`choices`) para limitar los valores válidos. `Carro` se relaciona uno a uno con `Usuario`; `ItemCarro` relaciona el carro con cada maquinaria y su período; `DetalleContrato` conserva los equipos, fechas y subtotales de cada contrato. Cada contrato tiene un `codigo_uuid` único para identificarlo externamente, además del ID numérico que usan las rutas de la API.

## 2. Configuración del entorno
La conexión usa `django.db.backends.postgresql`. La clave de Django, el modo de depuración, los hosts permitidos y la contraseña de PostgreSQL se leen desde variables de entorno. No hay valores predeterminados para la clave ni la contraseña.

Para desarrollo local, configura `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=True`, `ALLOWED_HOSTS=127.0.0.1,localhost` y `DB_PASSWORD` antes de ejecutar `manage.py`. En producción configura `DJANGO_DEBUG=False`, la clave privada, los dominios reales en `ALLOWED_HOSTS` y las credenciales de PostgreSQL desde el servicio de despliegue. `.env.example` enumera las variables; Django no carga automáticamente ese archivo.

## 3. Persistencia del Carro de Compras
A diferencia de implementaciones basadas en sesiones temporales, este sistema cuenta con un **carro de compras persistente**.
- Si un Cliente agrega un ítem al carrito y finaliza su sesión, los ítems agregados previamente se conservan intactos en la base de datos al volver a conectarse.
- Esto se logra mediante una relación uno a uno (`OneToOneField`) entre la entidad `Usuario` y la entidad `Carro`.
- Para probar empresas en paralelo, abre el sitio en dos perfiles de navegador e inicia sesión con cuentas `CLIENTE` distintas. El token se conserva en el almacenamiento local del navegador entre recargas, y la API obtiene el carro del usuario autenticado, por lo que las sesiones y los carros permanecen separados.

## 4. Reglas de Negocio y Flujo de Inventario
El sistema maneja el stock de manera transaccional para garantizar la integridad de los datos:
1. Al momento de añadir un producto al carro, **el stock no sufre descuentos**.
2. Al ejecutar el checkout desde la página `/carrito/`, se valida la disponibilidad, se vacía el carro y se crea un contrato **PENDIENTE**, sin descontar stock.
3. El Ejecutivo aprueba la solicitud y la deja **APROBADA**. Esta aprobación todavía no descuenta inventario.
4. Desde **Mis solicitudes**, el cliente inicia un pago con Webpay Plus en el ambiente de integración de Transbank. La aplicación crea la transacción con el SDK oficial, redirige al formulario de Webpay y recibe el retorno en `/webpay/retorno/`. El servidor confirma el token con Transbank; solo ante una respuesta `AUTHORIZED` válida el contrato pasa a **PAGADO** y descuenta stock dentro de una transacción. El ambiente de integración usa credenciales de prueba y no realiza cobros reales.
5. Las transiciones son `PENDIENTE → APROBADO` o `CANCELADO`, `APROBADO → CANCELADO`, `PAGADO → ENTREGADO` o `CANCELADO`, y `ENTREGADO → COMPLETADO` o `CANCELADO`. Un contrato pagado o entregado que se cancela, o se completa al devolver el equipo, repone el stock dentro de una transacción.

## 5. Autenticación, permisos y filtros
Los endpoints `/api/token/` y `/api/token/refresh/` entregan y renuevan JWT. El token incluye los claims `rol` e `is_superuser`. La lectura del catálogo es pública; el carro y checkout requieren rol de cliente; la edición del inventario y los cambios de estado requieren rol de ejecutivo. Cada cliente solo consulta sus propios contratos desde la sección **Mis arriendos**, que muestra el estado, folio, fechas y equipos asociados.

El catálogo se filtra con `django-filter`: `categoria`, `tarifa_min` y `tarifa_max`. También permite búsqueda por nombre o categoría mediante `search`.

## 6. Instrucciones de Uso y Pruebas (Swagger / OpenAPI)

Para interactuar con la API, el sistema provee una interfaz gráfica generada automáticamente mediante OpenAPI (Swagger).
**URL de acceso:** `http://127.0.0.1:8000/api/docs/`

### A. Seguridad y Autenticación (JWT)
El sistema está protegido mediante JSON Web Tokens (JWT). El token inyecta el *claim* del rol del usuario (`CLIENTE` o `ADMIN`).
- Para obtener un token, se debe consumir el endpoint `POST /api/token/` ingresando credenciales válidas.
- En la interfaz de Swagger, el token de acceso obtenido ("access") debe ingresarse en el botón superior **Authorize** para desbloquear los endpoints protegidos.
- Las consultas a endpoints protegidos sin proveer un token retornarán un error HTTP `401 Unauthorized`.

### B. Gestión de Catálogo y Carro
- **Creación de Maquinarias:** `POST /api/maquinarias/` (Requiere autenticación de Administrador).
- **Agregar al Carro:** `POST /api/carro-arriendo/` especificando el ID de la máquina, `fecha_inicio` y `fecha_fin`.
- **Procesamiento (Checkout):** `POST /api/contratos/checkout/` calcula el costo total (días de arriendo * tarifa diaria + garantía fija) y genera el contrato pendiente.
- **Aprobación ejecutiva:** `PATCH /api/contratos/{id}/estado/` con `{"estado":"APROBADO"}`.
- **Inicio de pago:** `POST /api/contratos/{id}/pago-demo/` requiere que el cliente dueño del contrato esté autenticado y que el contrato esté aprobado. Crea una transacción en Webpay Plus integración y responde con `url` y `token`; el frontend envía el token a esa URL mediante un formulario `POST`.
- **Retorno de Webpay:** `POST /webpay/retorno/` recibe `token_ws` desde Transbank, confirma la operación con el SDK y valida monto, orden y autorización antes de marcar el contrato pagado. Si Webpay cancela o rechaza, no se descuenta stock.
- **Configuración:** el servidor usa los códigos de integración de prueba incluidos por el SDK oficial. Si se necesita fijar una URL pública de retorno, configura `WEBPAY_RETURN_URL`; de lo contrario, la URL se genera desde el host que recibió la solicitud.

La migración `0006_contrato_webpay_token_and_more` agrega al contrato los campos temporales del intento Webpay. Los tokens activos permiten retomar el formulario durante 15 minutos; luego se puede iniciar otro intento. Si el pago se autoriza pero ya no hay inventario para el período, el sistema solicita la reversa a Transbank y no confirma el arriendo.

### C. Actualización de Estados
- **Actualización de Contrato:** `PATCH /api/contratos/{id}/estado/` (Requiere autenticación de Administrador). Permite aprobar solicitudes, entregar equipos, cancelar contratos y marcar devoluciones; el pago se inicia en el endpoint indicado y se confirma al volver desde Webpay.

## 7. Middleware de Autoría (Sello Estudiantil)
Para el cumplimiento de las normativas de desarrollo, se ha implementado un componente interceptor (`FooterMetadataMiddleware`). Este middleware inyecta permanentemente en las cabeceras de todas las respuestas HTTP emitidas por el servidor (Response Headers) los datos de autoría:
- `X-Student-Name: Maximo Agusto Aldea Garrido`
- `X-Student-Section: IEC-N4-C1`
- `X-Student-Year: 2 año`
