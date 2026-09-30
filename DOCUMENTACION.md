# Guía y Explicación del Proyecto: Arriendo de Maquinaria

Hola, esta guía está hecha para que puedas entender y explicar tu proyecto de forma sencilla. El objetivo de este sistema es permitir que **Empresas Constructoras** (Clientes) arrienden **Maquinaria**, y que los **Ejecutivos** (Administradores) gestionen ese inventario.

**Desarrollador:** Máximo Agusto Aldea Garrido  
**Sección:** IEC-N4-C1  
**Año:** 2 año  

---

## 1. ¿Cómo funciona la Base de Datos y los Roles?
El proyecto usa **PostgreSQL**. Tenemos dos tipos de usuarios (roles) guardados en la base de datos:
- **Cliente (Empresa Constructora):** Puede ver maquinarias, agregarlas a su carrito de compras y "pagar" (crear un contrato).
- **Admin (Ejecutivo de Arriendos):** Puede crear maquinarias nuevas, editar su precio/stock y cambiar el estado de los contratos (por ejemplo, marcarlos como PAGADOS).

## 2. ¿Qué pasa con el Carrito de Compras?
A diferencia de otros sistemas donde el carrito se borra si cierras la ventana, aquí **el carrito es persistente**.
- Si un Cliente agrega una excavadora al carrito y cierra sesión, la excavadora sigue en su carrito cuando vuelva a entrar. 
- Esto se logró conectando directamente el "Carro" al "Usuario" en la base de datos de forma permanente.

## 3. ¿Cómo se descuenta el Stock? (La Lógica del Negocio)
Este es el punto más importante que debes explicar:
1. Cuando el Cliente añade algo al carrito, **el stock NO se descuenta**.
2. Cuando el Cliente le da a "Checkout" (Confirmar compra), el sistema verifica si hay stock libre. Si lo hay, vacía el carrito y crea un "Contrato" en estado **PENDIENTE**. (El stock sigue sin descontarse aquí).
3. **El stock SÓLO se descuenta cuando el Ejecutivo (Admin) cambia el contrato al estado "PAGADO"**.
4. Si por alguna razón el contrato se cancela o se devuelve la máquina, el sistema **devuelve automáticamente la máquina al stock disponible**.

## 4. ¿Cómo probarlo para tu presentación? (Paso a paso)

Para mostrar el proyecto, usa **Swagger** (la pantalla interactiva donde ves todos los rectángulos azules y verdes). Entra a: 👉 `http://127.0.0.1:8000/api/docs/`

**Paso A: Demuestra que es seguro (Error 401)**
- Intenta crear una maquinaria en el `POST /api/maquinarias/` sin estar logueado.
- *Qué decir:* "El sistema está protegido. Si no estoy logueado, me da error 401 (No autorizado)."

**Paso B: Inicia sesión (Obtener el Token)**
- Ve a `POST /api/token/`, pon tu usuario y clave y ejecútalo.
- Copia el texto largo que dice "access".
- Sube arriba del todo, dale al botón verde **Authorize**, pega el token y bloquea el candado.
- *Qué decir:* "El sistema usa Tokens (JWT) para la seguridad. Este token lleva escondido mi rol (si soy Cliente o Admin)."

**Paso C: Crea una Maquinaria**
- Vuelve a `POST /api/maquinarias/` y ahora sí, crea una máquina con stock 2.
- *Qué decir:* "Como estoy autenticado como Administrador, ahora sí me deja crear inventario."

**Paso D: Muestra el Carrito y la Compra**
- Simula que eres el cliente: Ve a `POST /api/carro-arriendo/` y agrega la máquina al carrito indicando fecha de inicio y fin.
- Ve a `POST /api/contratos/checkout/` y ejecútalo para "Confirmar".
- *Qué decir:* "El sistema calculó el total automáticamente multiplicando los días por el precio y le sumó la garantía. El contrato está PENDIENTE."

**Paso E: El Descuento de Stock**
- Ve a `PATCH /api/contratos/1/estado/` y cámbialo a `PAGADO`.
- Muestra de nuevo el catálogo en `GET /api/maquinarias/`.
- *Qué decir:* "Al pasar el contrato a PAGADO, el sistema fue a la base de datos y le restó 1 al stock de la máquina de forma automática."

## 5. El Sello de Autoría (Tus datos en cada respuesta)
Para cumplir con las normas de la prueba, creaste un "Middleware".
- Abre cualquier respuesta exitosa o de error en Swagger y baja a la sección negra que dice **Response headers** (Cabeceras de respuesta).
- Ahí siempre estarán tus datos:
  - `x-student-name: Maximo Agusto Aldea Garrido`
  - `x-student-section: IEC-N4-C1`
  - `x-student-year: 2 año`
- *Qué decir:* "Creé un código que se ejecuta en absolutamente todas las respuestas del servidor para inyectar mis datos de estudiante de forma permanente."
