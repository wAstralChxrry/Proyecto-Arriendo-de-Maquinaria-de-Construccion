# API Arriendo de Maquinaria de Construcción

> **Desarrollador:** Máximo Agusto Aldea Garrido · **Sección:** IEC-N4-C1 · **Año:** 2 año

Backend REST API construida con Django REST Framework, PostgreSQL y autenticación JWT. Incluye gestión de inventario, carrito persistente y control transaccional de stock.

---

##  Inicio Rápido

### Prerrequisitos
- Python 3.x instalado
- PostgreSQL instalado y ejecutándose
- Base de datos `renting_db` creada con usuario `postgres` / contraseña `password_seguro`

### 1. Activar el entorno e instalar dependencias
```powershell
.\venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Migrar la base de datos
```powershell
.\venv\Scripts\python.exe manage.py migrate
```

### 3. Levantar el servidor
```powershell
.\venv\Scripts\python.exe manage.py runserver
```

### 4. Abrir el Frontend
Abrir directamente en el navegador (doble clic):
```
frontend\index.html
```

---

## URLs Principales

| Recurso | URL |
|---|---|
| API Docs (Swagger) | http://127.0.0.1:8000/api/docs/ |
| Catálogo Maquinarias | http://127.0.0.1:8000/api/maquinarias/ |
| Login JWT | http://127.0.0.1:8000/api/token/ |
| Admin Django | http://127.0.0.1:8000/admin/ |

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
