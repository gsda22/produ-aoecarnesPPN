import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import io
import os
import re

st.set_page_config(page_title="FAST", layout="wide")

# Estilo azul/vermelho simples
st.markdown(
    """
    <style>
    h1, h2, h3 { color: #0b5394; }
    .stButton>button { background-color: #c1121f; color: white; }
    .stButton>button:hover { background-color: #a10f19; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ===== Banco =====
def init_db():
    try:
        with sqlite3.connect('produtos.db', check_same_thread=False) as conn:
            cursor = conn.cursor()
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS produtos (
                codigo TEXT PRIMARY KEY,
                descricao TEXT
            )
            """)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS lancamentos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data TEXT,
                codigo TEXT,
                descricao TEXT,
                quantidade REAL,
                unidade TEXT,
                motivo TEXT
            )
            """)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS transformacoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data TEXT,
                codigo_origem TEXT,
                descricao_origem TEXT,
                quantidade REAL,
                unidade TEXT,
                codigo_destino TEXT,
                descricao_destino TEXT
            )
            """)
            conn.commit()
            st.write("Banco de dados inicializado com sucesso.")
    except Exception as e:
        st.error(f"Erro ao inicializar o banco de dados: {e}")

# Inicializa o banco
init_db()

# ===== Funções =====
def buscar_descricao(codigo):
    try:
        with sqlite3.connect('produtos.db', check_same_thread=False) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT descricao FROM produtos WHERE codigo = ?", (codigo,))
            result = cursor.fetchone()
            return result[0] if result else ""
    except Exception as e:
        st.error(f"Erro ao buscar descrição: {e}")
        return ""

def cadastrar_produto(codigo, descricao):
    try:
        with sqlite3.connect('produtos.db', check_same_thread=False) as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT OR IGNORE INTO produtos (codigo, descricao) VALUES (?, ?)", (codigo, descricao))
            conn.commit()
            st.write(f"Produto {codigo} cadastrado com sucesso.")
    except Exception as e:
        st.error(f"Erro ao cadastrar produto: {e}")

def salvar_lancamento(data, codigo, descricao, qtd, unidade, motivo):
    try:
        with sqlite3.connect('produtos.db', check_same_thread=False) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO lancamentos (data, codigo, descricao, quantidade, unidade, motivo)
                VALUES (?, ?, ?, ?, ?, ?)""",
                (data, codigo, descricao, qtd, unidade, motivo))
            conn.commit()
            st.write(f"Lançamento salvo: {descricao}, {qtd} {unidade}, motivo: {motivo}")
    except Exception as e:
        st.error(f"Erro ao salvar lançamento: {e}")

def salvar_transformacao(data, cod_ori, desc_ori, qtd, unidade, cod_dest, desc_dest):
    try:
        with sqlite3.connect('produtos.db', check_same_thread=False) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO transformacoes (data, codigo_origem, descricao_origem, quantidade, unidade, codigo_destino, descricao_destino)
                VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (data, cod_ori, desc_ori, qtd, unidade, cod_dest, desc_dest))
            conn.commit()
            st.write(f"Transformação salva: {desc_ori} -> {desc_dest}, {qtd} {unidade}")
    except Exception as e:
        st.error(f"Erro ao salvar transformação: {e}")

# Função para avaliar expressões com soma e subtração
def avaliar_expressao(expressao):
    try:
        if not expressao or expressao.strip() == "":
            st.write(f"Entrada vazia detectada: '{expressao}'")
            return None
        expressao = expressao.replace(',', '.').strip()  # Substitui vírgula por ponto e remove espaços
        st.write(f"Expressão processada: '{expressao}'")
        
        # Verifica se é um número simples (ex.: "12.5" ou "10")
        if re.match(r'^\d*\.?\d*$', expressao):
            resultado = float(expressao)
        else:
            # Verifica se é uma expressão válida (ex.: "12+5-3")
            if not re.match(r'^[\d+\-().\s]+$', expressao):
                st.write(f"Expressão inválida, contém caracteres não permitidos: '{expressao}'")
                return None
            resultado = eval(expressao, {"__builtins__": {}}, {})
        
        resultado = float(resultado)
        if resultado <= 0:
            st.write(f"Resultado não positivo: {resultado}")
            return None
        st.write(f"Resultado calculado: {resultado}")
        return resultado
    except Exception as e:
        st.write(f"Erro ao avaliar expressão '{expressao}': {e}")
        return None

# Inicializa session_state para os campos se não existirem
for key in ["codigo_padaria", "descricao_padaria", "qtd_padaria", "unidade_padaria", "motivo_padaria",
            "codigo_transf_ori", "descricao_transf_ori", "qtd_transf", "unidade_transf",
            "codigo_transf_dest", "descricao_transf_dest",
            "qtd_padaria_raw", "qtd_transf_raw"]:
    if key not in st.session_state:
        if key in ["qtd_padaria", "qtd_transf"]:
            st.session_state[key] = 0.0
        elif key in ["unidade_padaria", "unidade_transf"]:
            st.session_state[key] = "kg"
        elif key == "motivo_padaria":
            st.session_state[key] = "Avaria"
        else:
            st.session_state[key] = ""

st.title("📦 FAST - Gestão de Lançamentos")

# Verifica permissões do arquivo produtos.db
if os.path.exists('produtos.db'):
    if not os.access('produtos.db', os.W_OK):
        st.error("O arquivo produtos.db não tem permissões de escrita. Ajuste as permissões com 'chmod 664 produtos.db' (Linux) ou verifique as permissões no Windows.")
else:
    st.warning("O arquivo produtos.db não existe. Ele será criado automaticamente ao salvar dados.")

abas = st.tabs(["🥖 Lançamentos Padaria", "🥩 Transformações de Carne", "📁 Base de Produtos", "📊 Relatórios"])

# ------ Aba 1: Padaria ------
with abas[0]:
    st.subheader("🥖 Lançamentos da Padaria")
    with st.form("form_padaria", clear_on_submit=True):
        codigo = st.text_input("Código do produto", value=st.session_state["codigo_padaria"], key="codigo_padaria")
        buscar = st.form_submit_button("🔍 Buscar")
        if buscar and codigo:
            desc = buscar_descricao(codigo)
            if desc:
                st.session_state["descricao_padaria"] = desc
                st.success("Produto encontrado.")
            else:
                st.warning("Produto não encontrado. Preencha a descrição para cadastrar.")
                st.session_state["descricao_padaria"] = ""

        descricao = st.text_input("Descrição", value=st.session_state["descricao_padaria"], key="descricao_padaria")
        
        qtd_raw = st.text_input(
            "Quantidade (pode usar somas, subtrações ou número, ex: 12+5-3 ou 12.5)",
            value=st.session_state.get("qtd_padaria_raw", ""),
            key="qtd_padaria_raw",
            placeholder="Ex: 12+5-3 ou 12.5"
        )
        qtd = avaliar_expressao(qtd_raw)
        if qtd is None:
            st.error("Quantidade inválida! Insira um número positivo ou uma expressão válida (ex.: '12+5-3' ou '12.5').")
        else:
            st.session_state["qtd_padaria"] = qtd
            st.write(f"Quantidade calculada: {qtd} {st.session_state['unidade_padaria']}")

        unidade = st.selectbox("Unidade", ["kg", "un"], index=["kg", "un"].index(st.session_state["unidade_padaria"]), key="unidade_padaria")
        motivo = st.selectbox("Motivo", ["Avaria", "Doação", "Refeitório", "Inventário"], index=["Avaria", "Doação", "Refeitório", "Inventário"].index(st.session_state["motivo_padaria"]), key="motivo_padaria")

        salvar = st.form_submit_button("✅ Salvar Lançamento")
        if salvar:
            qtd = avaliar_expressao(st.session_state["qtd_padaria_raw"])  # Revalida a quantidade
            if not codigo or not descricao:
                st.error("Preencha código e descrição!")
            elif qtd is None or qtd <= 0:
                st.error("Quantidade inválida! Insira um número positivo ou uma expressão válida (ex.: '12+5-3' ou '12.5').")
            else:
                try:
                    st.write(f"Tentando salvar: Código={codigo}, Descrição={descricao}, Quantidade={qtd}, Unidade={unidade}, Motivo={motivo}")
                    cadastrar_produto(codigo, descricao)
                    salvar_lancamento(datetime.today().strftime("%Y-%m-%d"), codigo, descricao, qtd, unidade, motivo)
                    st.success("Lançamento salvo com sucesso!")
                    # Verifica se o registro foi salvo
                    with sqlite3.connect('produtos.db', check_same_thread=False) as conn:
                        df_check = pd.read_sql_query("SELECT * FROM lancamentos WHERE codigo = ? ORDER BY id DESC LIMIT 1", conn, params=(codigo,))
                        if not df_check.empty:
                            st.write("Registro encontrado no banco:", df_check)
                        else:
                            st.warning("Registro não encontrado no banco após salvamento.")
                except Exception as e:
                    st.error(f"Erro ao salvar lançamento: {e}")

    # Consolidação agrupando descrição + motivo
    st.markdown("---")
    st.subheader("📈 Consolidado por Descrição e Motivo (Padaria)")
    with sqlite3.connect('produtos.db', check_same_thread=False) as conn:
        df_lanc_padaria = pd.read_sql_query("SELECT descricao, motivo, SUM(quantidade) AS total_quantidade FROM lancamentos GROUP BY descricao, motivo", conn)
    if not df_lanc_padaria.empty:
        st.dataframe(df_lanc_padaria)
    else:
        st.write("Nenhum lançamento encontrado.")

# ------ Aba 2: Transformações ------
with abas[1]:
    st.subheader("🥩 Transformações de Carne Bovina")
    with st.form("form_transformacoes", clear_on_submit=True):
        codigo_ori = st.text_input("Código origem", value=st.session_state["codigo_transf_ori"], key="codigo_transf_ori")
        buscar_ori = st.form_submit_button("🔍 Buscar Origem")
        if buscar_ori and codigo_ori:
            desc_ori = buscar_descricao(codigo_ori)
            if desc_ori:
                st.session_state["descricao_transf_ori"] = desc_ori
                st.success("Produto origem encontrado.")
            else:
                st.warning("Produto origem não encontrado. Preencha a descrição para cadastrar.")
                st.session_state["descricao_transf_ori"] = ""

        descricao_ori = st.text_input("Descrição origem", value=st.session_state["descricao_transf_ori"], key="descricao_transf_ori")

        qtd_raw = st.text_input(
            "Quantidade (pode usar somas, subtrações ou número, ex: 12+5-3 ou 12.5)",
            value=st.session_state.get("qtd_transf_raw", ""),
            key="qtd_transf_raw",
            placeholder="Ex: 12+5-3 ou 12.5"
        )
        qtd = avaliar_expressao(qtd_raw)
        if qtd is None:
            st.error("Quantidade inválida! Insira um número positivo ou uma expressão válida (ex.: '12+5-3' ou '12.5').")
        else:
            st.session_state["qtd_transf"] = qtd
            st.write(f"Quantidade calculada: {qtd} {st.session_state['unidade_transf']}")

        unidade = st.selectbox("Unidade", ["kg", "un"], index=["kg", "un"].index(st.session_state["unidade_transf"]), key="unidade_transf")

        codigo_dest = st.text_input("Código destino", value=st.session_state["codigo_transf_dest"], key="codigo_transf_dest")
        buscar_dest = st.form_submit_button("🔍 Buscar Destino")
        if buscar_dest and codigo_dest:
            desc_dest = buscar_descricao(codigo_dest)
            if desc_dest:
                st.session_state["descricao_transf_dest"] = desc_dest
                st.success("Produto destino encontrado.")
            else:
                st.warning("Produto destino não encontrado. Preencha a descrição para cadastrar.")
                st.session_state["descricao_transf_dest"] = ""

        descricao_dest = st.text_input("Descrição destino", value=st.session_state["descricao_transf_dest"], key="descricao_transf_dest")

        salvar = st.form_submit_button("✅ Salvar Transformação")
        if salvar:
            qtd = avaliar_expressao(st.session_state["qtd_transf_raw"])  # Revalida a quantidade
            if not codigo_ori or not descricao_ori or not codigo_dest or not descricao_dest:
                st.error("Preencha todos os campos!")
            elif qtd is None or qtd <= 0:
                st.error("Quantidade inválida! Insira um número positivo ou uma expressão válida (ex.: '12+5-3' ou '12.5').")
            else:
                try:
                    st.write(f"Tentando salvar: Origem={codigo_ori}, Destino={codigo_dest}, Quantidade={qtd}, Unidade={unidade}")
                    cadastrar_produto(codigo_ori, descricao_ori)
                    cadastrar_produto(codigo_dest, descricao_dest)
                    salvar_transformacao(datetime.today().strftime("%Y-%m-%d"), codigo_ori, descricao_ori, qtd, unidade, codigo_dest, descricao_dest)
                    st.success("Transformação salva com sucesso!")
                    # Verifica se o registro foi salvo
                    with sqlite3.connect('produtos.db', check_same_thread=False) as conn:
                        df_check = pd.read_sql_query("SELECT * FROM transformacoes WHERE codigo_origem = ? ORDER BY id DESC LIMIT 1", conn, params=(codigo_ori,))
                        if not df_check.empty:
                            st.write("Registro encontrado no banco:", df_check)
                        else:
                            st.warning("Registro não encontrado no banco após salvamento.")
                except Exception as e:
                    st.error(f"Erro ao salvar transformação: {e}")

# ------ Aba 3: Base de Produtos ------
with abas[2]:
    st.subheader("📁 Upload da Base de Produtos")
    uploaded_file = st.file_uploader("Faça upload do Excel com colunas 'codigo' e 'descricao'", type=['xlsx', 'xls'])
    if uploaded_file:
        try:
            df = pd.read_excel(uploaded_file)
            if 'codigo' in df.columns and 'descricao' in df.columns:
                with sqlite3.connect('produtos.db', check_same_thread=False) as conn:
                    df.to_sql('produtos', conn, if_exists='replace', index=False)
                    conn.commit()
                st.success("Base de produtos carregada e salva no banco com sucesso!")
            else:
                st.error("O arquivo deve conter as colunas 'codigo' e 'descricao'.")
        except Exception as e:
            st.error(f"Erro ao ler arquivo: {e}")

    st.write("Base atual de produtos:")
    with sqlite3.connect('produtos.db', check_same_thread=False) as conn:
        df_produtos = pd.read_sql_query("SELECT * FROM produtos ORDER BY codigo", conn)
    st.dataframe(df_produtos)

# ------ Aba 4: Relatórios ------
with abas[3]:
    st.subheader("📊 Relatórios de Lançamentos")
    with sqlite3.connect('produtos.db', check_same_thread=False) as conn:
        df_lanc = pd.read_sql_query("SELECT * FROM lancamentos ORDER BY data DESC", conn)
    st.dataframe(df_lanc)

    if not df_lanc.empty:
        # Depuração: Exibir dados brutos
        st.write("Dados brutos de lançamentos:", df_lanc)
        # Converter quantidade para float e substituir NaN por 0
        df_lanc['quantidade'] = pd.to_numeric(df_lanc['quantidade'], errors='coerce').fillna(0)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_lanc.to_excel(writer, sheet_name='Detalhado', index=False)
            total_motivo = df_lanc.groupby(['descricao', 'motivo'])['quantidade'].sum().reset_index()
            total_motivo.rename(columns={'quantidade': 'Quantidade Total'}, inplace=True)
            total_motivo.to_excel(writer, sheet_name='Total por Descrição e Motivo', index=False)
            # Depuração: Exibir total por descrição e motivo antes de salvar
            st.write("Total por Descrição e Motivo (antes do Excel):", total_motivo)
        processed_data = output.getvalue()

        st.download_button(
            label="📥 Baixar Excel dos lançamentos",
            data=processed_data,
            file_name="lancamentos_fast.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    st.subheader("📊 Relatórios de Transformações")
    with sqlite3.connect('produtos.db', check_same_thread=False) as conn:
        df_transf = pd.read_sql_query("SELECT * FROM transformacoes ORDER BY data DESC", conn)
    st.dataframe(df_transf)

    if not df_transf.empty:
        # Depuração: Exibir dados brutos
        st.write("Dados brutos de transformações:", df_transf)
        # Converter quantidade para float e substituir NaN por 0
        df_transf['quantidade'] = pd.to_numeric(df_transf['quantidade'], errors='coerce').fillna(0)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_transf.to_excel(writer, sheet_name='Detalhado', index=False)
            total_dest = df_transf.groupby(['descricao_destino', 'codigo_destino'])['quantidade'].sum().reset_index()
            total_dest.rename(columns={'quantidade': 'Quantidade Total'}, inplace=True)
            total_dest.to_excel(writer, sheet_name='Total por Descrição e Código Destino', index=False)
            # Depuração: Exibir total por descrição e código destino antes de salvar
            st.write("Total por Descrição e Código Destino (antes do Excel):", total_dest)
        processed_data = output.getvalue()

        st.download_button(
            label="📥 Baixar Excel das transformações",
            data=processed_data,
            file_name="transformacoes_fast.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )