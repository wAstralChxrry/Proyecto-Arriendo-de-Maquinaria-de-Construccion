# API Arriendo de Maquinaria de Construcción

> **Desarrollador:** Máximo Agusto Aldea Garrido · **Sección:** IEC-N4-C1 · **Año:** 2 año

Backend REST API construida con Django REST Framework, PostgreSQL y autenticación JWT. Incluye gestión de inventario, carrito persistente y control transaccional de stock.

---

## Inicio Rápido

### Prerrequisitos
- Python 3.x instalado
- PostgreSQL instalado y ejecutándose
- Base de datos `renting_db` creada con usuario `postgres`

### 1. Crear entorno virtual e instalar dependencias
```powershell
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configurar la base de datos y el entorno

Crear la base de datos en PostgreSQL (desde psql o pgAdmin):
```sql
CREATE DATABASE renting_db;
```

Define los valores de entorno en PowerShell antes de ejecutar comandos de Django. Genera una clave secreta nueva para cada entorno:
```powershell
$env:DJANGO_SECRET_KEY = (python -c "import secrets; print(secrets.token_urlsafe(64))")
$env:DJANGO_DEBUG = "True"
$env:ALLOWED_HOSTS = "127.0.0.1,localhost"
$secureDbPassword = Read-Host "Contraseña de PostgreSQL" -AsSecureString
$env:DB_PASSWORD = [System.Net.NetworkCredential]::new("", $secureDbPassword).Password
```

Si el usuario o nombre de BD son distintos al default, también se pueden configurar:
```powershell
$env:DB_NAME = "renting_db"
$env:DB_USER = "postgres"
$env:DB_HOST = "localhost"
$env:DB_PORT = "5432"
```

No guardes estos valores en Git. `.env.example` es una plantilla de referencia; Django lee estas opciones desde el entorno del proceso y no carga archivos `.env`. Si falta la clave, la contraseña o la lista de hosts, Django se detiene con un mensaje claro. Para producción establece `DJANGO_DEBUG=False`, una `DJANGO_SECRET_KEY` privada, `ALLOWED_HOSTS` con los dominios reales y la contraseña de PostgreSQL mediante el proveedor de despliegue.

### 3. Migrar la base de datos
```powershell
.\venv\Scripts\python.exe manage.py migrate
```

### 4. Cargar maquinarias de demostración (opcional)
En una base de datos nueva, este comando carga el catálogo de ejemplo con sus fotografías. No crea cuentas; registra tu superusuario y crea clientes desde la página.
```powershell
.\venv\Scripts\python.exe manage.py loaddata api/fixtures/maquinarias_demo.json
```

### 5. Crear usuario administrador (primera vez)
```powershell
.\venv\Scripts\python.exe manage.py createsuperuser
```

### 6. Ejecutar las pruebas
```powershell
.\venv\Scripts\python.exe manage.py test api
```

### 7. Levantar el servidor
```powershell
.\venv\Scripts\python.exe manage.py runserver
```

---

## URLs Principales

| Recurso | URL |
|---|---|
| Frontend | http://127.0.0.1:8000/ |
| API Docs (Swagger) | http://127.0.0.1:8000/api/docs/ |
| Catálogo Maquinarias | http://127.0.0.1:8000/api/maquinarias/ |
| Login JWT | http://127.0.0.1:8000/api/token/ |
| Admin Django | http://127.0.0.1:8000/admin/ |

---

## Login desde el Frontend o Swagger

1. Crear un usuario con `createsuperuser` o registrarse vía la API
2. Ir a `POST /api/token/` con `username` y `password`
3. Copiar el valor de `access` del response
4. En Swagger: presionar **Authorize** e ingresar `Bearer <token>`

---

## Arquitectura

- **Backend:** Django 6.1 + Django REST Framework
- **Base de Datos:** PostgreSQL (`renting_db`)
- **Autenticación:** JWT con claims de rol (`CLIENTE` / `ADMIN`)
- **Documentación:** drf-spectacular (OpenAPI / Swagger)
- **Filtros:** django-filter sobre catálogo de maquinarias
- **Carrito:** Persistente en DB mediante relación `OneToOneField`
- **Stock:** Descuento atómico (`transaction.atomic`) al estado `PAGADO`
- **Contratos:** Cada orden tiene un folio UUID único además de su ID interno. El UUID se asigna también a contratos existentes mediante una migración.

---

## Roles del Sistema

| Rol | Permisos |
|---|---|
| `CLIENTE` (Empresa Constructora) | Ver catálogo, gestionar su carro, confirmar contratos y consultar sus contratos |
| `ADMIN` (Ejecutivo de Arriendos) | Gestionar maquinaria, consultar contratos y actualizar sus estados |

---

## Autoría

Todas las respuestas HTTP incluyen los headers:
```
X-Student-Name: Maximo Agusto Aldea Garrido
X-Student-Section: IEC-N4-C1
X-Student-Year: 2 año
```
