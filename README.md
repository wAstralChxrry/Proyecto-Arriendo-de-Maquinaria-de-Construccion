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

### 2. Configurar la base de datos

Crear la base de datos en PostgreSQL (desde psql o pgAdmin):
```sql
CREATE DATABASE renting_db;
```

La contraseña se configura con una variable de entorno. En PowerShell, antes de correr el servidor:
```powershell
$env:DB_PASSWORD = "tu_contraseña_postgres"
```

Si el usuario o nombre de BD son distintos al default, también se pueden configurar:
```powershell
$env:DB_NAME = "renting_db"
$env:DB_USER = "postgres"
$env:DB_HOST = "localhost"
$env:DB_PORT = "5432"
```

> Si no se define `DB_PASSWORD`, el sistema usa `admin123` como valor por defecto.

### 3. Migrar la base de datos
```powershell
.\venv\Scripts\python.exe manage.py migrate
```

### 4. Crear usuario administrador (primera vez)
```powershell
.\venv\Scripts\python.exe manage.py createsuperuser
```

### 5. Levantar el servidor
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

---

## Roles del Sistema

| Rol | Permisos |
|---|---|
| `CLIENTE` (Empresa Constructora) | Ver catálogo, gestionar carro, generar contratos |
| `ADMIN` (Ejecutivo de Arriendos) | Todo lo anterior + crear maquinarias, cambiar estados de contratos |

---

## Autoría

Todas las respuestas HTTP incluyen los headers:
```
X-Student-Name: Maximo Agusto Aldea Garrido
X-Student-Section: IEC-N4-C1
X-Student-Year: 2 año
```
