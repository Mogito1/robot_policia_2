import discord
from discord.ext import commands, tasks
import os
from dotenv import load_dotenv
from keep_alive import keep_alive  # 🔹 Mantiene vivo el bot en Render
import asyncio
import json
import aiofiles
from datetime import datetime, timedelta

# Cargar variables de entorno
load_dotenv()

# Configuración del bot - usando slash commands en lugar de prefijo
intents = discord.Intents.default()

bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

# Almacenamiento de configuración y ausencias
servidor_config = {}
ausencias_activas = {}
roles_admin = {
}  # {guild_id: [role_ids]} - roles que pueden usar comandos de administración

# Sistema de fichaje de horas
fichajes_activos = {}  # {user_id: {'inicio': datetime, 'guild_id': int}}
historico_fichajes = {
}  # {guild_id: {user_id: [{'inicio': str, 'fin': str, 'horas': float, 'fecha': str}]}}
horas_totales = {}  # {guild_id: {user_id: total_horas}}
periodos_fichaje = {
}  # {guild_id: [periodo1, periodo2, ...]} - histórico de períodos


# Funciones para gestión de datos
async def cargar_datos():
    """Cargar configuración, ausencias y fichajes desde archivos"""
    global servidor_config, ausencias_activas, fichajes_activos, historico_fichajes, horas_totales, periodos_fichaje, roles_admin
    try:
        # Cargar configuración de servidores
        if os.path.exists('servidor_config.json'):
            async with aiofiles.open('servidor_config.json', 'r') as f:
                content = await f.read()
                servidor_config = json.loads(content)

        # Cargar ausencias activas
        if os.path.exists('ausencias.json'):
            async with aiofiles.open('ausencias.json', 'r') as f:
                content = await f.read()
                ausencias_activas = json.loads(content)

        # Cargar fichajes activos
        if os.path.exists('fichajes_activos.json'):
            async with aiofiles.open('fichajes_activos.json', 'r') as f:
                content = await f.read()
                data = json.loads(content)
                # Convertir strings de datetime de vuelta a datetime objects
                for user_id, fichaje in data.items():
                    fichaje['inicio'] = datetime.fromisoformat(
                        fichaje['inicio'])
                fichajes_activos = data

        # Cargar histórico de fichajes
        if os.path.exists('historico_fichajes.json'):
            async with aiofiles.open('historico_fichajes.json', 'r') as f:
                content = await f.read()
                historico_fichajes = json.loads(content)

        # Cargar horas totales
        if os.path.exists('horas_totales.json'):
            async with aiofiles.open('horas_totales.json', 'r') as f:
                content = await f.read()
                horas_totales = json.loads(content)

        # Cargar períodos de fichaje
        if os.path.exists('periodos_fichaje.json'):
            async with aiofiles.open('periodos_fichaje.json', 'r') as f:
                content = await f.read()
                periodos_fichaje = json.loads(content)

        # Cargar roles administrativos
        if os.path.exists('roles_admin.json'):
            async with aiofiles.open('roles_admin.json', 'r') as f:
                content = await f.read()
                roles_admin = json.loads(content)

    except Exception as e:
        print(f"Error cargando datos: {e}")


async def guardar_datos():
    """Guardar configuración, ausencias y fichajes en archivos"""
    try:
        # Guardar configuración de servidores
        async with aiofiles.open('servidor_config.json', 'w') as f:
            await f.write(json.dumps(servidor_config, indent=2))

        # Guardar ausencias activas
        async with aiofiles.open('ausencias.json', 'w') as f:
            await f.write(json.dumps(ausencias_activas, indent=2))

        # Guardar fichajes activos (convertir datetime a string)
        fichajes_para_guardar = {}
        for user_id, fichaje in fichajes_activos.items():
            fichajes_para_guardar[user_id] = {
                'inicio': fichaje['inicio'].isoformat(),
                'guild_id': fichaje['guild_id']
            }
        async with aiofiles.open('fichajes_activos.json', 'w') as f:
            await f.write(json.dumps(fichajes_para_guardar, indent=2))

        # Guardar histórico de fichajes
        async with aiofiles.open('historico_fichajes.json', 'w') as f:
            await f.write(json.dumps(historico_fichajes, indent=2))

        # Guardar horas totales
        async with aiofiles.open('horas_totales.json', 'w') as f:
            await f.write(json.dumps(horas_totales, indent=2))

        # Guardar períodos de fichaje
        async with aiofiles.open('periodos_fichaje.json', 'w') as f:
            await f.write(json.dumps(periodos_fichaje, indent=2))

        # Guardar roles administrativos
        async with aiofiles.open('roles_admin.json', 'w') as f:
            await f.write(json.dumps(roles_admin, indent=2))

    except Exception as e:
        print(f"Error guardando datos: {e}")


# Funciones auxiliares para sistema de fichaje
def calcular_horas_trabajadas(inicio, fin):
    """Calcula las horas trabajadas entre dos datetime con precisión de segundos"""
    delta = fin - inicio
    # Mantener precisión completa de segundos
    return delta.total_seconds() / 3600


def formatear_tiempo(horas):
    """Convierte horas decimales a formato HH:MM:SS"""
    horas_enteras = int(horas)
    minutos_decimales = (horas - horas_enteras) * 60
    minutos = int(minutos_decimales)
    segundos = int((minutos_decimales - minutos) * 60)
    return f"{horas_enteras:02d}:{minutos:02d}:{segundos:02d}"


def tiene_permisos_admin(member, guild_id):
    """Verifica si un miembro tiene permisos administrativos"""
    # Si es administrador del servidor, siempre tiene permisos
    if member.guild_permissions.administrator:
        return True

    # Verificar si tiene algún rol administrativo configurado
    guild_str = str(guild_id)
    if guild_str in roles_admin:
        user_role_ids = [role.id for role in member.roles]
        return any(role_id in user_role_ids
                   for role_id in roles_admin[guild_str])

    return False


async def enviar_log_fichaje(guild_id, mensaje):
    """Envía un mensaje de log al canal configurado"""
    if str(guild_id
           ) in servidor_config and 'canal_logs_fichaje' in servidor_config[
               str(guild_id)]:
        try:
            guild = bot.get_guild(guild_id)
            if guild:
                canal_id = servidor_config[str(guild_id)]['canal_logs_fichaje']
                canal = guild.get_channel(canal_id)
                if canal and isinstance(canal, discord.TextChannel):
                    embed = discord.Embed(title="📋 Log de Fichaje",
                                          description=mensaje,
                                          color=0x3498db,
                                          timestamp=datetime.now())
                    await canal.send(embed=embed)
        except Exception as e:
            print(f"Error enviando log de fichaje: {e}")


def inicializar_datos_servidor(guild_id):
    """Inicializa las estructuras de datos para un servidor"""
    guild_str = str(guild_id)
    if guild_str not in historico_fichajes:
        historico_fichajes[guild_str] = {}
    if guild_str not in horas_totales:
        horas_totales[guild_str] = {}
    if guild_str not in periodos_fichaje:
        periodos_fichaje[guild_str] = []


# Función para sincronizar comandos slash
async def sync_commands():
    try:
        synced = await bot.tree.sync()
        print(f"✅ {len(synced)} comandos slash sincronizados")
    except Exception as e:
        print(f"❌ Error sincronizando comandos: {e}")


@bot.event
async def on_ready():
    print(f'✅ {bot.user} está conectado y listo!')
    if bot.user:
        print(f'🤖 Bot ID: {bot.user.id}')
    print(f'📊 Conectado a {len(bot.guilds)} servidores')
    print(f'⏰ Iniciado el: {datetime.now().strftime("%d/%m/%Y %H:%M:%S")}')

    # Cargar datos almacenados
    await cargar_datos()
    print('💾 Datos de configuración y ausencias cargados')

    # Iniciar tarea de revisión de ausencias
    if not revisar_ausencias.is_running():
        revisar_ausencias.start()
        print('🔄 Tarea de revisión de ausencias iniciada')

    # Sincronizar comandos slash
    await sync_commands()

    # Cambiar el estado del bot
    await bot.change_presence(activity=discord.Activity(
        type=discord.ActivityType.watching,
        name="Policía Nacional - SpainCityRP"),
                              status=discord.Status.online)
    print('🟢 Bot configurado para funcionamiento 24/7')


@bot.event
async def on_message(message):
    # Evitar que el bot responda a sus propios mensajes
    if message.author == bot.user:
        return

    # Procesar comandos
    await bot.process_commands(message)


# Tarea periódica para revisar ausencias
@tasks.loop(minutes=30)
async def revisar_ausencias():
    """Revisa y remueve roles de ausencia expirados"""
    if not ausencias_activas:
        return

    ahora = datetime.now()
    ausencias_a_remover = []

    for user_id, ausencia_info in ausencias_activas.items():
        fecha_fin = datetime.strptime(ausencia_info['fecha_fin'], '%d/%m/%Y')

        # Si la fecha de ausencia ya pasó
        if ahora.date() > fecha_fin.date():
            try:
                guild = bot.get_guild(ausencia_info['guild_id'])
                if guild:
                    member = guild.get_member(int(user_id))
                    if member:
                        # Buscar el rol de "Ausente"
                        rol_ausente = discord.utils.get(guild.roles,
                                                        name="Ausente")
                        if rol_ausente and rol_ausente in member.roles:
                            await member.remove_roles(rol_ausente)
                            print(
                                f"✅ Rol de ausencia removido para {member.display_name}"
                            )

                ausencias_a_remover.append(user_id)
            except Exception as e:
                print(f"❌ Error removiendo ausencia para {user_id}: {e}")

    # Remover ausencias expiradas
    for user_id in ausencias_a_remover:
        del ausencias_activas[user_id]

    if ausencias_a_remover:
        await guardar_datos()


@revisar_ausencias.before_loop
async def before_revisar_ausencias():
    await bot.wait_until_ready()


# Comandos Slash - funcionan sin permisos especiales
@bot.tree.command(name="ping", description="Muestra la latencia del bot")
async def ping(interaction: discord.Interaction):
    latencia = round(bot.latency * 1000)
    embed = discord.Embed(title="🏓 Pong!",
                          description=f"Latencia: {latencia}ms",
                          color=0x00ff00)
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="servidor", description="Información del servidor")
async def info_servidor(interaction: discord.Interaction):
    guild = interaction.guild
    if not guild:
        return

    embed = discord.Embed(title=f"📊 Información de {guild.name}",
                          color=0x0099ff)
    embed.add_field(name="👥 Miembros", value=guild.member_count, inline=True)
    embed.add_field(name="📅 Creado",
                    value=guild.created_at.strftime("%d/%m/%Y"),
                    inline=True)
    embed.add_field(
        name="👑 Propietario",
        value=guild.owner.mention if guild.owner else "Desconocido",
        inline=True)
    embed.add_field(name="💬 Canales", value=len(guild.channels), inline=True)
    embed.add_field(name="🎭 Roles", value=len(guild.roles), inline=True)

    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)

    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="usuario", description="Información de un usuario")
async def info_usuario(interaction: discord.Interaction,
                       miembro: discord.Member = None):
    if miembro is None:
        if isinstance(interaction.user, discord.Member):
            miembro = interaction.user
        else:
            await interaction.response.send_message(
                "❌ Error obteniendo información del usuario", ephemeral=True)
            return

    embed = discord.Embed(title=f"👤 Información de {miembro.display_name}",
                          color=0xff9900)
    embed.add_field(name="🏷️ Usuario",
                    value=f"{miembro.name}#{miembro.discriminator}"
                    if miembro.discriminator else miembro.name,
                    inline=True)
    embed.add_field(name="🆔 ID", value=miembro.id, inline=True)
    embed.add_field(name="📅 Se unió",
                    value=miembro.joined_at.strftime("%d/%m/%Y")
                    if miembro.joined_at else "No disponible",
                    inline=True)
    embed.add_field(name="📝 Cuenta creada",
                    value=miembro.created_at.strftime("%d/%m/%Y"),
                    inline=True)
    embed.add_field(name="🎭 Roles", value=len(miembro.roles) - 1, inline=True)
    embed.add_field(name="📱 Estado",
                    value=str(miembro.status).title(),
                    inline=True)

    if miembro.avatar:
        embed.set_thumbnail(url=miembro.avatar.url)

    await interaction.response.send_message(embed=embed)


@bot.command(name='limpiar')
@commands.has_permissions(manage_messages=True)
async def limpiar(ctx, cantidad: int = 5):
    """Elimina mensajes del canal (solo moderadores)"""
    if cantidad < 1 or cantidad > 100:
        await ctx.send("❌ La cantidad debe estar entre 1 y 100")
        return

    deleted = await ctx.channel.purge(limit=cantidad + 1)

    embed = discord.Embed(
        title="🧹 Mensajes eliminados",
        description=f"Se eliminaron {len(deleted)-1} mensajes",
        color=0xff0000)

    msg = await ctx.send(embed=embed)
    await asyncio.sleep(3)
    await msg.delete()


@bot.tree.command(name="ayuda",
                  description="Muestra todos los comandos disponibles")
async def ayuda(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🤖 Comandos del Bot",
        description="Aquí tienes todos los comandos disponibles:",
        color=0x9932cc)

    embed.add_field(
        name="🔧 Comandos Básicos",
        value=
        "`/ping` - Muestra la latencia\n`/servidor` - Info del servidor\n`/usuario [@usuario]` - Info de usuario",
        inline=False)

    embed.add_field(
        name="🏃‍♂️ Comandos de Ausencias",
        value=
        "`/setausencia` - Configurar canal de ausencias (Admin)\n`/ausencia` - Marcar usuario ausente (Moderador)\n`/quitarausencia` - Quitar ausencia antes de tiempo (Moderador)\n`/ausentes` - Ver lista de ausentes actuales",
        inline=False)

    embed.add_field(
        name="📋 Comandos de Dimisión",
        value=
        "`/setdimension` - Configurar canal de dimisiones (Admin)\n`/dimision @usuario` - Marca dimisión de usuario (Moderador)",
        inline=False)

    embed.add_field(
        name="⏰ Sistema de Fichaje de Horas",
        value=
        "`/fichar` - Iniciar fichaje\n`/cerrarfichaje` - Cerrar fichaje y recibir resumen\n`/verfichajes [período]` - Ver horas totales de todos\n`/gestionar` - Gestionar fichajes (Admin)\n`/finfichaje` - Finalizar período y resetear (Admin)\n`/logfichaje` - Configurar canal de logs (Admin)",
        inline=False)

    embed.add_field(name="ℹ️ Información",
                    value="`/ayuda` - Muestra este mensaje",
                    inline=False)

    embed.add_field(
        name="💡 Tip",
        value=
        "Usa `/` seguido del nombre del comando o selecciónalo del menú que aparece",
        inline=False)

    embed.set_footer(text="Bot de Discord 24/7 | Siempre activo para ti")

    await interaction.response.send_message(embed=embed)


# Nuevos comandos para sistema de ausencias
@bot.tree.command(name="setausencia",
                  description="Configura el canal para mensajes de ausencia")
@discord.app_commands.describe(
    canal="Canal donde se enviarán los mensajes de ausencia")
async def set_ausencia(interaction: discord.Interaction,
                       canal: discord.TextChannel):
    # Verificar permisos de administrador
    if not isinstance(interaction.user,
                      discord.Member) or not tiene_permisos_admin(
                          interaction.user, interaction.guild.id):
        embed = discord.Embed(
            title="❌ Sin permisos",
            description=
            "Solo los administradores pueden configurar el canal de ausencias",
            color=0xff0000)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    # Guardar configuración
    if not interaction.guild:
        return
    guild_id = str(interaction.guild.id)
    if guild_id not in servidor_config:
        servidor_config[guild_id] = {}

    servidor_config[guild_id]['canal_ausencias'] = canal.id
    await guardar_datos()

    embed = discord.Embed(
        title="✅ Canal configurado",
        description=f"Los mensajes de ausencia se enviarán a {canal.mention}",
        color=0x00ff00)
    await interaction.response.send_message(embed=embed)


@bot.tree.command(
    name="ausencia",
    description="Marca a un usuario como ausente hasta una fecha específica")
@discord.app_commands.describe(usuario="Usuario que estará ausente",
                               fecha="Fecha de regreso en formato DD/MM/YYYY")
async def ausencia(interaction: discord.Interaction, usuario: discord.Member,
                   fecha: str):
    # Verificar permisos administrativos
    if not isinstance(interaction.user,
                      discord.Member) or not tiene_permisos_admin(
                          interaction.user, interaction.guild.id):
        embed = discord.Embed(
            title="❌ Sin permisos",
            description="Solo los administradores pueden marcar ausencias",
            color=0xff0000)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    # Verificar que hay un canal configurado
    if not interaction.guild:
        return
    guild_id = str(interaction.guild.id)
    if guild_id not in servidor_config or 'canal_ausencias' not in servidor_config[
            guild_id]:
        embed = discord.Embed(
            title="❌ Canal no configurado",
            description="Primero configura un canal con `/setausencia`",
            color=0xff0000)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    # Validar formato de fecha
    try:
        fecha_obj = datetime.strptime(fecha, '%d/%m/%Y')
        if fecha_obj.date() <= datetime.now().date():
            embed = discord.Embed(
                title="❌ Fecha inválida",
                description="La fecha debe ser futura (formato: DD/MM/YYYY)",
                color=0xff0000)
            await interaction.response.send_message(embed=embed,
                                                    ephemeral=True)
            return
    except ValueError:
        embed = discord.Embed(
            title="❌ Formato de fecha incorrecto",
            description="Usa el formato DD/MM/YYYY (ejemplo: 25/12/2024)",
            color=0xff0000)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    # Buscar o crear el rol "Ausente"
    if not interaction.guild:
        return
    rol_ausente = discord.utils.get(interaction.guild.roles, name="Ausente")
    if not rol_ausente:
        try:
            rol_ausente = await interaction.guild.create_role(
                name="Ausente",
                color=discord.Color.orange(),
                reason="Rol creado automáticamente para ausencias")
        except Exception as e:
            embed = discord.Embed(
                title="❌ Error creando rol",
                description=
                "No pude crear el rol 'Ausente'. Verifica mis permisos.",
                color=0xff0000)
            await interaction.response.send_message(embed=embed,
                                                    ephemeral=True)
            return

    # Añadir rol al usuario
    try:
        await usuario.add_roles(rol_ausente)
    except Exception as e:
        embed = discord.Embed(
            title="❌ Error asignando rol",
            description=
            "No pude asignar el rol al usuario. Verifica mis permisos.",
            color=0xff0000)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    # Guardar ausencia en el sistema
    if not interaction.guild:
        return
    ausencias_activas[str(usuario.id)] = {
        'fecha_fin': fecha,
        'guild_id': interaction.guild.id,
        'asignado_por': interaction.user.id,
        'fecha_asignacion': datetime.now().strftime('%d/%m/%Y %H:%M')
    }
    await guardar_datos()

    # Enviar mensaje al canal configurado
    canal_id = servidor_config[guild_id]['canal_ausencias']
    canal = interaction.guild.get_channel(canal_id)

    if canal and isinstance(canal, discord.TextChannel):
        embed_ausencia = discord.Embed(
            title="🏃‍♂️ Ausencia Justificada",
            description=
            f"{usuario.mention} Ausencia justificada (Hasta el {fecha})",
            color=0xffa500,
            timestamp=datetime.now())
        embed_ausencia.set_footer(
            text=f"Asignado por {interaction.user.display_name}")
        await canal.send(embed=embed_ausencia)

    # Responder al comando
    embed = discord.Embed(
        title="✅ Ausencia registrada",
        description=
        f"Se ha marcado a {usuario.mention} como ausente hasta el {fecha}",
        color=0x00ff00)
    await interaction.response.send_message(embed=embed)


@bot.tree.command(
    name="quitarausencia",
    description="Quita la ausencia de un usuario antes de tiempo")
@discord.app_commands.describe(usuario="Usuario al que quitar la ausencia")
async def quitar_ausencia(interaction: discord.Interaction,
                          usuario: discord.Member):
    # Verificar permisos administrativos
    if not isinstance(interaction.user,
                      discord.Member) or not tiene_permisos_admin(
                          interaction.user, interaction.guild.id):
        embed = discord.Embed(
            title="❌ Sin permisos",
            description="Solo los administradores pueden quitar ausencias",
            color=0xff0000)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    # Verificar si el usuario tiene ausencia activa
    user_id = str(usuario.id)
    if user_id not in ausencias_activas:
        embed = discord.Embed(
            title="❌ Sin ausencia",
            description=f"{usuario.mention} no tiene una ausencia activa",
            color=0xff0000)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    # Buscar el rol "Ausente"
    if not interaction.guild:
        return
    rol_ausente = discord.utils.get(interaction.guild.roles, name="Ausente")
    if rol_ausente and rol_ausente in usuario.roles:
        try:
            await usuario.remove_roles(rol_ausente)
        except Exception as e:
            embed = discord.Embed(
                title="❌ Error removiendo rol",
                description=
                "No pude quitar el rol al usuario. Verifica mis permisos.",
                color=0xff0000)
            await interaction.response.send_message(embed=embed,
                                                    ephemeral=True)
            return

    # Remover la ausencia del sistema
    fecha_original = ausencias_activas[user_id]['fecha_fin']
    del ausencias_activas[user_id]
    await guardar_datos()

    # Enviar confirmación
    embed = discord.Embed(
        title="✅ Ausencia removida",
        description=
        f"Se ha quitado la ausencia de {usuario.mention} (originalmente hasta el {fecha_original})",
        color=0x00ff00)
    await interaction.response.send_message(embed=embed)


@bot.tree.command(
    name="ausentes",
    description="Muestra la lista de todos los usuarios ausentes")
async def lista_ausentes(interaction: discord.Interaction):
    # Verificar si hay ausencias activas
    if not ausencias_activas:
        embed = discord.Embed(
            title="📋 Lista de Ausentes",
            description="No hay usuarios ausentes en este momento",
            color=0x9932cc)
        await interaction.response.send_message(embed=embed)
        return

    # Filtrar ausencias de este servidor
    if not interaction.guild:
        return
    ausencias_servidor = {}
    for user_id, ausencia_info in ausencias_activas.items():
        if ausencia_info['guild_id'] == interaction.guild.id:
            ausencias_servidor[user_id] = ausencia_info

    if not ausencias_servidor:
        embed = discord.Embed(
            title="📋 Lista de Ausentes",
            description="No hay usuarios ausentes en este servidor",
            color=0x9932cc)
        await interaction.response.send_message(embed=embed)
        return

    # Crear mensaje simple con todos los ausentes
    mensaje_ausentes = "📋 **Lista de Ausentes:**\n\n"
    usuarios_mostrados = 0

    for user_id, ausencia_info in ausencias_servidor.items():
        try:
            # Intentar obtener el miembro del servidor
            if not interaction.guild:
                continue
            member = interaction.guild.get_member(int(user_id))

            # Si no está en el servidor, intentar obtener el usuario de Discord
            if not member:
                try:
                    user = await bot.fetch_user(int(user_id))
                    usuario_nombre = user.mention
                except:
                    usuario_nombre = f"Usuario {user_id}"
            else:
                usuario_nombre = member.mention

            fecha_fin = ausencia_info['fecha_fin']
            fecha_inicio = ausencia_info['fecha_asignacion'].split(' ')[
                0]  # Solo la fecha, sin hora

            # Calcular días restantes
            fecha_obj = datetime.strptime(fecha_fin, '%d/%m/%Y')
            dias_restantes = (fecha_obj.date() - datetime.now().date()).days

            if dias_restantes > 0:
                dias_text = f"({dias_restantes} días restantes)"
            elif dias_restantes == 0:
                dias_text = "(termina hoy)"
            else:
                dias_text = "(expirada)"

            mensaje_ausentes += f"{usuario_nombre} ausente desde {fecha_inicio} hasta {fecha_fin} {dias_text}\n"
            usuarios_mostrados += 1

        except Exception as e:
            # Si hay cualquier error, mostrar al menos el ID
            try:
                fecha_fin = ausencia_info['fecha_fin']
                fecha_inicio = ausencia_info['fecha_asignacion'].split(' ')[0]
                mensaje_ausentes += f"Usuario {user_id} ausente desde {fecha_inicio} hasta {fecha_fin}\n"
                usuarios_mostrados += 1
            except:
                continue

    if usuarios_mostrados == 0:
        mensaje_ausentes += "No hay usuarios ausentes en este momento."
    else:
        mensaje_ausentes += f"\n**Total: {usuarios_mostrados} usuario(s) ausente(s)**"

    await interaction.response.send_message(mensaje_ausentes)


@bot.tree.command(name="setdimension",
                  description="Configura el canal para mensajes de dimisión")
@discord.app_commands.describe(
    canal="Canal donde se enviarán los mensajes de dimisión")
async def set_dimision(interaction: discord.Interaction,
                       canal: discord.TextChannel):
    # Verificar permisos de administrador
    if not isinstance(interaction.user,
                      discord.Member) or not tiene_permisos_admin(
                          interaction.user, interaction.guild.id):
        embed = discord.Embed(
            title="❌ Sin permisos",
            description=
            "Solo los administradores pueden configurar el canal de dimisiones",
            color=0xff0000)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    # Guardar configuración
    if not interaction.guild:
        return
    guild_id = str(interaction.guild.id)
    if guild_id not in servidor_config:
        servidor_config[guild_id] = {}

    servidor_config[guild_id]['canal_dimisiones'] = canal.id
    await guardar_datos()

    embed = discord.Embed(
        title="✅ Canal configurado",
        description=f"Los mensajes de dimisión se enviarán a {canal.mention}",
        color=0x00ff00)
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="dimision",
                  description="Marca a un usuario como dimitido")
@discord.app_commands.describe(usuario="Usuario que ha dimitido")
async def dimision(interaction: discord.Interaction, usuario: discord.Member):
    # Verificar permisos de moderador
    if not isinstance(
            interaction.user, discord.Member
    ) or not interaction.user.guild_permissions.manage_messages:
        embed = discord.Embed(
            title="❌ Sin permisos",
            description="Solo los moderadores pueden marcar dimisiones",
            color=0xff0000)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    # Verificar que hay un canal configurado
    if not interaction.guild:
        return
    guild_id = str(interaction.guild.id)
    if guild_id not in servidor_config or 'canal_dimisiones' not in servidor_config[
            guild_id]:
        embed = discord.Embed(
            title="❌ Canal no configurado",
            description="Primero configura un canal con `/setdimension`",
            color=0xff0000)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    # Crear el mensaje de dimisión usando el nick del servidor
    usuario_nick = usuario.display_name

    # Enviar mensaje al canal configurado
    canal_id = servidor_config[guild_id]['canal_dimisiones']
    canal = interaction.guild.get_channel(canal_id)

    if canal and isinstance(canal, discord.TextChannel):
        embed_dimision = discord.Embed(
            title="📋 Dimisión",
            description=f"{usuario_nick} ha dimitido",
            color=0xff6600,
            timestamp=datetime.now())
        embed_dimision.set_footer(
            text=f"Marcado por {interaction.user.display_name}")
        await canal.send(embed=embed_dimision)

    # Responder al comando
    embed = discord.Embed(
        title="✅ Dimisión registrada",
        description=f"Se ha registrado la dimisión de {usuario_nick}",
        color=0x00ff00)
    await interaction.response.send_message(embed=embed)


# Comandos del Sistema de Fichaje de Horas
@bot.tree.command(name="logfichaje",
                  description="Configura el canal para logs de fichaje")
@discord.app_commands.describe(
    canal="Canal donde se enviarán los logs de fichaje")
async def log_fichaje(interaction: discord.Interaction,
                      canal: discord.TextChannel):
    # Verificar permisos de administrador
    if not isinstance(interaction.user,
                      discord.Member) or not tiene_permisos_admin(
                          interaction.user, interaction.guild.id):
        embed = discord.Embed(
            title="❌ Sin permisos",
            description=
            "Solo los administradores pueden configurar el canal de logs de fichaje",
            color=0xff0000)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    # Guardar configuración
    if not interaction.guild:
        return
    guild_id = str(interaction.guild.id)
    if guild_id not in servidor_config:
        servidor_config[guild_id] = {}

    servidor_config[guild_id]['canal_logs_fichaje'] = canal.id
    await guardar_datos()

    embed = discord.Embed(
        title="✅ Canal configurado",
        description=f"Los logs de fichaje se enviarán a {canal.mention}",
        color=0x00ff00)
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="fichar", description="Inicia tu fichaje de horas")
async def fichar(interaction: discord.Interaction):
    if not isinstance(interaction.user,
                      discord.Member) or not interaction.guild:
        return

    user_id = str(interaction.user.id)
    guild_id = interaction.guild.id

    # Verificar si ya tiene un fichaje activo
    if user_id in fichajes_activos:
        embed = discord.Embed(
            title="⏰ Fichaje activo",
            description=
            "Ya tienes un fichaje iniciado. Usa `/cerrarfichaje` primero.",
            color=0xff9900)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    # Inicializar datos del servidor
    inicializar_datos_servidor(guild_id)

    # Iniciar fichaje
    ahora = datetime.now()
    fichajes_activos[user_id] = {'inicio': ahora, 'guild_id': guild_id}
    await guardar_datos()

    # Enviar log
    await enviar_log_fichaje(
        guild_id,
        f"🟢 **{interaction.user.display_name}** ha iniciado fichaje a las {ahora.strftime('%H:%M:%S')}"
    )

    embed = discord.Embed(
        title="⏰ Fichaje iniciado",
        description=
        f"Has comenzado a fichar a las **{ahora.strftime('%H:%M:%S')}**",
        color=0x00ff00,
        timestamp=ahora)
    embed.set_footer(text="Usa /cerrarfichaje cuando termines")
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="cerrarfichaje",
                  description="Cierra tu fichaje y recibe un resumen por MD")
async def cerrar_fichaje(interaction: discord.Interaction):
    if not isinstance(interaction.user,
                      discord.Member) or not interaction.guild:
        return

    user_id = str(interaction.user.id)
    guild_id = interaction.guild.id
    guild_str = str(guild_id)

    # Verificar si tiene un fichaje activo
    if user_id not in fichajes_activos:
        embed = discord.Embed(
            title="❌ Sin fichaje activo",
            description=
            "No tienes ningún fichaje iniciado. Usa `/fichar` primero.",
            color=0xff0000)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    # Calcular horas trabajadas
    inicio = fichajes_activos[user_id]['inicio']
    fin = datetime.now()
    horas_trabajadas = calcular_horas_trabajadas(inicio, fin)

    # Actualizar historial
    inicializar_datos_servidor(guild_id)
    if user_id not in historico_fichajes[guild_str]:
        historico_fichajes[guild_str][user_id] = []

    # Agregar registro al historial
    registro = {
        'inicio': inicio.strftime('%H:%M:%S'),
        'fin': fin.strftime('%H:%M:%S'),
        'horas': horas_trabajadas,
        'fecha': fin.strftime('%d/%m/%Y')
    }
    historico_fichajes[guild_str][user_id].append(registro)

    # Actualizar horas totales
    if user_id not in horas_totales[guild_str]:
        horas_totales[guild_str][user_id] = 0
    horas_totales[guild_str][user_id] += horas_trabajadas

    # Remover fichaje activo
    del fichajes_activos[user_id]
    await guardar_datos()

    # Enviar log
    await enviar_log_fichaje(
        guild_id,
        f"🔴 **{interaction.user.display_name}** ha cerrado fichaje. Horas trabajadas: **{formatear_tiempo(horas_trabajadas)}**"
    )

    # Enviar MD al usuario
    try:
        embed_md = discord.Embed(title="📊 Resumen de Fichaje", color=0x3498db)
        embed_md.add_field(name="⏰ Inicio",
                           value=inicio.strftime('%H:%M:%S'),
                           inline=True)
        embed_md.add_field(name="🏁 Fin",
                           value=fin.strftime('%H:%M:%S'),
                           inline=True)
        embed_md.add_field(name="⏱️ Horas trabajadas",
                           value=formatear_tiempo(horas_trabajadas),
                           inline=True)
        embed_md.add_field(name="🏆 Total acumulado",
                           value=formatear_tiempo(
                               horas_totales[guild_str][user_id]),
                           inline=False)
        embed_md.set_footer(text=f"Servidor: {interaction.guild.name}")

        await interaction.user.send(embed=embed_md)

        # Responder al comando
        embed = discord.Embed(
            title="✅ Fichaje cerrado",
            description=
            f"Has fichado **{formatear_tiempo(horas_trabajadas)}** horas. Te he enviado un resumen por MD.",
            color=0x00ff00)
        await interaction.response.send_message(embed=embed)

    except discord.Forbidden:
        # Si no puede enviar MD, mostrar la info en el canal
        embed = discord.Embed(
            title="✅ Fichaje cerrado",
            description=
            f"Has fichado **{formatear_tiempo(horas_trabajadas)}** horas.\nTotal acumulado: **{formatear_tiempo(horas_totales[guild_str][user_id])}**",
            color=0x00ff00)
        embed.set_footer(
            text="No pude enviarte MD. Revisa tu configuración de privacidad.")
        await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="verfichajes",
                  description="Ver horas totales de todos los usuarios")
@discord.app_commands.describe(
    periodo="Número del período histórico (1=actual, 2=anterior, etc.)")
async def ver_fichajes(interaction: discord.Interaction, periodo: int = 1):
    if not interaction.guild:
        return

    guild_str = str(interaction.guild.id)
    inicializar_datos_servidor(interaction.guild.id)

    if periodo < 1:
        embed = discord.Embed(
            title="❌ Período inválido",
            description=
            "El período debe ser 1 o mayor (1=actual, 2=anterior, etc.)",
            color=0xff0000)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    # Verificar si hay datos para el período solicitado
    if len(periodos_fichaje[guild_str]) < periodo:
        embed = discord.Embed(
            title="📊 Sin datos históricos",
            description=
            f"No hay datos para el período {periodo}. Solo hay {len(periodos_fichaje[guild_str]) + 1} período(s) disponible(s).",
            color=0xff9900)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    # Si es período 1 (actual), usar datos actuales
    if periodo == 1:
        datos_periodo = horas_totales[
            guild_str] if guild_str in horas_totales else {}
        titulo_periodo = "📊 Fichajes Actuales"
    else:
        # Verificar que existan suficientes períodos históricos
        periodos_disponibles = len(periodos_fichaje[guild_str])
        if periodos_disponibles < (periodo - 1):
            embed = discord.Embed(
                title="❌ Período no encontrado",
                description=
                f"Solo hay {periodos_disponibles + 1} período(s) disponible(s)",
                color=0xff0000)
            await interaction.response.send_message(embed=embed,
                                                    ephemeral=True)
            return

        # Usar datos históricos - acceder desde el final hacia atrás
        indice = -(periodo - 1)  # periodo 2 = -1, periodo 3 = -2, etc.
        datos_periodo = periodos_fichaje[guild_str][indice]['datos']
        titulo_periodo = f"📊 Fichajes - Período {periodo}"

    if not datos_periodo:
        await interaction.response.send_message(
            f"📊 {titulo_periodo}\nNo hay fichajes registrados en este período")
        return

    # Crear mensaje simple con menciones
    mensaje = f"📊 {titulo_periodo}\n\n"
    usuarios_mostrados = 0

    # Ordenar por horas (de mayor a menor)
    usuarios_ordenados = sorted(datos_periodo.items(),
                                key=lambda x: x[1],
                                reverse=True)

    for user_id, total_horas in usuarios_ordenados:
        try:
            user_id_int = int(user_id)

            # Intentar obtener el miembro del servidor
            member = interaction.guild.get_member(user_id_int)

            if member:
                # Usar mención del usuario
                usuario_mencion = member.mention
            else:
                # Si no está en el servidor, usar mención básica
                usuario_mencion = f"<@{user_id_int}>"

            mensaje += f"{usuario_mencion} {formatear_tiempo(total_horas)} horas\n"
            usuarios_mostrados += 1

        except Exception:
            # Si hay error, mostrar al menos el ID
            mensaje += f"Usuario {user_id} {formatear_tiempo(total_horas)} horas\n"
            usuarios_mostrados += 1

    if usuarios_mostrados == 0:
        mensaje += "No hay fichajes registrados en este momento."
    else:
        mensaje += f"\n👥 {usuarios_mostrados} usuario(s) con fichajes registrados"

        if periodo == 1 and len(periodos_fichaje[guild_str]) > 0:
            mensaje += "\n💡 Usa `/verfichajes 2` para ver el período anterior"

    await interaction.response.send_message(mensaje)


@bot.tree.command(
    name="fichando",
    description="Ver usuarios que tienen un fichaje abierto actualmente")
async def fichando(interaction: discord.Interaction):
    if not interaction.guild:
        return

    guild_id = interaction.guild.id
    inicializar_datos_servidor(guild_id)

    # Filtrar fichajes activos del servidor actual
    usuarios_fichando = {}
    for user_id, data in fichajes_activos.items():
        if data['guild_id'] == guild_id:
            usuarios_fichando[user_id] = data

    if not usuarios_fichando:
        await interaction.response.send_message(
            "⏰ **Usuarios Fichando**\nNo hay usuarios con fichajes abiertos en este momento"
        )
        return

    # Crear mensaje simple
    mensaje = "⏰ **Usuarios Fichando**\n\n"
    ahora = datetime.now()
    usuarios_mostrados = 0

    for user_id, data in usuarios_fichando.items():
        try:
            user_id_int = int(user_id)
            member = interaction.guild.get_member(user_id_int)

            if member:
                # Usar mención del usuario
                usuario_mencion = member.mention
            else:
                # Si no está en el servidor, usar mención básica
                usuario_mencion = f"<@{user_id_int}>"

            # Calcular tiempo transcurrido
            tiempo_transcurrido = ahora - data['inicio']
            horas_transcurridas = tiempo_transcurrido.total_seconds() / 3600

            mensaje += f"{usuario_mencion} {formatear_tiempo(horas_transcurridas)} fichado\n"
            usuarios_mostrados += 1

        except Exception:
            continue

    mensaje += f"\n👥 **{usuarios_mostrados} usuario(s) con fichajes abiertos**"
    await interaction.response.send_message(mensaje)


@bot.tree.command(name="config",
                  description="Configurar roles administrativos del servidor")
@discord.app_commands.describe(
    accion="Acción a realizar",
    rol="Rol a agregar o quitar de los permisos administrativos")
@discord.app_commands.choices(accion=[
    discord.app_commands.Choice(name="Agregar rol administrativo",
                                value="agregar"),
    discord.app_commands.Choice(name="Quitar rol administrativo",
                                value="quitar"),
    discord.app_commands.Choice(name="Ver roles configurados", value="ver")
])
async def config_roles(interaction: discord.Interaction,
                       accion: str,
                       rol: discord.Role = None):
    # Solo los administradores del servidor pueden configurar roles
    if not isinstance(
            interaction.user, discord.Member
    ) or not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message(
            "❌ Solo los administradores del servidor pueden configurar roles administrativos.",
            ephemeral=True)
        return

    if not interaction.guild:
        return

    guild_id = interaction.guild.id
    guild_str = str(guild_id)

    # Inicializar roles admin para el servidor si no existe
    if guild_str not in roles_admin:
        roles_admin[guild_str] = []

    if accion == "ver":
        if not roles_admin[guild_str]:
            await interaction.response.send_message(
                "⚙️ **Configuración de Roles Administrativos**\n\nNo hay roles administrativos configurados.\n\n💡 Los administradores del servidor siempre tienen permisos."
            )
            return

        mensaje = "⚙️ **Configuración de Roles Administrativos**\n\n"
        for role_id in roles_admin[guild_str]:
            role = interaction.guild.get_role(role_id)
            if role:
                mensaje += f"• {role.mention}\n"
            else:
                # Rol eliminado del servidor
                roles_admin[guild_str].remove(role_id)

        mensaje += "\n💡 Los administradores del servidor siempre tienen permisos."
        await interaction.response.send_message(mensaje)
        await guardar_datos()
        return

    if rol is None:
        await interaction.response.send_message(
            "❌ Debes especificar un rol para agregar o quitar.",
            ephemeral=True)
        return

    if accion == "agregar":
        if rol.id in roles_admin[guild_str]:
            await interaction.response.send_message(
                f"❌ El rol {rol.mention} ya tiene permisos administrativos.",
                ephemeral=True)
            return

        roles_admin[guild_str].append(rol.id)
        await guardar_datos()
        await interaction.response.send_message(
            f"✅ El rol {rol.mention} ahora puede usar comandos administrativos."
        )

    elif accion == "quitar":
        if rol.id not in roles_admin[guild_str]:
            await interaction.response.send_message(
                f"❌ El rol {rol.mention} no tiene permisos administrativos.",
                ephemeral=True)
            return

        roles_admin[guild_str].remove(rol.id)
        await guardar_datos()
        await interaction.response.send_message(
            f"✅ El rol {rol.mention} ya no puede usar comandos administrativos."
        )


@bot.tree.command(
    name="gestionar",
    description="Gestionar fichajes de usuarios (solo administradores)")
@discord.app_commands.describe(
    accion="Acción a realizar",
    usuario="Usuario a gestionar",
    horas="Horas a añadir/quitar (formato: 2.5 o 2:30)",
    minutos="Minutos adicionales (opcional)")
@discord.app_commands.choices(accion=[
    discord.app_commands.Choice(name="Añadir horas", value="añadir"),
    discord.app_commands.Choice(name="Quitar horas", value="quitar"),
    discord.app_commands.Choice(name="Cerrar fichaje", value="cerrar")
])
async def gestionar_fichaje(interaction: discord.Interaction,
                            accion: str,
                            usuario: discord.Member,
                            horas: str = "0",
                            minutos: int = 0):
    # Verificar permisos de administrador
    if not isinstance(interaction.user,
                      discord.Member) or not tiene_permisos_admin(
                          interaction.user, interaction.guild.id):
        embed = discord.Embed(
            title="❌ Sin permisos",
            description="Solo los administradores pueden gestionar fichajes",
            color=0xff0000)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    if not interaction.guild:
        return

    guild_id = interaction.guild.id
    guild_str = str(guild_id)
    user_id = str(usuario.id)
    inicializar_datos_servidor(guild_id)

    if accion == "cerrar":
        # Cerrar fichaje de usuario
        if user_id not in fichajes_activos:
            embed = discord.Embed(
                title="❌ Sin fichaje activo",
                description=
                f"{usuario.display_name} no tiene un fichaje activo",
                color=0xff0000)
            await interaction.response.send_message(embed=embed,
                                                    ephemeral=True)
            return

        # Calcular horas y cerrar
        inicio = fichajes_activos[user_id]['inicio']
        fin = datetime.now()
        horas_trabajadas = calcular_horas_trabajadas(inicio, fin)

        # Actualizar totales e historial (igual que en cerrarfichaje)
        if user_id not in historico_fichajes[guild_str]:
            historico_fichajes[guild_str][user_id] = []

        registro = {
            'inicio': inicio.strftime('%H:%M:%S'),
            'fin': fin.strftime('%H:%M:%S'),
            'horas': horas_trabajadas,
            'fecha': fin.strftime('%d/%m/%Y')
        }
        historico_fichajes[guild_str][user_id].append(registro)

        if user_id not in horas_totales[guild_str]:
            horas_totales[guild_str][user_id] = 0
        horas_totales[guild_str][user_id] += horas_trabajadas

        del fichajes_activos[user_id]
        await guardar_datos()

        # Logs
        await enviar_log_fichaje(
            guild_id,
            f"🔴 **{interaction.user.display_name}** cerró el fichaje de **{usuario.display_name}**. Horas: **{formatear_tiempo(horas_trabajadas)}**"
        )

        embed = discord.Embed(
            title="✅ Fichaje cerrado por administrador",
            description=
            f"Se cerró el fichaje de {usuario.display_name}.\nHoras trabajadas: **{formatear_tiempo(horas_trabajadas)}**",
            color=0x00ff00)
        await interaction.response.send_message(embed=embed)

    else:  # añadir o quitar horas
        try:
            # Parsear horas (puede ser "2.5" o "2:30")
            if ":" in horas:
                partes = horas.split(":")
                horas_decimal = float(partes[0]) + float(partes[1]) / 60
            else:
                horas_decimal = float(horas)

            # Añadir minutos extra
            horas_decimal += minutos / 60

            if horas_decimal <= 0:
                embed = discord.Embed(
                    title="❌ Valor inválido",
                    description="Las horas deben ser mayor a 0",
                    color=0xff0000)
                await interaction.response.send_message(embed=embed,
                                                        ephemeral=True)
                return

        except ValueError:
            embed = discord.Embed(
                title="❌ Formato inválido",
                description="Usa formato de horas válido: `2.5` o `2:30`",
                color=0xff0000)
            await interaction.response.send_message(embed=embed,
                                                    ephemeral=True)
            return

        # Inicializar usuario si no existe
        if user_id not in horas_totales[guild_str]:
            horas_totales[guild_str][user_id] = 0

        if accion == "añadir":
            horas_totales[guild_str][user_id] += horas_decimal
            accion_texto = "añadido"
            emoji = "➕"
        else:  # quitar
            horas_totales[guild_str][user_id] -= horas_decimal
            # No permitir horas negativas
            if horas_totales[guild_str][user_id] < 0:
                horas_totales[guild_str][user_id] = 0
            accion_texto = "quitado"
            emoji = "➖"

        await guardar_datos()

        # Logs
        await enviar_log_fichaje(
            guild_id,
            f"{emoji} **{interaction.user.display_name}** ha {accion_texto} **{formatear_tiempo(horas_decimal)}** horas a **{usuario.display_name}**"
        )

        embed = discord.Embed(
            title=f"✅ Horas {accion_texto}",
            description=
            f"Se han {accion_texto} **{formatear_tiempo(horas_decimal)}** horas a {usuario.display_name}.\nTotal actual: **{formatear_tiempo(horas_totales[guild_str][user_id])}**",
            color=0x00ff00)
        await interaction.response.send_message(embed=embed)


@bot.tree.command(
    name="finfichaje",
    description="Finaliza el período actual y resetea todos los fichajes")
async def fin_fichaje(interaction: discord.Interaction):
    # Verificar permisos de administrador
    if not isinstance(interaction.user,
                      discord.Member) or not tiene_permisos_admin(
                          interaction.user, interaction.guild.id):
        embed = discord.Embed(
            title="❌ Sin permisos",
            description=
            "Solo los administradores pueden finalizar períodos de fichaje",
            color=0xff0000)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    if not interaction.guild:
        return

    guild_id = interaction.guild.id
    guild_str = str(guild_id)
    inicializar_datos_servidor(guild_id)

    # Confirmar acción
    embed_confirm = discord.Embed(
        title="⚠️ Confirmar finalización de período",
        description=
        "Esta acción:\n• Cerrará todos los fichajes activos\n• Guardará el período actual en el historial\n• Resetrará todas las horas a 0\n\n¿Estás seguro?",
        color=0xff9900)

    # Crear botones de confirmación (simplified approach - usar respuesta directa)
    view = discord.ui.View()

    async def confirmar_callback(confirm_interaction):
        if confirm_interaction.user != interaction.user:
            await confirm_interaction.response.send_message(
                "❌ Solo quien ejecutó el comando puede confirmar.",
                ephemeral=True)
            return

        fichajes_cerrados = 0
        total_usuarios = len(
            horas_totales[guild_str]) if guild_str in horas_totales else 0

        # Cerrar todos los fichajes activos
        fichajes_a_cerrar = list(fichajes_activos.items())
        for user_id, fichaje in fichajes_a_cerrar:
            if fichaje['guild_id'] == guild_id:
                try:
                    # Calcular horas y agregar al historial
                    inicio = fichaje['inicio']
                    fin = datetime.now()
                    horas_trabajadas = calcular_horas_trabajadas(inicio, fin)

                    if user_id not in historico_fichajes[guild_str]:
                        historico_fichajes[guild_str][user_id] = []

                    registro = {
                        'inicio': inicio.strftime('%H:%M:%S'),
                        'fin': fin.strftime('%H:%M:%S'),
                        'horas': horas_trabajadas,
                        'fecha': fin.strftime('%d/%m/%Y')
                    }
                    historico_fichajes[guild_str][user_id].append(registro)

                    if user_id not in horas_totales[guild_str]:
                        horas_totales[guild_str][user_id] = 0
                    horas_totales[guild_str][user_id] += horas_trabajadas

                    del fichajes_activos[user_id]
                    fichajes_cerrados += 1
                except Exception as e:
                    print(f"Error cerrando fichaje de {user_id}: {e}")

        # Guardar período actual en historial
        if guild_str in horas_totales and horas_totales[guild_str]:
            periodo_actual = {
                'fecha_fin': datetime.now().strftime('%d/%m/%Y %H:%M'),
                'datos': horas_totales[guild_str].copy()
            }
            periodos_fichaje[guild_str].append(periodo_actual)

        # Resetear horas totales
        horas_totales[guild_str] = {}

        await guardar_datos()

        # Enviar log
        await enviar_log_fichaje(
            guild_id,
            f"🏁 **{interaction.user.display_name}** ha finalizado el período de fichaje. {fichajes_cerrados} fichajes cerrados, {total_usuarios} usuarios reseteados."
        )

        embed_result = discord.Embed(
            title="✅ Período finalizado",
            description=
            f"**Resumen:**\n• {fichajes_cerrados} fichajes cerrados automáticamente\n• {total_usuarios} usuarios tenían horas registradas\n• Período guardado en historial\n• Todas las horas reseteadas a 0\n\n¡Nuevo período iniciado!",
            color=0x00ff00,
            timestamp=datetime.now())
        await confirm_interaction.response.edit_message(embed=embed_result,
                                                        view=None)

    async def cancelar_callback(cancel_interaction):
        if cancel_interaction.user != interaction.user:
            await cancel_interaction.response.send_message(
                "❌ Solo quien ejecutó el comando puede cancelar.",
                ephemeral=True)
            return

        embed_cancel = discord.Embed(
            title="❌ Operación cancelada",
            description="No se ha finalizado el período de fichaje",
            color=0xff0000)
        await cancel_interaction.response.edit_message(embed=embed_cancel,
                                                       view=None)

    confirm_button = discord.ui.Button(label="Confirmar",
                                       style=discord.ButtonStyle.danger,
                                       emoji="✅")
    cancel_button = discord.ui.Button(label="Cancelar",
                                      style=discord.ButtonStyle.secondary,
                                      emoji="❌")

    confirm_button.callback = confirmar_callback
    cancel_button.callback = cancelar_callback

    view.add_item(confirm_button)
    view.add_item(cancel_button)

    await interaction.response.send_message(embed=embed_confirm,
                                            view=view,
                                            ephemeral=True)


@bot.event
async def on_command_error(ctx, error):
    """Manejo de errores de comandos"""
    if isinstance(error, commands.CommandNotFound):
        embed = discord.Embed(
            title="❌ Comando no encontrado",
            description="Usa `!ayuda` para ver los comandos disponibles",
            color=0xff0000)
        await ctx.send(embed=embed, delete_after=5)

    elif isinstance(error, commands.MissingPermissions):
        embed = discord.Embed(
            title="❌ Sin permisos",
            description="No tienes permisos para usar este comando",
            color=0xff0000)
        await ctx.send(embed=embed, delete_after=5)

    elif isinstance(error, commands.MissingRequiredArgument):
        embed = discord.Embed(
            title="❌ Argumento faltante",
            description=
            "Te falta proporcionar algunos argumentos para este comando",
            color=0xff0000)
        await ctx.send(embed=embed, delete_after=5)

    else:
        print(f"Error no manejado: {error}")


@bot.event
async def on_member_join(member):
    """Mensaje de bienvenida cuando alguien se une"""
    # Buscar un canal llamado 'general' o 'bienvenida'
    channel = discord.utils.get(member.guild.channels, name='general')
    if not channel:
        channel = discord.utils.get(member.guild.channels, name='bienvenida')
    if not channel:
        channel = member.guild.system_channel

    if channel:
        embed = discord.Embed(
            title="🎉 ¡Bienvenido!",
            description=
            f"¡Hola {member.mention}! Bienvenido a **{member.guild.name}**",
            color=0x00ff00)
        embed.add_field(name="📝 Información",
                        value="Usa `!ayuda` para ver los comandos disponibles",
                        inline=False)
        embed.set_thumbnail(url=member.avatar.url if member.avatar else member.
                            default_avatar.url)
        embed.set_footer(
            text=f"Ahora somos {member.guild.member_count} miembros")

        await channel.send(embed=embed)


# Función para mantener el bot vivo optimizada para deployment

# Función principal optimizada para 24/7
async def main():
    """Función principal del bot optimizada para deployment 24/7"""
    max_retries = 5
    retry_count = 0

    while retry_count < max_retries:
        try:
            # Verificar que el token existe
            token = os.getenv('DISCORD_TOKEN')
            if not token:
                print("❌ Error: No se encontró el token de Discord")
                print("🔧 Configura la variable DISCORD_TOKEN")
                return

            print(
                f"🚀 Iniciando bot de Discord 24/7 (intento {retry_count + 1}/{max_retries})"
            )

            # Iniciar el bot
            async with bot:
                # Crear tarea para mantener vivo el bot
                keep_alive()  # 🔹 Levanta el servidor Flask para Render
                await bot.start(token)

        except discord.LoginFailure:
            print("❌ Error: Token de Discord inválido")
            break  # No reintentar con token inválido
        except discord.ConnectionClosed:
            retry_count += 1
            print(
                f"⚠️ Conexión perdida. Reintentando en 30 segundos... ({retry_count}/{max_retries})"
            )
            await asyncio.sleep(30)
        except Exception as e:
            retry_count += 1
            print(f"❌ Error inesperado: {e}")
            if retry_count < max_retries:
                print(
                    f"🔄 Reintentando en 60 segundos... ({retry_count}/{max_retries})"
                )
                await asyncio.sleep(60)
            else:
                print("❌ Máximo de reintentos alcanzado. Cerrando bot.")
                break


if __name__ == "__main__":
    print("🤖 Bot de Discord CNP SC-RP iniciando...")
    print("⚡ Configurado para funcionamiento 24/7")
    print("🔧 Powered by Replit Deployment")
    asyncio.run(main())

