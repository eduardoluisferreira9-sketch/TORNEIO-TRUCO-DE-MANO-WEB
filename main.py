import os
import sqlite3
import random
import time
import shutil
from fastapi import FastAPI, Request, Form, Depends, HTTPException, UploadFile, File
from fastapi.responses import RedirectResponse, HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

# --- CONFIGURAÇÃO DE SEGURANÇA POR VARIÁVEIS DE AMBIENTE ---
# Pega as chaves do ambiente web, se não achar, usa os padrões locais
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "truco123")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# --- ALTERAÇÃO CRÍTICA DO BANCO DE DADOS (HISTÓRICO SEGURO) ---
# Se estiver na nuvem (ex: Render), apontamos o SQLite para uma pasta persistente (/data)
if os.path.exists("/data"):
    DB_FILE = "/data/torneio.db"
else:
    DB_FILE = os.path.join(BASE_DIR, "torneio.db")

TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
TEMPLATES_PUBLICO_DIR = os.path.join(BASE_DIR, "sistema_publico", "templates")

app = FastAPI(title="Painel de Controle do Administrador - Truco Cego")
templates = Jinja2Templates(directory=[TEMPLATES_DIR, TEMPLATES_PUBLICO_DIR])

UPLOAD_DIR = os.path.join(BASE_DIR, "static", "comprovantes")
os.makedirs(UPLOAD_DIR, exist_ok=True)

try:
    app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
except Exception:
    pass

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL;")
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS torneios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome_torneio TEXT DEFAULT 'Torneio de Truco Cego',
            taxa_inscricao REAL DEFAULT 0.0,
            max_rodadas_classificatoria INTEGER DEFAULT 5,
            crono_tempo_restante_seg INTEGER DEFAULT 3000,
            crono_ativo INTEGER DEFAULT 0,
            crono_ultimo_clique REAL DEFAULT 0,
            fase_torneio TEXT DEFAULT 'INSCRICAO'
        )
    ''')
    
    cursor.execute("SELECT COUNT(*) FROM torneios")
    if cursor.fetchone()[0] == 0:
        cursor.execute('''
            INSERT INTO torneios (nome_torneio, taxa_inscricao, max_rodadas_classificatoria, crono_tempo_restante_seg, fase_torneio) 
            VALUES ('Torneio de Truco Cego', 5.00, 5, 3000, 'INSCRICAO')
        ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS atletas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            torneio_id INTEGER NOT NULL DEFAULT 1,
            nome TEXT NOT NULL,
            entidade TEXT NOT NULL DEFAULT 'AVULSO',
            whatsapp TEXT,
            status TEXT DEFAULT 'PENDENTE',
            FOREIGN KEY (torneio_id) REFERENCES torneios(id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS confrontos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            torneio_id INTEGER NOT NULL DEFAULT 1,
            rodada INTEGER NOT NULL,
            mesa INTEGER NOT NULL,
            atleta1_id INTEGER,
            atleta2_id INTEGER,
            atleta1_nome TEXT,
            atleta2_nome TEXT,
            tipo_placar TEXT DEFAULT NULL,
            vencedor_id INTEGER DEFAULT NULL,
            sets1 INTEGER DEFAULT NULL,
            sets2 INTEGER DEFAULT NULL,
            tentos1 INTEGER DEFAULT NULL,
            tentos2 INTEGER DEFAULT NULL,
            flores1 INTEGER DEFAULT 0,
            flores2 INTEGER DEFAULT 0,
            FOREIGN KEY (torneio_id) REFERENCES torneios(id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS historico_campeoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            torneio_id INTEGER UNIQUE,
            nome_torneio TEXT,
            campeao TEXT,
            vice TEXT,
            terceiro TEXT,
            quarto TEXT,
            rei_das_flores TEXT,
            qtd_flores INTEGER,
            FOREIGN KEY (torneio_id) REFERENCES torneios(id)
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def get_db():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def verificar_admin(request: Request):
    token = request.cookies.get("admin_token")
    if token != ADMIN_PASSWORD:
        raise HTTPException(status_code=303, headers={"Location": "/admin-painel/login"})
    return True

def obter_torneio_ativo(cursor):
    cursor.execute("SELECT * FROM torneios WHERE fase_torneio != 'CONCLUIDO' ORDER BY id DESC LIMIT 1")
    torneio = cursor.fetchone()
    if not torneio:
        cursor.execute("SELECT * FROM torneios ORDER BY id DESC LIMIT 1")
        torneio = cursor.fetchone()
    return dict(torneio)

def atualizar_e_obter_cronometro(db: sqlite3.Connection):
    cursor = db.cursor()
    config = obter_torneio_ativo(cursor)
    
    if config["crono_ativo"] == 1:
        agora = time.time()
        decorrido = int(agora - config["crono_ultimo_clique"])
        if decorrido > 0:
            novo_tempo = max(0, config["crono_tempo_restante_seg"] - decorrido)
            ativo = 1 if novo_tempo > 0 else 0
            cursor.execute('UPDATE torneios SET crono_tempo_restante_seg = ?, crono_ultimo_clique = ?, crono_ativo = ? WHERE id = ?', 
                           (novo_tempo, agora, ativo, config["id"]))
            db.commit()
            config["crono_tempo_restante_seg"] = novo_tempo
            config["crono_ativo"] = ativo
    return config

def obter_ranking_fase_classificatoria(cursor, torneio_id: int):
    cursor.execute("SELECT id, nome FROM atletas WHERE status = 'APROVADO' AND torneio_id = ?", (torneio_id,))
    todos_atletas = cursor.fetchall()
    lista_classificacao = []
    
    for atleta in todos_atletas:
        atleta_id = atleta["id"]
        
        cursor.execute("""
            SELECT COALESCE(SUM(sets1), 0) as s_pro, COALESCE(SUM(tentos1), 0) as t_pro, 
                   COALESCE(SUM(tentos2), 0) as t_contra, COALESCE(SUM(flores1), 0) as fl, 
                   SUM(CASE WHEN atleta2_id IS NULL THEN 1 ELSE 0 END) as byes 
            FROM confrontos 
            WHERE atleta1_id = ? AND torneio_id = ? AND rodada > 0 AND vencedor_id IS NOT NULL
        """, (atleta_id, torneio_id))
        p1 = cursor.fetchone()
        
        cursor.execute("""
            SELECT COALESCE(SUM(sets2), 0) as s_pro, COALESCE(SUM(tentos2), 0) as t_pro, 
                   COALESCE(SUM(tentos1), 0) as t_contra, COALESCE(SUM(flores2), 0) as fl 
            FROM confrontos 
            WHERE atleta2_id = ? AND torneio_id = ? AND rodada > 0 AND vencedor_id IS NOT NULL
        """, (atleta_id, torneio_id))
        p2 = cursor.fetchone()
            
        cursor.execute("SELECT COUNT(*) FROM confrontos WHERE vencedor_id = ? AND torneio_id = ? AND rodada > 0", (atleta_id, torneio_id))
        vitorias = cursor.fetchone()[0]
        
        sets_ganhos = p1["s_pro"] + p2["s_pro"]
        tentos_pro = p1["t_pro"] + p2["t_pro"]
        tentos_contra = p1["t_contra"] + p2["t_contra"]
        flores = p1["fl"] + p2["fl"]
        
        lista_classificacao.append({
            "id": atleta_id, "nome": atleta["nome"], "vitorias": vitorias, "sets_ganhos": sets_ganhos,
            "saldo_tentos": tentos_pro - tentos_contra, "tentos_pro": tentos_pro, "flores": flores, "chapeu_jogados": p1["byes"]
        })
    lista_classificacao.sort(key=lambda x: (-x["vitorias"], -x["sets_ganhos"], -x["saldo_tentos"], -x["tentos_pro"], -x["flores"], x["id"]))
    return lista_classificacao

@app.get("/inscrever", response_class=HTMLResponse)
@app.get("/admin-painel/inscrever", response_class=HTMLResponse)
def tela_inscricao_atleta(request: Request, db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    cfg_db = obter_torneio_ativo(cursor)
    
    cursor.execute("SELECT DISTINCT entidade FROM atletas WHERE status = 'APROVADO' AND torneio_id = ? ORDER BY entidade ASC", (cfg_db["id"],))
    entidades = [row["entidade"] for row in cursor.fetchall()]
    
    taxa_val = cfg_db["taxa_inscricao"] if cfg_db else 0.0
    taxa_formatada = f"{taxa_val:.2f}".replace('.', ',')

    return templates.TemplateResponse(
        request=request, name="inscricao_atleta.html", 
        context={"config_taxa": taxa_formatada, "entidades": entidades}
    )

@app.post("/inscrever")
@app.post("/admin-painel/inscrever")
async def processar_inscricao_atleta(
    nome: str = Form(...), entidade: str = Form(...), whatsapp: str = Form(...),
    comprovante: UploadFile = File(...), db: sqlite3.Connection = Depends(get_db)
):
    if not comprovante.filename:
        raise HTTPException(status_code=400, detail="O envio do comprovante é obrigatório.")
    
    extensao = os.path.splitext(comprovante.filename)[1]
    nome_seguro = "".join(c for c in nome if c.isalnum() or c in (' ', '_')).rstrip()
    nome_arquivo = f"comprovante_{nome_seguro}_{int(time.time())}{extensao}"
    caminho_final = os.path.join(UPLOAD_DIR, nome_arquivo)
    
    with open(caminho_final, "wb") as buffer:
        shutil.copyfileobj(comprovante.file, buffer)
        
    cursor = db.cursor()
    cfg = obter_torneio_ativo(cursor)
    entidade_limpa = entidade.strip().upper() if entidade.strip() else "AVULSO"
    cursor.execute('''
        INSERT INTO atletas (torneio_id, nome, entidade, whatsapp, status) VALUES (?, ?, ?, ?, 'PENDENTE')
    ''', (cfg["id"], nome.strip().upper(), entidade_limpa, whatsapp.strip()))
    db.commit()
    return RedirectResponse(url="/admin-painel/inscrever?sucesso=true", status_code=303)

@app.get("/login", response_class=HTMLResponse)
@app.get("/admin-painel/login", response_class=HTMLResponse)
def tela_login(request: Request, erro: str = None):
    html_content = f"""
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8"><title>Acesso Restrito</title>
        <style>
            body {{ background: #121212; color: #fff; font-family: sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }}
            .box {{ background: #1e1e1e; padding: 30px; border-radius: 8px; border: 1px solid #333; width: 300px; text-align: center; }}
            input {{ width: 100%; padding: 10px; margin: 15px 0; border: 1px solid #444; background: #2a2a2a; color: #fff; border-radius: 4px; box-sizing: border-box; }}
            button {{ background: #d4af37; color: #000; font-weight: bold; border: none; padding: 10px; width: 100%; border-radius: 4px; cursor: pointer; }}
        </style>
    </head>
    <body>
        <div class="box">
            <h2>🔑 Área do Administrador</h2>
            {"<p style='color:red;'>Chave incorreta!</p>" if erro else ""}
            <form action="/admin-painel/login" method="POST">
                <input type="password" name="chave" placeholder="Digite a chave de acesso" required autofocus>
                <button type="submit">Entrar no Sistema</button>
            </form>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.post("/login")
@app.post("/admin-painel/login")
def processar_login(chave: str = Form(...)):
    if chave == ADMIN_PASSWORD:
        response = RedirectResponse(url="/admin-painel/admin/inscricoes", status_code=303)
        response.set_cookie(key="admin_token", value=chave, httponly=True)
        return response
    return RedirectResponse(url="/admin-painel/login?erro=1", status_code=303)

@app.get("/logout")
@app.get("/admin-painel/logout")
def processar_logout():
    response = RedirectResponse(url="/admin-painel/login", status_code=303)
    response.delete_cookie("admin_token")
    return response

@app.get("/api/cronometro")
@app.get("/admin-painel/api/cronometro")
def api_cronometro(db: sqlite3.Connection = Depends(get_db)):
    cfg = atualizar_e_obter_cronometro(db)
    return JSONResponse({"tempo_restante": cfg["crono_tempo_restante_seg"], "ativo": cfg["crono_ativo"]})

@app.post("/admin/cronometro/controle")
@app.post("/admin-painel/admin/cronometro/controle")
def controle_cronometro(acao: str = Form(...), db: sqlite3.Connection = Depends(get_db), auth: bool = Depends(verificar_admin)):
    cursor = db.cursor()
    cfg = obter_torneio_ativo(cursor)
    
    if cfg["fase_torneio"] == "INSCRICAO":
        return RedirectResponse(url="/admin-painel/admin/inscricoes?erro=torneio_nao_iniciado", status_code=303)

    if acao == "iniciar" and cfg["crono_ativo"] == 0 and cfg["crono_tempo_restante_seg"] > 0:
        cursor.execute("UPDATE torneios SET crono_ativo = 1, crono_ultimo_clique = ? WHERE id = ?", (time.time(), cfg["id"]))
    elif acao == "pausar" and cfg["crono_ativo"] == 1:
        agora = time.time()
        decorrido = int(agora - cfg["crono_ultimo_clique"])
        novo_tempo = max(0, cfg["crono_tempo_restante_seg"] - decorrido)
        cursor.execute("UPDATE torneios SET crono_ativo = 0, crono_tempo_restante_seg = ? WHERE id = ?", (novo_tempo, cfg["id"]))
    elif acao == "reiniciar":
        cursor.execute("UPDATE torneios SET crono_ativo = 0, crono_tempo_restante_seg = 3000 WHERE id = ?", (cfg["id"],))
    db.commit()
    return RedirectResponse(url="/admin-painel/admin/jogos", status_code=303)

@app.get("/admin/inscricoes")
@app.get("/admin-painel/admin/inscricoes")
def aba_inscricoes(request: Request, db: sqlite3.Connection = Depends(get_db), auth: bool = Depends(verificar_admin)):
    cfg = atualizar_e_obter_cronometro(db)
    cursor = db.cursor()
    cursor.execute("SELECT * FROM atletas WHERE status = 'PENDENTE' AND torneio_id = ? ORDER BY id DESC", (cfg["id"],))
    pendentes = cursor.fetchall()
    cursor.execute("SELECT * FROM atletas WHERE status = 'APROVADO' AND torneio_id = ? ORDER BY nome ASC", (cfg["id"],))
    oficiais = cursor.fetchall()
    total_arrecadado = len(oficiais) * cfg['taxa_inscricao']
    
    return templates.TemplateResponse(
        request=request, name="admin_inscricoes.html", 
        context={"config": cfg, "pendentes": pendentes, "oficiais": oficiais, "total_arrecadado": str(total_arrecadado), "aba_ativa": "inscricoes"}
    )

@app.post("/admin/salvar-configuracoes")
@app.post("/admin-painel/admin/salvar-configuracoes")
def salvar_configuracoes(nome_torneio: str = Form(...), max_rodadas: int = Form(...), tempo_minutos: int = Form(...), db: sqlite3.Connection = Depends(get_db), auth: bool = Depends(verificar_admin)):
    cursor = db.cursor()
    cfg = obter_torneio_ativo(cursor)
    if cfg["fase_torneio"] != "INSCRICAO":
         return RedirectResponse(url="/admin-painel/admin/inscricoes?erro=torneio_ja_iniciado", status_code=303)
    total_seg = tempo_minutos * 60
    cursor.execute("UPDATE torneios SET nome_torneio = ?, max_rodadas_classificatoria = ?, crono_tempo_restante_seg = ? WHERE id = ?", 
                   (nome_torneio.strip(), max_rodadas, total_seg, cfg["id"]))
    db.commit()
    return RedirectResponse(url="/admin-painel/admin/inscricoes", status_code=303)

@app.post("/admin/iniciar-torneio")
@app.post("/admin-painel/admin/iniciar-torneio")
def iniciar_torneio_e_gerar_r1(db: sqlite3.Connection = Depends(get_db), auth: bool = Depends(verificar_admin)):
    cursor = db.cursor()
    cfg = obter_torneio_ativo(cursor)
    if cfg["fase_torneio"] != "INSCRICAO":
        return RedirectResponse(url="/admin-painel/admin/jogos", status_code=303)
        
    cursor.execute("SELECT COUNT(*) FROM atletas WHERE status = 'APROVADO' AND torneio_id = ?", (cfg["id"],))
    if cursor.fetchone()[0] < 2:
        return RedirectResponse(url="/admin-painel/admin/inscricoes?erro=jogadores_insuficientes", status_code=303)

    cursor.execute("UPDATE torneios SET fase_torneio = 'CLASSIFICATORIA' WHERE id = ?", (cfg["id"],))
    db.commit()
    return RedirectResponse(url="/admin-painel/admin/jogos", status_code=303)

@app.get("/admin/jogos")
@app.get("/admin-painel/admin/jogos")
def aba_jogos(request: Request, db: sqlite3.Connection = Depends(get_db), auth: bool = Depends(verificar_admin)):
    cfg = atualizar_e_obter_cronometro(db)
    
    if cfg["fase_torneio"] == "INSCRICAO":
        return RedirectResponse(url="/admin-painel/admin/inscricoes?erro=inicie_o_torneio", status_code=303)

    cursor = db.cursor()
    cursor.execute("SELECT rodada FROM confrontos WHERE torneio_id = ? ORDER BY id DESC LIMIT 1", (cfg["id"],))
    row_r = cursor.fetchone()
    rodada_atual = row_r["rodada"] if row_r else 1
    
    cursor.execute("SELECT * FROM confrontos WHERE rodada = ? AND torneio_id = ? ORDER BY mesa ASC", (rodada_atual, cfg["id"]))
    confrontos = cursor.fetchall()
    
    cursor.execute("SELECT COUNT(*) FROM confrontos WHERE rodada = ? AND torneio_id = ? AND vencedor_id IS NULL", (rodada_atual, cfg["id"]))
    rodada_concluida = cursor.fetchone()[0] == 0 if confrontos else False

    mins = cfg["crono_tempo_restante_seg"] // 60
    segs = cfg["crono_tempo_restante_seg"] % 60
    tempo_formatado = f"{mins:02d}:{segs:02d}"

    return templates.TemplateResponse(
        request=request, name="admin_jogos.html", 
        context={"config": cfg, "rodada": rodada_atual, "confrontos": confrontos, "rodada_concluida": rodada_concluida, "tempo_formatado": tempo_formatado, "aba_ativa": "jogos"}
    )

@app.post("/admin/gerar-rodada")
@app.post("/admin-painel/admin/gerar-rodada")
def gerar_rodada_admin(db: sqlite3.Connection = Depends(get_db), auth: bool = Depends(verificar_admin)):
    cursor = db.cursor()
    cfg = obter_torneio_ativo(cursor)
    if cfg["fase_torneio"] == "INSCRICAO":
        return RedirectResponse(url="/admin-painel/admin/inscricoes?erro=inicie_o_torneio", status_code=303)

    cursor.execute("SELECT COALESCE(MAX(rodada), 0) FROM confrontos WHERE rodada > 0 AND torneio_id = ?", (cfg["id"],))
    rodada_atual = cursor.fetchone()[0]
    proxima_rodada = rodada_atual + 1
    
    if rodada_atual > 0:
        cursor.execute("SELECT COUNT(*) FROM confrontos WHERE rodada = ? AND torneio_id = ? AND vencedor_id IS NULL", (rodada_atual, cfg["id"]))
        if cursor.fetchone()[0] > 0:
            return RedirectResponse(url="/admin-painel/admin/jogos?erro=jogos_pendentes", status_code=303)

    if proxima_rodada > cfg["max_rodadas_classificatoria"]:
        return RedirectResponse(url="/admin-painel/admin/classificacao?aviso=fim_da_classificatoria", status_code=303)
        
    cursor.execute("SELECT id, nome, entidade FROM atletas WHERE status = 'APROVADO' AND torneio_id = ?", (cfg["id"],))
    atletas_lista = [dict(row) for row in cursor.fetchall()]
    if len(atletas_lista) < 2:
        return RedirectResponse(url="/admin-painel/admin/inscricoes?erro=jogadores_insuficientes", status_code=303)
        
    cursor.execute("SELECT atleta1_id, atleta2_id FROM confrontos WHERE atleta2_id IS NOT NULL AND rodada > 0 AND torneio_id = ?", (cfg["id"],))
    historico = {tuple(sorted((r["atleta1_id"], r["atleta2_id"]))) for r in cursor.fetchall()}
        
    sucesso = False
    parceiros_finais = []
    atleta_folga = None
    
    for tentativa in range(1000):
        copia_atletas = atletas_lista.copy()
        random.shuffle(copia_atletas)
        propostos = []
        valido = True
        
        while len(copia_atletas) >= 2:
            a1 = copia_atletas[0]
            parceiro_encontrado = None
            for i in range(1, len(copia_atletas)):
                potencial_a2 = copia_atletas[i]
                ja_jogaram = tuple(sorted((a1["id"], potencial_a2["id"]))) in historico
                mesma_entidade = a1["entidade"] == potencial_a2["entidade"]
                
                if tentativa < 500:
                    if not ja_jogaram and not mesma_entidade:
                        parceiro_encontrado = potencial_a2
                        break
                else:
                    if not ja_jogaram:
                        parceiro_encontrado = potencial_a2
                        break
            if parceiro_encontrado:
                copia_atletas.remove(a1)
                copia_atletas.remove(parceiro_encontrado)
                propostos.append((a1, parceiro_encontrado))
            else:
                valido = False
                break
        if valido:
            if copia_atletas: atleta_folga = copia_atletas[0]
            parceiros_finais = propostos
            sucesso = True
            break
            
    if not sucesso:
        copia_atletas = atletas_lista.copy()
        random.shuffle(copia_atletas)
        parceiros_finais = []
        while len(copia_atletas) >= 2:
            parceiros_finais.append((copia_atletas.pop(0), copia_atletas.pop(0)))
        atleta_folga = copia_atletas[0] if copia_atletas else None

    mesa = 1
    for a1, a2 in parceiros_finais:
        cursor.execute('INSERT INTO confrontos (torneio_id, rodada, mesa, atleta1_id, atleta2_id, atleta1_nome, atleta2_nome) VALUES (?, ?, ?, ?, ?, ?, ?)',
                       (cfg["id"], proxima_rodada, mesa, a1['id'], a2['id'], a1['nome'], a2['nome']))
        mesa += 1
    
    if atleta_folga:
        cursor.execute("""
            INSERT INTO confrontos (torneio_id, rodada, mesa, atleta1_id, atleta2_id, atleta1_nome, atleta2_nome, tipo_placar, sets1, sets2, tentos1, tentos2, vencedor_id) 
            VALUES (?, ?, ?, ?, NULL, ?, 'FOLGA - GANHOU PONTOS', '2x0', 3, 0, 72, 0, ?)
        """, (cfg["id"], proxima_rodada, mesa, atleta_folga['id'], atleta_folga['nome'], atleta_folga['id']))
                            
    cursor.execute("UPDATE torneios SET crono_ativo = 0, crono_tempo_restante_seg = 3000 WHERE id = ?", (cfg["id"],))
    
    db.commit()
    return RedirectResponse(url="/admin-painel/admin/jogos", status_code=303)

@app.post("/admin/disparar-matamata")
@app.post("/admin-painel/admin/disparar-matamata")
def disparar_matamata(corte: int = Form(...), db: sqlite3.Connection = Depends(get_db), auth: bool = Depends(verificar_admin)):
    cursor = db.cursor()
    cfg = obter_torneio_ativo(cursor)
    cursor.execute("SELECT COALESCE(MAX(rodada), 0) FROM confrontos WHERE rodada > 0 AND torneio_id = ?", (cfg["id"],))
    r_atual = cursor.fetchone()[0]
    if r_atual > 0:
        cursor.execute("SELECT COUNT(*) FROM confrontos WHERE rodada = ? AND torneio_id = ? AND vencedor_id IS NULL", (r_atual, cfg["id"]))
        if cursor.fetchone()[0] > 0:
            return RedirectResponse(url="/admin-painel/admin/classificacao?erro=conclua_rodada_atual", status_code=303)

    ranking = obter_ranking_fase_classificatoria(cursor, cfg["id"])
    if len(ranking) < corte:
        return RedirectResponse(url="/admin-painel/admin/classificacao?erro=atletas_insuficientes_para_corte", status_code=303)

    classificados = ranking[:corte]
    cursor.execute("UPDATE torneios SET fase_torneio = 'MATA_MATA' WHERE id = ?", (cfg["id"],))
    
    if corte == 16: fase_id = -1
    elif corte == 8: fase_id = -2
    elif corte == 4: fase_id = -3
    else: fase_id = -2

    confrontos_fase = []
    if corte == 8:
        confrontos_fase = [
            (classificados[0], classificados[7]), (classificados[3], classificados[4]),
            (classificados[1], classificados[6]), (classificados[2], classificados[5])
        ]
    elif corte == 16:
        confrontos_fase = [
            (classificados[0], classificados[15]), (classificados[7], classificados[8]),
            (classificados[3], classificados[12]), (classificados[4], classificados[11]),
            (classificados[1], classificados[14]), (classificados[6], classificados[9]),
            (classificados[2], classificados[13]), (classificados[5], classificados[10])
        ]
    elif corte == 4:
        confrontos_fase = [
            (classificados[0], classificados[3]), (classificados[1], classificados[2])
        ]

    for idx, (a1, a2) in enumerate(confrontos_fase, start=1):
        cursor.execute('''
            INSERT INTO confrontos (torneio_id, rodada, mesa, atleta1_id, atleta2_id, atleta1_nome, atleta2_nome) VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (cfg["id"], fase_id, idx, a1["id"], a2["id"], a1["nome"], a2["nome"]))
        
    cursor.execute("UPDATE torneios SET crono_ativo = 0, crono_tempo_restante_seg = 3000 WHERE id = ?", (cfg["id"],))
        
    db.commit()
    return RedirectResponse(url="/admin-painel/admin/jogos", status_code=303)

@app.post("/admin/avancar-matamata")
@app.post("/admin-painel/admin/avancar-matamata")
def avancar_matamata(db: sqlite3.Connection = Depends(get_db), auth: bool = Depends(verificar_admin)):
    cursor = db.cursor()
    cfg = obter_torneio_ativo(cursor)
    cursor.execute("SELECT rodada FROM confrontos WHERE torneio_id = ? ORDER BY id DESC LIMIT 1", (cfg["id"],))
    row_f = cursor.fetchone()
    if not row_f:
        return RedirectResponse(url="/admin-painel/admin/jogos?erro=nenhum_jogo", status_code=303)
        
    fase_atual = row_f["rodada"]
    
    cursor.execute("SELECT COUNT(*) FROM confrontos WHERE rodada = ? AND torneio_id = ? AND vencedor_id IS NULL", (fase_atual, cfg["id"]))
    if cursor.fetchone()[0] > 0:
        return RedirectResponse(url="/admin-painel/admin/jogos?erro=jogos_eliminatorios_pendentes", status_code=303)
        
    cursor.execute("SELECT * FROM confrontos WHERE rodada = ? AND torneio_id = ? ORDER BY mesa ASC", (fase_atual, cfg["id"]))
    jogos_concluidos = cursor.fetchall()
    
    if fase_atual == -4:
        return RedirectResponse(url="/admin-painel/admin/podio", status_code=303)

    cursor.execute("UPDATE torneios SET crono_ativo = 0, crono_tempo_restante_seg = 3000 WHERE id = ?", (cfg["id"],))

    proxima_fase = fase_atual - 1
    
    if fase_atual in [-1, -2]:
        nova_mesa = 1
        for i in range(0, len(jogos_concluidos), 2):
            j1 = jogos_concluidos[i]
            j2 = jogos_concluidos[i+1] if (i+1) < len(jogos_concluidos) else j1 
            
            v1_id = j1["vencedor_id"]
            v1_nome = j1["atleta1_nome"] if v1_id == j1["atleta1_id"] else j1["atleta2_nome"]
                
            v2_id = j2["vencedor_id"]
            v2_nome = j2["atleta1_nome"] if v2_id == j2["atleta1_id"] else j2["atleta2_nome"]
            
            cursor.execute('INSERT INTO confrontos (torneio_id, rodada, mesa, atleta1_id, atleta2_id, atleta1_nome, atleta2_nome) VALUES (?, ?, ?, ?, ?, ?, ?)',
                           (cfg["id"], proxima_fase, nova_mesa, v1_id, v2_id, v1_nome, v2_nome))
            nova_mesa += 1
            
    elif fase_atual == -3:
        if len(jogos_concluidos) < 2:
            return RedirectResponse(url="/admin-painel/admin/jogos?erro=semifinais_insuficientes", status_code=303)
            
        j1 = jogos_concluidos[0]
        j2 = jogos_concluidos[1]
        
        v1_id = j1["vencedor_id"]
        v2_id = j2["vencedor_id"]
        
        v1_nome = j1["atleta1_nome"] if v1_id == j1["atleta1_id"] else j1["atleta2_nome"]
        v2_nome = j2["atleta1_nome"] if v2_id == j2["atleta1_id"] else j2["atleta2_nome"]
        p1_id = j1["atleta2_id"] if v1_id == j1["atleta1_id"] else j1["atleta1_id"]
        p1_nome = j1["atleta2_nome"] if v1_id == j1["atleta1_id"] else j1["atleta1_nome"]
        p2_id = j2["atleta2_id"] if v2_id == j2["atleta1_id"] else j2["atleta1_id"]
        p2_nome = j2["atleta2_nome"] if v2_id == j2["atleta1_id"] else j2["atleta1_nome"]

        cursor.execute('INSERT INTO confrontos (torneio_id, rodada, mesa, atleta1_id, atleta2_id, atleta1_nome, atleta2_nome) VALUES (?, -4, 1, ?, ?, ?, ?)', (cfg["id"], v1_id, v2_id, v1_nome, v2_nome))
        cursor.execute('INSERT INTO confrontos (torneio_id, rodada, mesa, atleta1_id, atleta2_id, atleta1_nome, atleta2_nome) VALUES (?, -4, 2, ?, ?, ?, ?)', (cfg["id"], p1_id, p2_id, p1_nome, p2_nome))
        
    db.commit()
    return RedirectResponse(url="/admin-painel/admin/jogos", status_code=303)

def aplicar_salvamento_placar(cursor, confronto_id, vencedor_id, tipo_placar, tentos1, tentos2, flores1, flores2):
    cursor.execute("SELECT atleta1_id, atleta2_id FROM confrontos WHERE id = ?", (confronto_id,))
    conf = cursor.fetchone()
    id1, id2 = conf["atleta1_id"], conf["atleta2_id"]
    
    if tipo_placar == "2x0":
        if vencedor_id == id1:
            if tentos1 != 72 or tentos2 > 46:
                raise HTTPException(status_code=400, detail="Para 2x0, o vencedor deve ter exatamente 72 tentos e o perdedor no máximo 46.")
        elif vencedor_id == id2:
            if tentos2 != 72 or tentos1 > 46:
                raise HTTPException(status_code=400, detail="Para 2x0, o vencedor deve ter exatamente 72 tentos e o perdedor no máximo 46.")
    elif tipo_placar == "2x1":
        if vencedor_id == id1:
            if tentos1 < 48 or tentos2 < 24:
                raise HTTPException(status_code=400, detail="Para 2x1, o vencedor precisa de no mínimo 48 tentos e o perdedor no mínimo 24.")
        elif vencedor_id == id2:
            if tentos2 < 48 or tentos1 < 24:
                raise HTTPException(status_code=400, detail="Para 2x1, o vencedor precisa de no mínimo 48 tentos e o perdedor no mínimo 24.")

    s1 = (3 if tipo_placar == "2x0" else 2) if vencedor_id == id1 else (0 if tipo_placar == "2x0" else 1)
    s2 = (3 if tipo_placar == "2x0" else 2) if vencedor_id == id2 else (0 if tipo_placar == "2x0" else 1)
    t1 = 72 if (tipo_placar == "2x0" and vencedor_id == id1) else tentos1
    t2 = 72 if (tipo_placar == "2x0" and vencedor_id == id2) else tentos2

    cursor.execute('UPDATE confrontos SET tipo_placar = ?, vencedor_id = ?, sets1 = ?, sets2 = ?, tentos1 = ?, tentos2 = ?, flores1 = ?, flores2 = ? WHERE id = ?',
                   (tipo_placar, vencedor_id, s1, s2, t1, t2, flores1, flores2, confronto_id))

@app.post("/admin/salvar-placar")
@app.post("/admin-painel/admin/salvar-placar")
def salvar_placar(confronto_id: int = Form(...), vencedor_id: int = Form(...), tipo_placar: str = Form(...), tentos1: int = Form(...), tentos2: int = Form(...), flores1: int = Form(0), flores2: int = Form(0), db: sqlite3.Connection = Depends(get_db), auth: bool = Depends(verificar_admin)):
    cursor = db.cursor()
    try:
        aplicar_salvamento_placar(cursor, confronto_id, vencedor_id, tipo_placar, tentos1, tentos2, flores1, flores2)
    except HTTPException as e:
        return JSONResponse(status_code=e.status_code, content={"erro": e.detail})
    db.commit()
    return RedirectResponse(url="/admin-painel/admin/jogos", status_code=303)

@app.get("/admin/classificacao")
@app.get("/admin-painel/admin/classificacao")
def aba_classificacao_e_auditoria(request: Request, rodada_filtro: int = None, db: sqlite3.Connection = Depends(get_db), auth: bool = Depends(verificar_admin)):
    cfg = atualizar_e_obter_cronometro(db)
    
    if cfg["fase_torneio"] == "INSCRICAO":
        return RedirectResponse(url="/admin-painel/admin/inscricoes?erro=inicie_o_torneio", status_code=303)

    cursor = db.cursor()
    lista_classificacao = obter_ranking_fase_classificatoria(cursor, cfg["id"])

    cursor.execute("SELECT DISTINCT rodada FROM confrontos WHERE torneio_id = ? ORDER BY rodada DESC", (cfg["id"],))
    todas_rodadas = [r["rodada"] for r in cursor.fetchall()]
    
    rodada_selecionada = rodada_filtro if rodada_filtro is not None else (todas_rodadas[0] if todas_rodadas else 1)
    cursor.execute("SELECT * FROM confrontos WHERE rodada = ? AND torneio_id = ? ORDER BY mesa ASC", (rodada_selecionada, cfg["id"]))
    confrontos_auditoria = cursor.fetchall()

    return templates.TemplateResponse(
        request=request, name="admin_classificacao.html",
        context={"config": cfg, "classificacao": lista_classificacao, "todas_rodadas": todas_rodadas, "rodada_selecionada": rodada_selecionada, "confrontos_auditoria": confrontos_auditoria, "aba_ativa": "classificacao"}
    )

@app.post("/admin/auditoria/corrigir")
@app.post("/admin-painel/admin/auditoria/corrigir")
def corrigir_placar_auditoria(confronto_id: int = Form(...), vencedor_id: int = Form(...), tipo_placar: str = Form(...), tentos1: int = Form(...), tentos2: int = Form(...), flores1: int = Form(0), flores2: int = Form(0), rodada_retorno: int = Form(...), db: sqlite3.Connection = Depends(get_db), auth: bool = Depends(verificar_admin)):
    cursor = db.cursor()
    try:
        aplicar_salvamento_placar(cursor, confronto_id, vencedor_id, tipo_placar, tentos1, tentos2, flores1, flores2)
    except HTTPException as e:
        return JSONResponse(status_code=e.status_code, content={"erro": e.detail})
    db.commit()
    return RedirectResponse(url=f"/admin-painel/admin/classificacao?rodada_filtro={rodada_retorno}", status_code=303)

@app.get("/admin/podio")
@app.get("/admin-painel/admin/podio")
def exibir_podio(request: Request, db: sqlite3.Connection = Depends(get_db), auth: bool = Depends(verificar_admin)):
    cfg = atualizar_e_obter_cronometro(db)
    
    if cfg["fase_torneio"] == "INSCRICAO":
        return RedirectResponse(url="/admin-painel/admin/inscricoes?erro=inicie_o_torneio", status_code=303)

    cursor = db.cursor()
    cursor.execute("SELECT COUNT(*) FROM confrontos WHERE rodada = -4 AND torneio_id = ? AND vencedor_id IS NULL", (cfg["id"],))
    if cursor.fetchone()[0] > 0:
        return RedirectResponse(url="/admin-painel/admin/jogos?erro=finais_nao_concluidas", status_code=303)
        
    cursor.execute("SELECT * FROM confrontos WHERE rodada = -4 AND mesa = 1 AND torneio_id = ?", (cfg["id"],))
    jogo_final = cursor.fetchone()
    cursor.execute("SELECT * FROM confrontos WHERE rodada = -4 AND mesa = 2 AND torneio_id = ?", (cfg["id"],))
    jogo_terceiro = cursor.fetchone()

    if not jogo_final or not jogo_terceiro:
        return RedirectResponse(url="/admin-painel/admin/jogos?erro=finais_nao_geradas", status_code=303)

    campeao = jogo_final["atleta1_nome"] if jogo_final["vencedor_id"] == jogo_final["atleta1_id"] else jogo_final["atleta2_nome"]
    vice = jogo_final["atleta2_nome"] if jogo_final["vencedor_id"] == jogo_final["atleta1_id"] else jogo_final["atleta1_nome"]
    
    third_place = jogo_terceiro["atleta1_nome"] if jogo_terceiro["vencedor_id"] == jogo_terceiro["atleta1_id"] else jogo_terceiro["atleta2_nome"]
    fourth_place = jogo_terceiro["atleta2_nome"] if jogo_terceiro["vencedor_id"] == jogo_terceiro["atleta1_id"] else jogo_terceiro["atleta1_nome"]

    cursor.execute("SELECT id, nome FROM atletas WHERE status = 'APROVADO' AND torneio_id = ?", (cfg["id"],))
    atletas = cursor.fetchall()
    
    rei_nome = "Nenhum"
    max_flores = 0
    for atl in atletas:
        a_id = atl["id"]
        cursor.execute("SELECT COALESCE(SUM(flores1), 0) FROM confrontos WHERE atleta1_id = ? AND torneio_id = ?", (a_id, cfg["id"]))
        f1 = cursor.fetchone()[0]
        cursor.execute("SELECT COALESCE(SUM(flores2), 0) FROM confrontos WHERE atleta2_id = ? AND torneio_id = ?", (a_id, cfg["id"]))
        f2 = cursor.fetchone()[0]
            
        total_f = f1 + f2
        if total_f > max_flores:
            max_flores = total_f
            rei_nome = atl["nome"]

    return templates.TemplateResponse(
        request=request, name="admin_podio.html",
        context={"config": cfg, "campeao": campeao, "vice": vice, "terceiro": third_place, "quarto": fourth_place, "rei_nome": rei_nome, "max_flores": max_flores, "aba_ativa": "podio"}
    )

@app.post("/admin/encerrar-e-salvar")
@app.post("/admin-painel/admin/encerrar-e-salvar")
def encerrar_e_salvar(campeao: str = Form(...), vice: str = Form(...), terceiro: str = Form(...), quarto: str = Form(...), rei: str = Form(...), flores: int = Form(...), db: sqlite3.Connection = Depends(get_db), auth: bool = Depends(verificar_admin)):
    cursor = db.cursor()
    cfg = obter_torneio_ativo(cursor)
    
    cursor.execute('INSERT INTO historico_campeoes (torneio_id, nome_torneio, campeao, vice, terceiro, quarto, rei_das_flores, qtd_flores) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                   (cfg["id"], cfg["nome_torneio"], campeao, vice, terceiro, quarto, rei, flores))
    
    cursor.execute("UPDATE torneios SET fase_torneio = 'CONCLUIDO', crono_ativo = 0 WHERE id = ?", (cfg["id"],))
    
    novo_nome_sugerido = f"Torneio de Truco Cego - Edição {cfg['id'] + 1}"
    cursor.execute('''
        INSERT INTO torneios (nome_torneio, taxa_inscricao, max_rodadas_classificatoria, crono_tempo_restante_seg, fase_torneio) 
        VALUES (?, ?, ?, ?, 'INSCRICAO')
    ''', (novo_nome_sugerido, cfg["taxa_inscricao"], cfg["max_rodadas_classificatoria"], 3000))
    
    db.commit()
    return RedirectResponse(url="/admin-painel/admin/historico?sucesso=torneio_imortalizado", status_code=303)

@app.get("/admin/historico")
@app.get("/admin-painel/admin/historico")
def exibir_historico(request: Request, db: sqlite3.Connection = Depends(get_db), auth: bool = Depends(verificar_admin)):
    cfg = atualizar_e_obter_cronometro(db)
    cursor = db.cursor()
    cursor.execute("SELECT * FROM historico_campeoes ORDER BY id DESC")
    galeria = cursor.fetchall()
    return templates.TemplateResponse(request=request, name="admin_historico.html", context={"config": cfg, "galeria": galeria, "aba_ativa": "historico"})

@app.post("/admin/reset-total-testes")
@app.post("/admin-painel/admin/reset-total-testes")
def reset_total_testes(db: sqlite3.Connection = Depends(get_db), auth: bool = Depends(verificar_admin)):
    cursor = db.cursor()
    
    cursor.execute("DROP TABLE IF EXISTS confrontos")
    cursor.execute("DROP TABLE IF EXISTS atletas")
    cursor.execute("DROP TABLE IF EXISTS historico_campeoes")
    cursor.execute("DROP TABLE IF EXISTS torneios")
    
    cursor.execute('''
        CREATE TABLE torneios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome_torneio TEXT DEFAULT 'Torneio de Truco Cego',
            fase_torneio TEXT DEFAULT 'INSCRICAO',
            max_rodadas_classificatoria INTEGER DEFAULT 5,
            taxa_inscricao REAL DEFAULT 5.00,
            crono_tempo_restante_seg INTEGER DEFAULT 3000,
            crono_ativo INTEGER DEFAULT 0,
            crono_ultimo_clique REAL DEFAULT 0.0
        )
    ''')
    
    cursor.execute('''
        INSERT INTO torneios (nome_torneio, taxa_inscricao, max_rodadas_classificatoria, crono_tempo_restante_seg, fase_torneio) 
        VALUES ('Torneio de Truco Cego', 5.00, 5, 3000, 'INSCRICAO')
    ''')
    
    cursor.execute('''
        CREATE TABLE atletas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            torneio_id INTEGER,
            nome TEXT NOT NULL,
            entidade TEXT DEFAULT 'AVULSO',
            whatsapp TEXT,
            status TEXT DEFAULT 'PENDENTE'
        )
    ''')

    cursor.execute('''
        CREATE TABLE confrontos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            torneio_id INTEGER,
            rodada INTEGER NOT NULL,
            mesa INTEGER NOT NULL,
            atleta1_id INTEGER,
            atleta2_id INTEGER,
            atleta1_nome TEXT,
            atleta2_nome TEXT,
            tipo_placar TEXT DEFAULT NULL,
            sets1 INTEGER DEFAULT 0,
            sets2 INTEGER DEFAULT 0,
            tentos1 INTEGER DEFAULT 0,
            tentos2 INTEGER DEFAULT 0,
            flores1 INTEGER DEFAULT 0,
            flores2 INTEGER DEFAULT 0,
            vencedor_id INTEGER
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE historico_campeoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            torneio_id INTEGER,
            nome_torneio TEXT,
            campeao TEXT,
            vice TEXT,
            terceiro TEXT,
            quarto TEXT,
            rei_das_flores TEXT,
            qtd_flores INTEGER
        )
    ''')
    
    db.commit()
    return RedirectResponse(url="/admin-painel/admin/inscricoes?sucesso=banco_zerado", status_code=303)

@app.post("/admin/cadastrar-direto")
@app.post("/admin-painel/admin/cadastrar-direto")
def cadastrar_direto_admin(nome: str = Form(...), entity: str = Form(None), entidade: str = Form("INDIVIDUAL"), db: sqlite3.Connection = Depends(get_db), auth: bool = Depends(verificar_admin)):
    ent_nome = entity if entity else entidade
    cursor = db.cursor()
    cfg = obter_torneio_ativo(cursor)
    entidade_limpa = ent_nome.strip().upper() if ent_nome else "AVULSO"
    
    cursor.execute("INSERT INTO atletas (torneio_id, nome, entidade, status) VALUES (?, ?, ?, 'APROVADO')", (cfg["id"], nome.strip().upper(), entidade_limpa))
    db.commit()
    return RedirectResponse(url="/admin-painel/admin/inscricoes", status_code=303)

@app.post("/admin/acao-atleta")
@app.post("/admin-painel/admin/acao-atleta")
def acao_atleta_admin(id_atleta: int = Form(...), acao: str = Form(...), db: sqlite3.Connection = Depends(get_db), auth: bool = Depends(verificar_admin)):
    cursor = db.cursor()
    if acao == "aprovar":
        cursor.execute("UPDATE atletas SET status = 'APROVADO' WHERE id = ?", (id_atleta,))
    elif acao in ["recusar", "excluir"]:
        cursor.execute("DELETE FROM atletas WHERE id = ?", (id_atleta,))
    db.commit()
    return RedirectResponse(url="/admin-painel/admin/inscricoes", status_code=303)

@app.get("/telao", response_class=HTMLResponse)
def pagina_telao_publico(request: Request, db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    cfg = obter_torneio_ativo(cursor)
    cursor.execute("SELECT rodada FROM confrontos WHERE torneio_id = ? ORDER BY id DESC LIMIT 1", (cfg["id"],))
    row_r = cursor.fetchone()
    rodada_atual = row_r["rodada"] if row_r else 1
    return templates.TemplateResponse(request=request, name="telao.html", context={"config": cfg, "rodada": rodada_atual})

@app.get("/api/publico/dados")
@app.get("/admin-painel/api/publico/dados")
def api_dados_publicos_telao(db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    cfg = obter_torneio_ativo(cursor)
    
    cursor.execute("SELECT rodada FROM confrontos WHERE torneio_id = ? ORDER BY id DESC LIMIT 1", (cfg["id"],))
    row_r = cursor.fetchone()
    rodada_atual = row_r["rodada"] if row_r else 1
    
    cursor.execute("SELECT * FROM confrontos WHERE rodada = ? AND torneio_id = ? ORDER BY mesa ASC", (rodada_atual, cfg["id"]))
    confrontos = [dict(row) for row in cursor.fetchall()]
    
    ranking = obter_ranking_fase_classificatoria(cursor, cfg["id"])
    
    mins = cfg["crono_tempo_restante_seg"] // 60
    segs = cfg["crono_tempo_restante_seg"] % 60
    tempo_formatado = f"{mins:02d}:{segs:02d}"
    if cfg["crono_ativo"] == 1 and cfg["crono_tempo_restante_seg"] == 0:
        tempo_formatado = "AGORA TUDO É FALTA!"
        
    cursor.execute("SELECT * FROM historico_campeoes WHERE torneio_id = ?", (cfg["id"],))
    hist = cursor.fetchone()
    podio_dados = None
    
    if hist:
        podio_dados = {
            "primeiro": str(hist["campeao"]),
            "segundo": str(hist["vice"]),
            "terceiro": str(hist["terceiro"]),
            "quarto": str(hist["quarto"]),
            "rei": str(hist["rei_das_flores"]),
            "rei_nome": str(hist["rei_das_flores"]),
            "rei_flores": str(hist["rei_das_flores"]),
            "flores": int(hist["qtd_flores"]),
            "max_flores": int(hist["qtd_flores"])
        }
    else:
        cursor.execute("SELECT id, nome FROM atletas WHERE status = 'APROVADO' AND torneio_id = ?", (cfg["id"],))
        atletas = cursor.fetchall()
        
        rei_nome = "---"
        max_flores = 0
        for atl in atletas:
            a_id = atl["id"]
            cursor.execute("SELECT COALESCE(SUM(flores1), 0) FROM confrontos WHERE atleta1_id = ? AND torneio_id = ?", (a_id, cfg["id"]))
            f1 = cursor.fetchone()[0]
            cursor.execute("SELECT COALESCE(SUM(flores2), 0) FROM confrontos WHERE atleta2_id = ? AND torneio_id = ?", (a_id, cfg["id"]))
            f2 = cursor.fetchone()[0]
            
            total_f = f1 + f2
            if total_f > max_flores:
                max_flores = total_f
                rei_nome = str(atl["nome"]).strip()
        
        podio_dados = {
            "primeiro": "---",
            "segundo": "---",
            "terceiro": "---",
            "quarto": "---",
            "rei": rei_nome,
            "rei_nome": rei_nome,
            "rei_flores": rei_nome,
            "flores": int(max_flores),
            "max_flores": int(max_flores)
        }

    nome_fase = f"{rodada_atual}ª Rodada"
    if rodada_atual == -1: nome_fase = "Oitavas de Final"
    elif rodada_atual == -2: nome_fase = "Quartas de Final"
    elif rodada_atual == -3: nome_fase = "Semifinal"
    elif rodada_atual == -4: nome_fase = "Grande Final"

    dados_retorno = {
        "fase_torneio": cfg["fase_torneio"],
        "nome_fase": nome_fase,
        "tempo": tempo_formatado,
        "crono_ativo": cfg["crono_ativo"],
        "rodada": rodada_atual,
        "confrontos": confrontos,
        "ranking": ranking,
        "podio": podio_dados
    }

    return JSONResponse(content=dados_retorno)

@app.get("/inscricao", response_class=HTMLResponse)
@app.get("/admin-painel/inscricao", response_class=HTMLResponse)
def pagina_inscricao_externa(request: Request, db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    cfg = obter_torneio_ativo(cursor)
    
    taxa_val = cfg["taxa_inscricao"] if cfg else 0.0
    taxa_formatada = f"{taxa_val:.2f}".replace('.', ',')
    
    return templates.TemplateResponse(
        request=request, 
        name="inscricao_atleta.html", 
        context={
            "config": cfg, 
            "config_taxa": taxa_formatada
        }
    )

@app.post("/inscrever")
@app.post("/inscricao/salvar")
@app.post("/admin-painel/inscrever")
@app.post("/admin-painel/inscricao/salvar")
async def salvar_inscricao_externa(
    nome: str = Form(...), 
    ctg: str = Form(None), 
    entidade: str = Form(None), 
    whatsapp: str = Form(""), 
    comprovante: UploadFile = File(None),
    db: sqlite3.Connection = Depends(get_db)
):
    cursor = db.cursor()
    cfg = obter_torneio_ativo(cursor)
    
    ent_final = entidade if entidade else ctg
    entidade_limpa = ent_final.strip().upper() if (ent_final and ent_final.strip()) else "AVULSO"
    
    cursor.execute('''
        INSERT INTO atletas (torneio_id, nome, entity, status) -- Corrigido para a tabela estruturada
        VALUES (?, ?, ?, 'PENDENTE')
    ''', (cfg["id"], nome.strip().upper(), entidade_limpa))
    db.commit()
    
    return RedirectResponse(url="/admin-painel/inscricao?sucesso=true", status_code=303)

@app.exception_handler(404)
async def redirecionar_links_antigos(request: Request, exc: Exception):
    url_path = request.url.path
    if url_path.startswith("/admin") or url_path == "/login" or url_path == "/logout":
        return RedirectResponse(url=f"/admin-painel{url_path}", status_code=303)
    return HTMLResponse(content="Página não encontrada no Painel", status_code=404)