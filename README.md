# 🤖 Bot Discord CNP SC-RP

Bot de Discord para servidor de roleplay de Policía Nacional con sistema de fichaje, gestión de ausencias y controles administrativos.

## ✨ Características

- **Sistema de Fichaje:** Control de horas de trabajo con inicio/cierre automático
- **Gestión de Ausencias:** Registro y administración de permisos y vacaciones  
- **Roles Administrativos:** Sistema configurable de permisos por roles
- **Histórico Completo:** Seguimiento detallado de fichajes y horas trabajadas
- **Interfaz Amigable:** Comandos slash con formato limpio y menciones

## 🚀 Deploy en Render

### 1. Fork este repositorio

Haz fork de este repo a tu cuenta de GitHub.

### 2. Conectar con Render

1. Ve a [Render.com](https://render.com)
2. Crea una cuenta o inicia sesión
3. Click en "New +" → "Web Service"
4. Conecta tu repositorio de GitHub
5. Selecciona este repositorio

### 3. Configuración en Render

**Build & Deploy:**
- **Environment:** `Python 3`
- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `python main.py`

**Variables de Entorno:**
Agrega estas variables en la sección "Environment Variables":

```
DISCORD_TOKEN=tu_token_de_discord_aqui
```

### 4. Obtener Token de Discord

1. Ve a [Discord Developer Portal](https://discord.com/developers/applications)
2. Crea una nueva aplicación o selecciona la existente
3. Ve a "Bot" en el menú lateral
4. Copia el token y úsalo en la variable `DISCORD_TOKEN`

### 5. Invitar el Bot

URL de invitación con permisos necesarios:
```
https://discord.com/api/oauth2/authorize?client_id=TU_CLIENT_ID&permissions=2147483648&scope=bot%20applications.commands
```

Reemplaza `TU_CLIENT_ID` con el ID de tu aplicación.

## 🛠️ Desarrollo Local

### Instalación

```bash
# Clonar repositorio
git clone https://github.com/tu-usuario/tu-repo.git
cd tu-repo

# Crear entorno virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows

# Instalar dependencias
pip install -r requirements.txt

# Crear archivo de entorno
cp .env.example .env
# Editar .env y agregar tu DISCORD_TOKEN
```

### Ejecutar

```bash
python main.py
```

## 📋 Comandos Disponibles

### Para Usuarios:
- `/fichar` - Iniciar fichaje de trabajo
- `/cerrarfichaje` - Cerrar fichaje actual
- `/verfichajes` - Ver tus horas totales trabajadas
- `/fichando` - Ver quién está fichando actualmente

### Para Administradores:
- `/config` - Configurar roles administrativos
- `/gestionar` - Gestionar fichajes de usuarios
- `/ausencia` - Registrar ausencias/permisos
- `/quitarausencia` - Eliminar ausencias
- `/exportar` - Exportar datos a Excel
- `/stats` - Estadísticas del servidor

## 🔧 Configuración

El bot se auto-configura la primera vez que se ejecuta. Los administradores pueden usar `/config` para establecer roles con permisos administrativos.

## 📊 Persistencia de Datos

Los datos se almacenan en archivos JSON locales:
- `fichajes_activos.json` - Fichajes en curso
- `historico_fichajes.json` - Histórico completo
- `horas_totales.json` - Horas acumuladas por usuario
- `ausencias.json` - Registro de ausencias
- `roles_admin.json` - Configuración de roles
- `servidor_config.json` - Configuración de canales

## 🔒 Seguridad

- Los tokens se manejan como variables de entorno
- Los archivos de datos no se suben al repositorio
- Sistema de permisos por roles configurable

## 📝 Licencia

Este proyecto es de código abierto. Úsalo libremente para tu servidor de Discord.

---

**Desarrollado para:** CNP SC-RP "Policía Nacional - SpainCityRP"