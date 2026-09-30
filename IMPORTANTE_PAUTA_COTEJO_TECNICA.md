# IMPORTANTE: PAUTA DE COTEJO TÉCNICA (Checklist de Defensa)

Este documento es estrictamente para ti. Úsalo como "torpedo" o guía de estudio para tu defensa ante el profesor. Aquí están las respuestas exactas (teóricas y prácticas) a cada punto que te van a evaluar.

---

## 1. Sobre tu pregunta: "¿Es necesario un Frontend?"
**La respuesta es NO.** 
La rúbrica es clarísima: *"El objetivo de esta evaluación es medir la capacidad técnica en la construcción de servicios Backend con Django REST Framework"*. Todo el sistema es una API (el motor trasero).
Lo único visual que te pedían era que los datos del alumno fueran visibles. Eso lo solucionamos de dos maneras increíbles:
1. Aparecen escritos en la portada misma de tu **Swagger HTML** (`/api/docs/`).
2. Viajan permanentemente ocultos en los **Headers HTTP** gracias a nuestro Middleware. 
Con Swagger (la interfaz de la API) tienes todo el "frontend" que necesitas para presentar y aprobar.

---

## II. Pauta de Cotejo Técnica (Checklist Explicado)

### [✓] Conexión activa a PostgreSQL en `settings.py`
- **¿Dónde está?** En el archivo `settings.py`, dentro de la variable `DATABASES`.
- **Qué responder si te preguntan:** "Configuré el `ENGINE` de la base de datos usando `django.db.backends.postgresql`. Definí el nombre de la DB (`renting_db`), el usuario (`postgres`) y el puerto por defecto (`5432`). No usé SQLite."

### [✓] Swagger / OpenAPI operativo en `/api/docs/`
- **¿Dónde está?** En `renting_maquinaria/urls.py` (usando `SpectacularSwaggerView`) y en `settings.py` (`SPECTACULAR_SETTINGS`).
- **Qué responder si te preguntan:** "Instalé e integré la librería `drf-spectacular` para autogenerar el esquema OpenAPI de mi proyecto. Configuré la ruta en `/api/docs/` para tener una interfaz interactiva donde probar mis endpoints."

### [✓] Código documentado en bloques explícitos
- **¿Dónde está?** En todos los archivos (`models.py`, `views.py`, `serializers.py`, `urls.py`, `middleware.py`).
- **Qué responder si te preguntan:** "Me aseguré de agregar comentarios en español simple antes de las clases y métodos importantes, explicando la lógica de negocio (como el descuento de stock o el rol)."

### [✓] Datos Alumno presentes en vista/footer base
- **¿Dónde está?** En `api/middleware.py` y en la configuración de Swagger en `settings.py`.
- **Qué responder si te preguntan:** "Implementé un `FooterMetadataMiddleware`. Teóricamente, un middleware es código que intercepta la petición antes de devolver la respuesta. Yo lo usé para inyectar mis datos (Nombre, Sección, Año) como cabeceras (`X-Student-Name`) en *todas* las respuestas de la API. Además, agregué mis datos en la descripción inicial de Swagger para que se vean gráficamente."

### [✓] Modelos Atributo con CHOICES definido
- **¿Dónde está?** En `api/models.py`.
- **Qué responder si te preguntan:** "Usé atributos `choices` en dos partes: en el modelo `Usuario` para definir los roles (`CLIENTE` y `ADMIN`), y en el modelo `Contrato` para definir el estado de la compra (`PENDIENTE`, `PAGADO`, `CANCELADO`, etc.)."

### [✓] Filtros django-filter configurado en endpoints
- **¿Dónde está?** En `api/views.py`, dentro de `MaquinariaViewSet`.
- **Qué responder si te preguntan:** "Integré `DjangoFilterBackend` en la vista de las Maquinarias. Configurarlo me permite que, con solo enviar parámetros por la URL (ej: `?categoria=Excavacion`), la base de datos me devuelva los datos filtrados."

### [✓] Autenticación Login JWT retornando tokens y claims de rol
- **¿Dónde está?** En `api/serializers.py` (`CustomTokenObtainPairSerializer`).
- **Qué responder si te preguntan:** "Al heredar de `TokenObtainPairSerializer`, sobrescribí el método `get_token(cls, user)` para inyectar un 'claim' personalizado en el payload del JSON Web Token. En mi caso, metí la variable `user.rol` para que el sistema sepa qué rol tiene el usuario sin tener que consultar a la base de datos de nuevo."

### [✓] Carro Persistencia post-logout en PostgreSQL
- **¿Dónde está?** En `api/models.py` (relación OneToOne) y `api/views.py` (uso de `get_or_create`).
- **Qué responder si te preguntan:** "En lugar de guardar el carrito en la Sesión del navegador o en LocalStorage, creé un modelo `Carro` en PostgreSQL vinculado mediante una llave foránea única (`OneToOneField`) al `Usuario`. En las vistas, uso `Carro.objects.get_or_create()`, así el carrito nunca se pierde aunque el usuario cierre la pestaña o el logout."

### [✓] Stock Validación y descuento atómico al estado PAGADO
- **¿Dónde está?** En `api/views.py`, dentro de `ContratoViewSet` (método `estado`).
- **Qué responder si te preguntan:** "Usé `transaction.atomic()` para garantizar la integridad de la base de datos (si algo falla en medio del proceso, hace rollback automático). Itero sobre los detalles del contrato: si el estado pasa a `PAGADO`, le resto 1 al `stock_disponible` de la máquina y guardo en DB. Si pasa a `CANCELADO` o `COMPLETADO`, le sumo 1 de vuelta. Todo en el backend de forma segura."
