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

## 2. Persistencia del Carro de Compras
A diferencia de implementaciones basadas en sesiones temporales, este sistema cuenta con un **carro de compras persistente**.
- Si un Cliente agrega un ítem al carrito y finaliza su sesión, los ítems agregados previamente se conservan intactos en la base de datos al volver a conectarse.
- Esto se logra mediante una relación uno a uno (`OneToOneField`) entre la entidad `Usuario` y la entidad `Carro`.

## 3. Reglas de Negocio y Flujo de Inventario
El sistema maneja el stock de manera transaccional para garantizar la integridad de los datos:
1. Al momento de añadir un producto al carro, **el stock no sufre descuentos**.
2. Al ejecutar el "Checkout" (Confirmar compra), el sistema verifica la disponibilidad de stock. Si la validación es exitosa, se vacía el carrito y se genera un "Contrato" en estado **PENDIENTE**. (El stock físico se mantiene intacto en esta fase).
3. **El stock se descuenta únicamente** cuando el Ejecutivo (Administrador) actualiza el contrato al estado **PAGADO**.
4. Si un contrato cambia a estado **CANCELADO** o **COMPLETADO** (devolución del equipo), el sistema **repone automáticamente** el stock de la máquina al inventario disponible.

## 4. Instrucciones de Uso y Pruebas (Swagger / OpenAPI)

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

## 5. Middleware de Autoría (Sello Estudiantil)
Para el cumplimiento de las normativas de desarrollo, se ha implementado un componente interceptor (`FooterMetadataMiddleware`). Este middleware inyecta permanentemente en las cabeceras de todas las respuestas HTTP emitidas por el servidor (Response Headers) los datos de autoría:
- `X-Student-Name: Maximo Agusto Aldea Garrido`
- `X-Student-Section: IEC-N4-C1`
- `X-Student-Year: 2 año`
