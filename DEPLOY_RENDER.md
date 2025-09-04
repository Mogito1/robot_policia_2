# 🚀 Instrucciones para Deploy en Render

## Pasos Detallados

### 1. Preparar el Repositorio en GitHub

1. **Fork o Crea** un nuevo repositorio en GitHub
2. **Sube** todos los archivos de este directorio
3. **NO subas** archivos `.json` con datos (están en .gitignore)

### 2. Configurar en Render

1. Ve a [render.com](https://render.com) y crea una cuenta
2. Click en **"New +"** → **"Web Service"**
3. Conecta tu cuenta de GitHub
4. Selecciona tu repositorio del bot

### 3. Configuración del Servicio

**Runtime:**
- **Environment:** `Python 3`
- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `python main.py`

**Variables de Entorno:**
Agrega en la sección "Environment Variables":

| Key | Value |
|-----|-------|
| `DISCORD_TOKEN` | Tu token de Discord |

### 4. Obtener Token de Discord

1. Ve a [Discord Developer Portal](https://discord.com/developers/applications)
2. Selecciona tu aplicación o crea una nueva
3. Ve a **"Bot"** en el menú lateral
4. Copia el **Token** (click en "Copy")
5. Pégalo en la variable `DISCORD_TOKEN` en Render

### 5. Configurar el Bot en Discord

**Permisos necesarios:**
- Send Messages
- Use Slash Commands
- Read Message History
- Add Reactions
- Mention Everyone (opcional)

**URL de invitación:**
```
https://discord.com/api/oauth2/authorize?client_id=TU_CLIENT_ID&permissions=2147483648&scope=bot%20applications.commands
```

### 6. Deploy y Verificación

1. Click en **"Create Web Service"** en Render
2. Espera a que termine el build (2-3 minutos)
3. Verifica en los logs que el bot se conecte correctamente
4. Prueba los comandos en Discord

## ⚠️ Notas Importantes

- **Plan Gratuito:** Render suspende el servicio tras 15 minutos de inactividad
- **Plan Paid:** Para funcionamiento 24/7 sin interrupciones ($7/mes)
- **Variables de Entorno:** NUNCA pongas el token en el código
- **Datos:** Los archivos JSON se crean automáticamente al usar el bot

## 🔍 Troubleshooting

### Bot no se conecta:
- Verifica que el token sea correcto
- Revisa las variables de entorno en Render
- Chequea los logs del deployment

### Bot no responde:
- Asegúrate de que esté invitado al servidor
- Verifica los permisos del bot
- Los comandos son `/comando` (slash commands)

### Datos se pierden:
- En plan gratuito, los datos se resetean al hibernar
- Considera backup manual o plan paid para persistencia

---

**⭐ Tip:** Una vez funcionando, guarda la URL del servicio de Render para monitoring.