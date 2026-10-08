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
- Para probar empresas en paralelo, abre el sitio en dos ventanas e inicia sesión con cuentas `CLIENTE` distintas. El token vive en el almacenamiento de la pestaña y la API obtiene el carro del usuario autenticado, por lo que las sesiones y los carros permanecen separados.

## 4. Reglas de Negocio y Flujo de Inventario
El sistema maneja el stock de manera transaccional para garantizar la integridad de los datos:
1. Al momento de añadir un producto al carro, **el stock no sufre descuentos**.
2. Al ejecutar el "Checkout" (Confirmar compra), el sistema verifica la disponibilidad de stock. Si la validación es exitosa, se vacía el carrito y se genera un "Contrato" en estado **PENDIENTE**. (El stock físico se mantiene intacto en esta fase).
3. **El stock se descuenta únicamente** cuando el Ejecutivo (Administrador) actualiza el contrato al estado **PAGADO**.
4. Las transiciones aceptadas son `PENDIENTE → PAGADO` o `CANCELADO`, `PAGADO → ENTREGADO` o `CANCELADO`, y `ENTREGADO → COMPLETADO` o `CANCELADO`.
5. Si un contrato pagado o entregado se cancela, o se marca como completado al devolver el equipo, el sistema repone el stock dentro de una transacción.

## 5. Autenticación, permisos y filtros
Los endpoints `/api/token/` y `/api/token/refresh/` entregan y renuevan JWT. El token incluye los claims `rol` e `is_superuser`. La lectura del catálogo es pública; el carro y checkout requieren rol de cliente; la edición del inventario y los cambios de estado requieren rol de ejecutivo. Cada cliente solo consulta sus propios contratos.

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
- **Procesamiento (Checkout):** `POST /api/contratos/checkout/` calcula el costo total (días de arriendo * tarifa diaria + garantía fija) y genera el contrato formal.

### C. Actualización de Estados
- **Modificación de Contrato:** `PATCH /api/contratos/{id}/estado/` (Requiere autenticación de Administrador). Modificar el estado a `"PAGADO"` ejecutará la validación y el descuento atómico de inventario.

## 7. Middleware de Autoría (Sello Estudiantil)
Para el cumplimiento de las normativas de desarrollo, se ha implementado un componente interceptor (`FooterMetadataMiddleware`). Este middleware inyecta permanentemente en las cabeceras de todas las respuestas HTTP emitidas por el servidor (Response Headers) los datos de autoría:
- `X-Student-Name: Maximo Agusto Aldea Garrido`
- `X-Student-Section: IEC-N4-C1`
- `X-Student-Year: 2 año`
