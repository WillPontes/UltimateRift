import os
import json
import urllib.parse
import discord
from discord.ext import commands
import random
from flask import Flask
from threading import Thread

# ==============================================================================
# ⚙️ GERENCIADOR DE CONFIGURAÇÃO, MENSAGENS E PERSISTÊNCIA (JSON)
# ==============================================================================

MENSAGENS_FILE = "mensagens.json"
DATA_FILE = "data.json"

def carregar_mensagens():
    """Carrega as frases do bot a partir do mensagens.json"""
    if os.path.exists(MENSAGENS_FILE):
        try:
            with open(MENSAGENS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️ Erro ao carregar {MENSAGENS_FILE}: {e}")
    return {}

def carregar_dados():
    """Carrega a base de dados local a partir do data.json"""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️ Erro ao carregar {DATA_FILE}: {e}")
    return {"checkins": [], "rosters": {}}

def salvar_dados(dados):
    """Salva as informações no data.json para persistência"""
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(dados, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"❌ Erro ao salvar {DATA_FILE}: {e}")

MSGS = carregar_mensagens()
DADOS_BOT = carregar_dados()

TOKEN = os.getenv("TOKEN", "SEU_TOKEN_AQUI")
PREFIXO = "!"
STATUS_JOGO = MSGS.get("status_jogo", "🏆 Ultimate Rift | !ajuda")

# ==============================================================================
# 🌐 SERVIDOR WEB FAKE (KEEP ALIVE COMPATÍVEL COM RENDER E WEB SERVICE)
# ==============================================================================

app = Flask('')

@app.route('/')
def home():
    return "Bot Ultimate Rift rodando 24/7!"

def run_web():
    # Render injeta a variável PORT. Usa 8080 como fallback local.
    port = int(os.getenv("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_web)
    t.daemon = True
    t.start()

# ==============================================================================
# 🛠️ FUNÇÕES AUXILIARES (OP.GG MULTI-SEARCH)
# ==============================================================================

def gerar_opgg_multisearch(nicks_str_ou_lista, regiao="br"):
    """
    Gera o link de Multi-Search do OP.GG para uma lista de Nick#TAG ou nomes de invocadores.
    Exemplo: Player1#BR1, Player2#BR1 -> https://www.op.gg/multisearch/br?summoners=Player1%23BR1%2CPlayer2%23BR1
    """
    if isinstance(nicks_str_ou_lista, str):
        # Separa por vírgula ou quebra de linha
        nicks = [n.strip() for n in nicks_str_ou_lista.replace("\n", ",").split(",") if n.strip()]
    else:
        nicks = [n.strip() for n in nicks_str_ou_lista if n.strip()]

    if not nicks:
        return None

    encoded_nicks = [urllib.parse.quote(nick) for nick in nicks]
    summoners_param = "%2C".join(encoded_nicks)
    return f"https://www.op.gg/multisearch/{regiao}?summoners={summoners_param}"

# ==============================================================================
# 🚨 LÓGICA E EVENTOS DO BOT
# ==============================================================================

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix=PREFIXO, intents=intents, help_command=None)

@bot.event
async def on_ready():
    print(f"🚀 Bot {bot.user.name} está online!")
    await bot.change_presence(activity=discord.Game(name=STATUS_JOGO))

# --- EVENTOS DE ENTRADA E SAÍDA ---

@bot.event
async def on_member_join(member):
    canal_nome = MSGS.get("nome_canal_boas_vindas", "chat-geral-equipes")
    canal = discord.utils.get(member.guild.text_channels, name=canal_nome)
    if canal:
        embed = discord.Embed(
            title=MSGS.get("boas_vindas_titulo", "").format(membro=member.display_name),
            description=MSGS.get("boas_vindas_texto", "").format(membro_mention=member.mention),
            color=discord.Color.gold()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        foto = MSGS.get("foto_boas_vindas")
        if foto:
            embed.set_image(url=foto)
        embed.set_footer(text=MSGS.get("boas_vindas_rodape", "Ultimate Rift"))
        await canal.send(content=f"👋 Bem-vindo(a) {member.mention}!", embed=embed)

@bot.event
async def on_member_remove(member):
    canal_nome = MSGS.get("nome_canal_boas_vindas", "chat-geral-equipes")
    canal = discord.utils.get(member.guild.text_channels, name=canal_nome)
    if canal:
        embed = discord.Embed(
            title=MSGS.get("saida_titulo", "👋 Jogador Saiu"),
            description=MSGS.get("saida_texto", "").format(membro_display=member.display_name, membro_name=member.name),
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

        self.votar_azul.label = MSGS.get("botao_azul_rotulo", "Vitória Time Azul 🔵")
        self.votar_vermelho.label = MSGS.get("botao_vermelho_rotulo", "Vitória Time Vermelho 🔴")

    def atualizar_embed(self) -> discord.Embed:
        total = len(self.votos_azul) + len(self.votos_vermelho)
        votos_req = MSGS.get("votos_necessarios", 6)
        texto = MSGS.get("votacao_texto", "").format(
            time_azul=self.time_azul,
            time_vermelho=self.time_vermelho,
            votos_necessarios=votos_req,
            total_votos=total,
            votos_azul=len(self.votos_azul),
            votos_vermelho=len(self.votos_vermelho)
        )
        embed = discord.Embed(title=MSGS.get("votacao_titulo", "Validação de Resultado"), description=texto, color=discord.Color.gold())
        embed.set_footer(text="Ultimate Rift • Votação Oficial")
        return embed

    async def verificar_fim(self, interaction: discord.Interaction):
        total = len(self.votos_azul) + len(self.votos_vermelho)
        votos_req = MSGS.get("votos_necessarios", 6)
        if total >= votos_req:
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

            canal_nome = MSGS.get("nome_canal_resultados", "chaveamento-e-tabela")
            canal_res = discord.utils.get(interaction.guild.text_channels, name=canal_nome) or interaction.channel
            texto_oficial = MSGS.get("resultado_oficial_texto", "").format(
                vencedor=vencedor,
                lado_vencedor=lado,
                perdedor=perdedor,
                total_votos=total
            )
            embed_oficial = discord.Embed(title=MSGS.get("resultado_oficial_titulo", "RESULTADO OFICIAL"), description=texto_oficial, color=discord.Color.green())
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

# --- SISTEMA DE CADASTRO E OP.GG DE EQUIPES ---

@bot.command(name="cadastrartime", aliases=["cadastrar_time", "addtime"])
@commands.has_permissions(administrator=True)
async def cadastrar_time(ctx, *, conteudo: str):
    """
    Sintaxe: !cadastrartime Nome do Time | Nick1#BR1, Nick2#BR1, Nick3#BR1, Nick4#BR1, Nick5#BR1
    """
    if "|" not in conteudo:
        await ctx.send("❌ Uso correto: `!cadastrartime Nome do Time | Nick1#BR1, Nick2#BR1, Nick3#BR1, Nick4#BR1, Nick5#BR1`")
        return

    nome_time_raw, nicks_raw = conteudo.split("|", 1)
    nome_time = nome_time_raw.strip()
    key_time = nome_time.lower()

    nicks_lista = [n.strip() for n in nicks_raw.split(",") if n.strip()]
    opgg_link = gerar_opgg_multisearch(nicks_lista)

    DADOS_BOT["rosters"][key_time] = {
        "nome": nome_time,
        "jogadores": nicks_lista,
        "opgg_link": opgg_link
    }
    salvar_dados(DADOS_BOT)

    embed = discord.Embed(title=f"✅ Equipe Cadastrada: {nome_time}", color=discord.Color.green())
    jogadores_fmt = "\n".join([f"• {j}" for j in nicks_lista])
    embed.add_field(name="👥 Elenco", value=jogadores_fmt if jogadores_fmt else "Nenhum jogador informado", inline=False)
    if opgg_link:
        embed.add_field(name="🔍 OP.GG Multi-Search", value=f"[👉 Clique aqui para abrir a análise da equipe no OP.GG]({opgg_link})", inline=False)

    await ctx.send(embed=embed)

@bot.command(name="time", aliases=["elenco", "roster"])
async def consultar_time(ctx, *, nome_time: str):
    key_time = nome_time.strip().lower()

    if key_time in DADOS_BOT["rosters"]:
        info = DADOS_BOT["rosters"][key_time]
        nome = info.get("nome", nome_time.upper())
        jogadores = info.get("jogadores", [])
        opgg_link = info.get("opgg_link") or gerar_opgg_multisearch(jogadores)

        embed = discord.Embed(title=f"🛡️ Elenco • {nome}", color=discord.Color.blue())
        if jogadores:
            jogadores_fmt = "\n".join([f"• {j}" for j in jogadores])
            embed.add_field(name="👥 Integrantes / Nicks", value=jogadores_fmt, inline=False)
        else:
            embed.description = "Elenco a ser definido pelo capitão."

        if opgg_link:
            embed.add_field(name="🔍 OP.GG Multi-Search", value=f"[👉 Abrir Multi-Search da Equipe]({opgg_link})", inline=False)

        await ctx.send(embed=embed)
    else:
        await ctx.send(f"❌ Time `{nome_time}` não encontrado no sistema. Admins podem cadastrar via `!cadastrartime Nome | Nick1#TAG, Nick2#TAG`.")

# --- CHECK-IN PERSISTENTE ---

@bot.command(name="checkin")
async def checkin(ctx, *, nome_time: str):
    nome_limpo = nome_time.strip().lower()
    if nome_limpo in DADOS_BOT["checkins"]:
        await ctx.send(f"⚠️ O **{nome_time.upper()}** já realizou o check-in!")
        return

    DADOS_BOT["checkins"].append(nome_limpo)
    salvar_dados(DADOS_BOT)
    await ctx.send(f"✅ Check-in confirmado para a equipe **{nome_time.upper()}**!")

@bot.command(name="checkins")
@commands.has_permissions(administrator=True)
async def ver_checkins(ctx):
    checkins = DADOS_BOT.get("checkins", [])
    if not checkins:
        await ctx.send("📋 Nenhum time fez check-in ainda.")
        return
    lista = "\n".join([f"• {t.title()}" for t in checkins])
    await ctx.send(f"📋 **Times com Check-in Realizado:**\n{lista}")

@bot.command(name="limparcheckins")
@commands.has_permissions(administrator=True)
async def limpar_checkins(ctx):
    DADOS_BOT["checkins"] = []
    salvar_dados(DADOS_BOT)
    await ctx.send("🧹 Lista de check-ins zerada com sucesso!")

# --- SISTEMA DE CHAMADOS / JUIZ ---

@bot.command(name="juiz", aliases=["suporte", "ticket"])
async def chamar_juiz(ctx, *, motivo: str = "Sem motivo especificado"):
    canal_suporte_nome = MSGS.get("nome_canal_suporte", "chamados-juiz")
    canal_suporte = discord.utils.get(ctx.guild.text_channels, name=canal_suporte_nome) or ctx.channel

    texto_chamado = MSGS.get("juiz_solicitado_texto", "").format(
        autor_mention=ctx.author.mention,
        autor_name=ctx.author.name,
        canal_mention=ctx.channel.mention,
        motivo=motivo
    )
    embed = discord.Embed(
        title=MSGS.get("juiz_solicitado_titulo", "🚨 Chamado de Suporte / Juiz Solicitado"),
        description=texto_chamado,
        color=discord.Color.red()
    )
    embed.set_footer(text=f"Solicitado por {ctx.author.display_name}")

    msg_suporte = await canal_suporte.send(content="🔔 @here **Atenção Juízes/Staff!** Novo chamado aberto:", embed=embed)
    if canal_suporte != ctx.channel:
        await ctx.send(f"✅ Chamado enviado para a arbitragem! Um juiz atenderá em breve no canal {canal_suporte.mention}.")

# --- COMANDOS DE INFORMAÇÕES E RECARGA ---

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

@bot.command(name="reloadmsgs")
@commands.has_permissions(administrator=True)
async def recarregar_mensagens(ctx):
    global MSGS, STATUS_JOGO
    MSGS = carregar_mensagens()
    STATUS_JOGO = MSGS.get("status_jogo", "🏆 Ultimate Rift | !ajuda")
    await bot.change_presence(activity=discord.Game(name=STATUS_JOGO))
    await ctx.send("🔄 Mensagens do `mensagens.json` recarregadas com sucesso!")

@bot.command(name="ajuda", aliases=["help"])
async def ajuda(ctx):
    embed = discord.Embed(title="🤖 Comandos da Arena • Ultimate Rift", color=discord.Color.purple())
    embed.add_field(
        name="⚔️ Gestão de Partidas",
        value="• `!resultado <TimeAzul> <TimeVermelho>` - Inicia votação de resultado\n"
              "• `!checkin <Nome do Time>` - Confirms presença\n"
              "• `!time <Nome do Time>` - Ver integrantes e link do OP.GG\n"
              "• `!lado` - Sorteio de Blue/Red Side\n"
              "• `!juiz <motivo>` - Solicita atendimento de um juiz/staff",
        inline=False
    )
    embed.add_field(
        name="📊 Informações",
        value=f"• `!tabela` - Link do chaveamento\n"
              f"• `!regras` - Regulamento oficial\n"
              f"• `!pausa` - Regras de pause",
        inline=False
    )
    if ctx.author.guild_permissions.administrator:
        embed.add_field(
            name="🛠️ Administração & Staff",
            value="• `!cadastrartime Nome | Nick1#TAG, Nick2#TAG...` - Cadastra equipe & OP.GG\n"
                  "• `!checkins` - Lista times confirmados\n"
                  "• `!limparcheckins` - Reseta lista de presenciais\n"
                  "• `!anunciar #canal Titulo | Texto` - Posta comunicado\n"
                  "• `!reloadmsgs` - Atualiza frases do `mensagens.json`",
            inline=False
        )
    await ctx.send(embed=embed)

@bot.command(name="tabela")
async def tabela(ctx):
    link = MSGS.get("link_tabela", "https://challonge.com/seu-campeonato")
    await ctx.send(f"📊 **Chaveamento Oficial:** {link}")

@bot.command(name="regras")
async def regras(ctx):
    embed = discord.Embed(
        title=MSGS.get("regras_titulo", "📜 Regulamento"),
        description=MSGS.get("regras_texto", ""),
        color=discord.Color.red()
    )
    await ctx.send(embed=embed)

@bot.command(name="pausa")
async def pausa(ctx):
    embed = discord.Embed(
        title=MSGS.get("pausa_titulo", "⏱️ Regras de Pausa"),
        description=MSGS.get("pausa_texto", ""),
        color=discord.Color.orange()
    )
    await ctx.send(embed=embed)

@bot.command(name="lado")
async def lado(ctx):
    res = random.choice(["BLUE SIDE 🔵 (Lado Azul)", "RED SIDE 🔴 (Lado Vermelho)"])
    await ctx.send(f"🎲 Sorteio de lado: **{res}**")

# Executa o servidor web fake junto com o bot
keep_alive()
bot.run(TOKEN)
