import os
import discord
from discord.ext import commands
import random
from flask import Flask
from threading import Thread

# ==============================================================================
# ⚙️ CENTRAL DE CONFIGURAÇÃO E TEXTOS DO BOT (EDITE AQUI)
# ==============================================================================

# 🔑 CREDENCIAIS E APLICAÇÃO (Leitura segura via Variáveis de Ambiente)
TOKEN = os.getenv("TOKEN", "SEU_TOKEN_AQUI")
PREFIXO = "!"
STATUS_JOGO = "🏆 Ultimate Rift | !ajuda"

# 🔗 LINKS E NOMES DOS CANAIS
LINK_TABELA = "https://challonge.com/seu-campeonato"
FOTO_BOAS_VINDAS = "https://i.imgur.com/8N7aWkM.png"
NOME_CANAL_BOAS_VINDAS = "chat-geral-equipes"
NOME_CANAL_RESULTADOS = "chaveamento-e-tabela"

# 💬 MENSAGEM DE BOAS-VINDAS (ENTRADA)
BOAS_VINDAS_TITULO = "⚔️ Bem-vindo(a) ao Ultimate Rift, {membro}!"
BOAS_VINDAS_TEXTO = (
    "Olá {membro_mention}! Seja bem-vindo ao servidor oficial do campeonato.\n\n"
    "📌 **Primeiros Passos:**\n"
    "• Digite `!tabela` para consultar o chaveamento.\n"
    "• Digite `!regras` para ver o regulamento oficial.\n"
    "• Digite `!ajuda` para ver os comandos do bot."
)
BOAS_VINDAS_RODAPE = "Ultimate Rift • Campeonato de LoL"

# 👋 MENSAGEM DE SAÍDA (DESPEDIDA)
SAIDA_TITULO = "👋 Um jogador saiu do servidor"
SAIDA_TEXTO = "**{membro_display}** (`{membro_name}`) deixou o campeonato."

# 📜 REGULAMENTO E PAUSAS
REGRAS_TITULO = "📜 Regulamento Oficial do Torneio"
REGRAS_TEXTO = (
    "**1. Pontualidade:** Tolerância de 10 minutos após o horário marcado.\n"
    "**2. Pausas:** Cada equipe tem direito a até 10 minutos de pausa por partida.\n"
    "**3. Comprovação:** O capitão vencedor deve enviar a print do fim do jogo.\n"
    "**4. Conduta:** Respeito obrigatório com juízes e adversários."
)

PAUSA_TITULO = "⏱️ Regras de Pausa (Pause)"
PAUSA_TEXTO = (
    "• **Tempo Máximo:** 10 minutos acumulados por equipe.\n"
    "• **Motivos Válidos:** Desconexão técnica ou problema de equipamento.\n"
    "• **Aviso:** Deve-se informar no chat `/all` o motivo da pausa imediatamente."
)

# 🗳️ SISTEMA DE VOTAÇÃO E RESULTADOS
VOTOS_NECESSARIOS = 6
BOTAO_AZUL_ROTULO = "Vitória Time Azul 🔵"
BOTAO_VERMELHO_ROTULO = "Vitória Time Vermelho 🔴"

VOTACAO_TITULO = "⚔️ Validação de Resultado da Partida"
VOTACAO_TEXTO = (
    "**Lado Azul 🔵:** {time_azul}\n"
    "**Lado Vermelho 🔴:** {time_vermelho}\n\n"
    "📌 *Clique no botão do time que venceu para confirmar.*\n"
    "São necessários **{votos_necessarios} votos** no total para homologar a partida.\n\n"
    "📊 **Placar da Votação ({total_votos}/{votos_necessarios}):**\n"
    "• Votos no {time_azul} 🔵: **{votos_azul}**\n"
    "• Votos no {time_vermelho} 🔴: **{votos_vermelho}**"
)

RESULTADO_OFICIAL_TITULO = "🏆 RESULTADO OFICIAL DA PARTIDA"
RESULTADO_OFICIAL_TEXTO = (
    "👑 **VENCEDOR:** {vencedor} ({lado_vencedor})\n"
    "💀 **DERROTADO:** {perdedor}\n\n"
    "✨ *A vitória foi validada pelos próprios jogadores por votação ({total_votos} votos).*"
)

# 🛡️ ELENCOS DOS TIMES (ROSTERS)
ROSTERS = {
    "equipe 1": "• Capitão: Player1\n• Top: Player1\n• JG: Player2\n• Mid: Player3\n• ADC: Player4\n• Sup: Player5",
    "equipe 2": "• Capitão: Player6\n• Top: Player6\n• JG: Player7\n• Mid: Player8\n• ADC: Player9\n• Sup: Player10",
    "equipe 3": "Elenco a ser definido pelo capitão.",
    "equipe 4": "Elenco a ser definido pelo capitão.",
    "equipe 5": "Elenco a ser definido pelo capitão.",
    "equipe 6": "Elenco a ser definido pelo capitão.",
    "equipe 7": "Elenco a ser definido pelo capitão.",
    "equipe 8": "Elenco a ser definido pelo capitão.",
}

# ==============================================================================
# 🌐 SERVIDOR WEB FAKE (KEEP ALIVE PARA RENDER / WEB SERVICE)
# ==============================================================================

app = Flask('')

@app.route('/')
def home():
    return "Bot Ultimate Rift rodando 24/7!"

def run_web():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run_web)
    t.start()

# ==============================================================================
# 🚨 LÓGICA DO BOT
# ==============================================================================

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix=PREFIXO, intents=intents, help_command=None)
checkins_realizados = set()

@bot.event
async def on_ready():
    print(f"🚀 Bot {bot.user.name} está online!")
    await bot.change_presence(activity=discord.Game(name=STATUS_JOGO))

# --- EVENTOS DE ENTRADA E SAÍDA ---

@bot.event
async def on_member_join(member):
    canal = discord.utils.get(member.guild.text_channels, name=NOME_CANAL_BOAS_VINDAS)
    if canal:
        embed = discord.Embed(
            title=BOAS_VINDAS_TITULO.format(membro=member.display_name),
            description=BOAS_VINDAS_TEXTO.format(membro_mention=member.mention),
            color=discord.Color.gold()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        if FOTO_BOAS_VINDAS:
            embed.set_image(url=FOTO_BOAS_VINDAS)
        embed.set_footer(text=BOAS_VINDAS_RODAPE)
        await canal.send(content=f"👋 Bem-vindo(a) {member.mention}!", embed=embed)

@bot.event
async def on_member_remove(member):
    canal = discord.utils.get(member.guild.text_channels, name=NOME_CANAL_BOAS_VINDAS)
    if canal:
        embed = discord.Embed(
            title=SAIDA_TITULO,
            description=SAIDA_TEXTO.format(membro_display=member.display_name, membro_name=member.name),
            color=discord.Color.red()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        await canal.send(embed=embed)

# --- VOTAÇÃO DE RESULTADOS INTERATIVA ---

class VotacaoResultadoView(discord.ui.View):
    def __init__(self, time_azul: str, time_vermelho: str):
        super().__init__(timeout=1800)
        self.time_azul = time_azul
        self.time_vermelho = time_vermelho
        self.votos_azul = set()
        self.votos_vermelho = set()

        self.votar_azul.label = BOTAO_AZUL_ROTULO
        self.votar_vermelho.label = BOTAO_VERMELHO_ROTULO

    def atualizar_embed(self) -> discord.Embed:
        total = len(self.votos_azul) + len(self.votos_vermelho)
        texto = VOTACAO_TEXTO.format(
            time_azul=self.time_azul,
            time_vermelho=self.time_vermelho,
            votos_necessarios=VOTOS_NECESSARIOS,
            total_votos=total,
            votos_azul=len(self.votos_azul),
            votos_vermelho=len(self.votos_vermelho)
        )
        embed = discord.Embed(title=VOTACAO_TITULO, description=texto, color=discord.Color.gold())
        embed.set_footer(text="Ultimate Rift • Votação Oficial")
        return embed

    async def verificar_fim(self, interaction: discord.Interaction):
        total = len(self.votos_azul) + len(self.votos_vermelho)
        if total >= VOTOS_NECESSARIOS:
            for item in self.children:
                item.disabled = True

            if len(self.votos_azul) > len(self.votos_vermelho):
                vencedor, perdedor, lado = self.time_azul, self.time_vermelho, "Azul 🔵"
            else:
                vencedor, perdedor, lado = self.time_vermelho, self.time_azul, "Vermelho 🔴"

            embed_fim = self.atualizar_embed()
            embed_fim.title = "✅ Votação Concluída e Confirmada!"
            embed_fim.color = discord.Color.green()
            await interaction.response.edit_message(embed=embed_fim, view=self)

            canal_res = discord.utils.get(interaction.guild.text_channels, name=NOME_CANAL_RESULTADOS) or interaction.channel
            texto_oficial = RESULTADO_OFICIAL_TEXTO.format(
                vencedor=vencedor,
                lado_vencedor=lado,
                perdedor=perdedor,
                total_votos=total
            )
            embed_oficial = discord.Embed(title=RESULTADO_OFICIAL_TITULO, description=texto_oficial, color=discord.Color.green())
            embed_oficial.set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else None)
            await canal_res.send(embed=embed_oficial)
        else:
            await interaction.response.edit_message(embed=self.atualizar_embed(), view=self)

    @discord.ui.button(style=discord.ButtonStyle.primary)
    async def votar_azul(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.votos_vermelho.discard(interaction.user.id)
        self.votos_azul.add(interaction.user.id)
        await self.verificar_fim(interaction)

    @discord.ui.button(style=discord.ButtonStyle.danger)
    async def votar_vermelho(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.votos_azul.discard(interaction.user.id)
        self.votos_vermelho.add(interaction.user.id)
        await self.verificar_fim(interaction)

@bot.command(name="resultado", aliases=["validar"])
async def iniciar_resultado(ctx, time_azul: str, time_vermelho: str):
    view = VotacaoResultadoView(time_azul=time_azul, time_vermelho=time_vermelho)
    await ctx.send(embed=view.atualizar_embed(), view=view)

# --- COMANDOS UTILITÁRIOS E INFORMATIVOS ---

@bot.command(name="checkin")
async def checkin(ctx, *, nome_time: str):
    nome_limpo = nome_time.strip().lower()
    if nome_limpo in checkins_realizados:
        await ctx.send(f"⚠️ O **{nome_time.upper()}** já realizou o check-in!")
        return
    checkins_realizados.add(nome_limpo)
    await ctx.send(f"✅ Check-in confirmado para a equipe **{nome_time.upper()}**!")

@bot.command(name="checkins")
@commands.has_permissions(administrator=True)
async def ver_checkins(ctx):
    if not checkins_realizados:
        await ctx.send("📋 Nenhum time fez check-in ainda.")
        return
    lista = "\n".join([f"• {t.title()}" for t in checkins_realizados])
    await ctx.send(f"📋 **Times com Check-in Realizado:**\n{lista}")

@bot.command(name="time", aliases=["elenco", "roster"])
async def consultar_time(ctx, *, nome_time: str):
    nome_limpo = nome_time.strip().lower()
    if nome_limpo in ROSTERS:
        embed = discord.Embed(title=f"🛡️ Elenco • {nome_time.upper()}", description=ROSTERS[nome_limpo], color=discord.Color.blue())
        await ctx.send(embed=embed)
    else:
        await ctx.send(f"❌ Time `{nome_time}` não encontrado no sistema.")

@bot.command(name="anunciar")
@commands.has_permissions(administrator=True)
async def anunciar(ctx, canal: discord.TextChannel, *, conteudo: str):
    try:
        titulo, texto = conteudo.split("|", 1) if "|" in conteudo else ("📢 Comunicado Oficial", conteudo)
        embed = discord.Embed(title=titulo.strip(), description=texto.strip(), color=discord.Color.blue())
        embed.set_footer(text=f"Enviado por {ctx.author.display_name}")
        await canal.send(embed=embed)
        await ctx.send(f"✅ Anúncio postado em {canal.mention}!")
    except Exception:
        await ctx.send("❌ Uso correto: `!anunciar #canal Titulo | Mensagem`")

@bot.command(name="ajuda", aliases=["help"])
async def ajuda(ctx):
    embed = discord.Embed(title="🤖 Comandos da Arena • Ultimate Rift", color=discord.Color.purple())
    embed.add_field(
        name="⚔️ Gestão de Partidas",
        value="• `!resultado <TimeAzul> <TimeVermelho>` - Inicia votação de resultado\n• `!checkin <Nome do Time>` - Confirma presença\n• `!time <Nome do Time>` - Ver integrantes\n• `!lado` - Sorteio de Blue/Red Side",
        inline=False
    )
    embed.add_field(
        name="📊 Informações",
        value="• `!tabela` - Link do chaveamento\n• `!regras` - Regulamento\n• `!pausa` - Regras de pause",
        inline=False
    )
    if ctx.author.guild_permissions.administrator:
        embed.add_field(name="🛠️ Staff", value="• `!checkins` - Lista de presenciais\n• `!anunciar #canal Titulo | Texto` - Envia aviso", inline=False)
    await ctx.send(embed=embed)

@bot.command(name="tabela")
async def tabela(ctx):
    await ctx.send(f"📊 **Chaveamento Oficial:** {LINK_TABELA}")

@bot.command(name="regras")
async def regras(ctx):
    embed = discord.Embed(title=REGRAS_TITULO, description=REGRAS_TEXTO, color=discord.Color.red())
    await ctx.send(embed=embed)

@bot.command(name="pausa")
async def pausa(ctx):
    embed = discord.Embed(title=PAUSA_TITULO, description=PAUSA_TEXTO, color=discord.Color.orange())
    await ctx.send(embed=embed)

@bot.command(name="lado")
async def lado(ctx):
    res = random.choice(["BLUE SIDE 🔵 (Lado Azul)", "RED SIDE 🔴 (Lado Vermelho)"])
    await ctx.send(f"🎲 Sorteio de lado: **{res}**")

# Executa o servidor web fake junto com o bot
keep_alive()
bot.run(TOKEN)
