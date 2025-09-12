import os
import io
import zipfile
from flask import Flask, render_template, request, send_file, flash

# --- Imports do ReportLab ---
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm, mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, SimpleDocTemplate
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.colors import black, blue

# --- Inicialização do Flask ---
app = Flask(__name__)
app.secret_key = 'sua-chave-secreta-muito-segura'

# --- LÓGICA COMPLETA DE GERAÇÃO DE PDF ---

def static_file_path(filename):
    return os.path.join(app.root_path, 'static', filename)

def obter_texto_citacao(dados, incluir_disponivel_em=True, titulo_override=None, subtitulo_override=None):
    nome_citacao = dados.get('nome_citacao', '').strip()
    autor_citacao = f"{nome_citacao.split(',')[0].upper()}, {nome_citacao.split(',', 1)[1].strip()}" if "," in nome_citacao else nome_citacao.upper()
    autor_citacao += "." if not autor_citacao.endswith('.') else ""
    titulo_str = (titulo_override if titulo_override is not None else dados.get('titulo', '')).strip()
    subtitulo_str = (subtitulo_override if subtitulo_override is not None else dados.get('subtitulo', '')).strip()
    titulo_formatado = f"<b>{titulo_str}</b>" + (f": {subtitulo_str}" if subtitulo_str else "") + "."
    nivel = dados.get('nivel', '')
    if "Tese" in nivel: tipo_trabalho = "Tese (Doutorado em Tecnologia Nuclear)"
    elif "Mestrado Profissional" in nivel: tipo_trabalho = "Dissertação (Mestrado Profissional em Tecnologia das Radiações em Ciências da Saúde)"
    else: tipo_trabalho = "Dissertação (Mestrado em Tecnologia Nuclear)"
    demais = f"{dados.get('ano', '')}. {dados.get('paginas', '')} p. {tipo_trabalho}."
    texto_base = f"{autor_citacao} {titulo_formatado} {demais}"
    if incluir_disponivel_em: texto_fixo = ' Instituto de Pesquisas Energéticas e Nucleares. São Paulo. Disponível em: <a href="http://repositorio.ipen.br/" color="blue"><u>http://repositorio.ipen.br/</u></a>. Acesso em: (data de consulta no formato: dia mês_abrev. ano).'
    else: texto_fixo = " Instituto de Pesquisas Energéticas e Nucleares - IPEN-CNEN/SP. São Paulo."
    return f"{texto_base}{texto_fixo}"

def gerar_capa(dados, buffer):
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    nivel = dados.get("nivel", "")
    cores = {"Mestrado Profissional": (129/255, 0/255, 64/255), "Mestrado": (30/255, 143/255, 113/255), "Tese": (52/255, 14/255, 113/255)}
    cor_faixas = next((cor for key, cor in cores.items() if key in nivel), cores["Tese"])
    c.setFillColorRGB(*cor_faixas)
    top_margin, f_fina, f_grossa, esp, f_comp = 16*mm, 2.7*mm, 4.8*mm, 1.2*mm, 78*mm
    y1, y2, y3 = height - top_margin - f_fina, height - top_margin - f_fina - esp - f_grossa, height - top_margin - f_fina - esp - f_grossa - esp - f_fina
    for y_pos in [y1, y3]: c.rect(0, y_pos, f_comp, f_fina, fill=1, stroke=0); c.rect(width - f_comp, y_pos, f_comp, f_fina, fill=1, stroke=0)
    c.rect(0, y2, f_comp, f_grossa, fill=1, stroke=0); c.rect(width - f_comp, y2, f_comp, f_grossa, fill=1, stroke=0)
    b_margin = 9*mm
    c.rect(0, b_margin, width, f_fina, fill=1, stroke=0)
    c.rect(0, b_margin + f_fina + esp, width, f_grossa, fill=1, stroke=0)
    c.rect(0, b_margin + f_fina + esp + f_grossa + esp, width, f_fina, fill=1, stroke=0)
    try:
        logo = ImageReader(static_file_path('ipen_logo_azul.jpg'))
        iw, ih = logo.getSize(); l_larg = 54*mm; l_alt = ih * (l_larg/iw)
        y_logo = y3 + (f_grossa + 2*f_fina + 2*esp - l_alt) / 2
        c.drawImage(logo, (width-l_larg)/2, y_logo, width=l_larg, height=l_alt, preserveAspectRatio=True, mask='auto')
    except Exception as e: print(f"Erro ao carregar o logo: {e}")
    c.setFillColorRGB(0,0,0)
    styles = getSampleStyleSheet()
    s_titulo = ParagraphStyle(name='Center', parent=styles['h1'], fontName='Helvetica-Bold', fontSize=12, leading=14, alignment=TA_CENTER)
    s_autor = ParagraphStyle(name='CenterAutor', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=12, leading=14, alignment=TA_CENTER)
    s_just = ParagraphStyle(name='Justify', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=12, leading=14, alignment=TA_JUSTIFY)
    s_orient = ParagraphStyle(name='LeftOrientador', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=12, leading=14, alignment=TA_LEFT)
    y = y3 - 20*mm
    c.setFont("Helvetica-Bold", 12)
    c.drawCentredString(width/2, y, "INSTITUTO DE PESQUISAS ENERGÉTICAS E NUCLEARES")
    y -= 0.5*cm
    c.drawCentredString(width/2, y, "Mestrado Profissional em Tecnologia das Radiações em Ciências da Saúde" if "Mestrado Profissional" in nivel else "Autarquia associada à Universidade de São Paulo")
    y -= 2.5*cm
    titulo_completo = dados.get('titulo','') + (f": {dados.get('subtitulo','')}" if dados.get('subtitulo') else "")
    p_titulo = Paragraph(titulo_completo, s_titulo)
    w, h = p_titulo.wrapOn(c, width-4*cm, y); p_titulo.drawOn(c, 2*cm, y-h); y -= h + 2*cm
    autor = f"{dados.get('nome_completo','')} {dados.get('sobrenome','')}".upper()
    p_autor = Paragraph(autor, s_autor)
    w, h = p_autor.wrapOn(c, width-4*cm, y); p_autor.drawOn(c, 2*cm, y-h); y -= h + 4.5*cm
    if "Mestrado Profissional" in nivel: t_final = f"Dissertação apresentada como parte dos requisitos para obtenção do Grau de Mestre Profissional em Tecnologia das Radiações em Ciências da Saúde na Área de {dados.get('area','')}"
    elif "Mestrado" in nivel: t_final = f"Dissertação apresentada como parte dos requisitos para obtenção do Grau de Mestre em Ciências na Área de Tecnologia Nuclear - {dados.get('area','')}"
    else: t_final = f"Tese apresentada como parte dos requisitos para obtenção do Grau de Doutor em Ciências na Área de Tecnologia Nuclear - {dados.get('area','')}"
    p_final = Paragraph(t_final, s_just)
    w, h = p_final.wrapOn(c, width/2-2*cm, y); p_final.drawOn(c, width/2, y-h); y -= h + 0.8*cm
    if dados.get("orientador"):
        p_label = Paragraph("Orientadora:" if "Profa" in dados.get("orientador_tipo") else "Orientador:", s_orient)
        w, h = p_label.wrapOn(c, width/2-2*cm, y); p_label.drawOn(c, width/2, y-h); y -= h + 0.1*cm
        p_nome = Paragraph(f"{dados.get('orientador_tipo')} {dados.get('orientador')}", s_orient)
        w, h = p_nome.wrapOn(c, width/2-2*cm, y); p_nome.drawOn(c, width/2, y-h); y -= h + 0.8*cm
    if dados.get("coorientador"):
        p_label_co = Paragraph("Coorientadora:" if "Profa" in dados.get("coorientador_tipo") else "Coorientador:", s_orient)
        w, h = p_label_co.wrapOn(c, width/2-2*cm, y); p_label_co.drawOn(c, width/2, y-h); y -= h + 0.1*cm
        p_nome_co = Paragraph(f"{dados.get('coorientador_tipo')} {dados.get('coorientador')}", s_orient)
        w, h = p_nome_co.wrapOn(c, width/2-2*cm, y); p_nome_co.drawOn(c, width/2, y-h)
    c.setFont("Helvetica-Bold", 12)
    c.drawCentredString(width/2, 5.5*cm, "São Paulo"); c.drawCentredString(width/2, 5*cm, dados.get("ano",""))
    c.save()

# --- (As outras funções de geração de PDF como gerar_pagina_rosto, etc. devem ser coladas aqui) ---
# --- Incluí todas as outras funções abaixo para o código ficar completo ---

def gerar_pagina_rosto(dados, buffer):
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    nivel = dados.get("nivel", "")
    c.setFillColorRGB(0, 0, 0)
    styles = getSampleStyleSheet()
    style_normal_center = ParagraphStyle(name='Center', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=12, leading=14, alignment=TA_CENTER)
    style_titulo = ParagraphStyle(name='TitleCenter', parent=styles['h1'], fontName='Helvetica-Bold', fontSize=12, leading=14, alignment=TA_CENTER)
    style_versao = ParagraphStyle(name='VersionCenter', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=11, leading=13, alignment=TA_CENTER)
    y = height - 2.5*cm 
    c.setFont("Helvetica-Bold", 12)
    c.drawCentredString(width/2, y, "INSTITUTO DE PESQUISAS ENERGÉTICAS E NUCLEARES")
    y -= 0.5*cm
    c.drawCentredString(width/2, y, "Mestrado Profissional em Tecnologia das Radiações em Ciências da Saúde" if "Mestrado Profissional" in nivel else "Autarquia associada à Universidade de São Paulo")
    y -= 3*cm 
    titulo_completo = dados.get('titulo','').strip() + (f": {dados.get('subtitulo','').strip()}" if dados.get('subtitulo','') else "")
    p_titulo = Paragraph(titulo_completo, style_titulo)
    w, h = p_titulo.wrapOn(c, width-4*cm, y); p_titulo.drawOn(c, 2*cm, y - h); y -= h + 0.8*cm
    versao_texto = "Versão Corrigida<br/>Versão Original Disponível no IPEN" if dados.get('versao','') == 'Versão Corrigida' else "Versão Original"
    p_versao = Paragraph(versao_texto, style_versao)
    w, h = p_versao.wrapOn(c, width-4*cm, y); p_versao.drawOn(c, 2*cm, y - h); y -= h + 2*cm
    autor = f"{dados.get('nome_completo','')} {dados.get('sobrenome','')}".upper()
    p_autor = Paragraph(autor, style_normal_center)
    w, h = p_autor.wrapOn(c, width-4*cm, y); p_autor.drawOn(c, 2*cm, y - h); y -= h + 4.5*cm
    style_justificado = ParagraphStyle(name='Justify', parent=styles['Normal'], fontName='Helvetica', fontSize=12, leading=14, alignment=TA_JUSTIFY)
    style_orientador = ParagraphStyle(name='LeftOrientador', parent=styles['Normal'], fontName='Helvetica', fontSize=12, leading=14, alignment=TA_LEFT)
    if "Mestrado Profissional" in nivel: texto_final = f"Dissertação apresentada como parte dos requisitos para obtenção do Grau de Mestre Profissional em Tecnologia das Radiações em Ciências da Saúde na Área de {dados.get('area','')}"
    elif "Mestrado" in nivel: texto_final = f"Dissertação apresentada como parte dos requisitos para obtenção do Grau de Mestre em Ciências na Área de Tecnologia Nuclear - {dados.get('area','')}"
    else: texto_final = f"Tese apresentada como parte dos requisitos para obtenção do Grau de Doutor em Ciências na Área de Tecnologia Nuclear - {dados.get('area','')}"
    p_texto_final = Paragraph(texto_final, style_justificado)
    w, h = p_texto_final.wrapOn(c, width/2 - 2*cm, y); p_texto_final.drawOn(c, width/2, y - h); y -= h + 0.8*cm
    if dados.get("orientador"):
        p_label = Paragraph("Orientadora:" if "Profa" in dados.get("orientador_tipo") else "Orientador:", style_orientador)
        w, h = p_label.wrapOn(c, width/2-2*cm, y); p_label.drawOn(c, width/2, y-h); y -= h + 0.1*cm
        p_nome = Paragraph(f"{dados.get('orientador_tipo')} {dados.get('orientador')}", style_orientador)
        w, h = p_nome.wrapOn(c, width/2-2*cm, y); p_nome.drawOn(c, width/2, y-h); y -= h + 0.8*cm
    if dados.get("coorientador"):
        p_label_co = Paragraph("Coorientadora:" if "Profa" in dados.get("coorientador_tipo") else "Coorientador:", style_orientador)
        w, h = p_label_co.wrapOn(c, width/2-2*cm, y); p_label_co.drawOn(c, width/2, y-h); y -= h + 0.1*cm
        p_nome_co = Paragraph(f"{dados.get('coorientador_tipo')} {dados.get('coorientador')}", style_orientador)
        w, h = p_nome_co.wrapOn(c, width/2-2*cm, y); p_nome_co.drawOn(c, width/2, y-h)
    c.setFont("Helvetica", 12)
    c.drawCentredString(width/2, 5.5*cm, "São Paulo"); c.drawCentredString(width/2, 5*cm, dados.get("ano",""))
    c.save()

def gerar_ficha_catalografica(dados, buffer):
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4; margem_esq = 2.5 * cm; largura_texto = width - 2*margem_esq; y = height - 2.5*cm
    styles = getSampleStyleSheet()
    style_normal = ParagraphStyle(name='Normal', fontName='Helvetica', fontSize=11, leading=13)
    if dados.get('bolsa'): c.setFont("Helvetica", 11); c.drawString(margem_esq, y, f"Fonte de Financiamento: {dados['bolsa']}"); y -= 25
    texto_licenca = f"Autorizo a reprodução e divulgação deste trabalho acadêmico, total ou parcialmente, sob os termos da licença <b>{dados.get('licenca','')}</b>, permitindo seu uso e compartilhamento, desde que os devidos créditos sejam atribuídos e as condições estabelecidas na licença sejam respeitadas."
    p_licenca = Paragraph(texto_licenca, style_normal)
    w, h = p_licenca.wrapOn(c, largura_texto, y); p_licenca.drawOn(c, margem_esq, y-h); y -= h + 25
    c.setFont("Helvetica", 11); c.drawString(margem_esq, y, "Como citar:"); y -= 15
    p_citacao = Paragraph(obter_texto_citacao(dados), ParagraphStyle(name='Citacao', fontName='Helvetica', fontSize=11, leading=13, alignment=TA_JUSTIFY))
    w, h = p_citacao.wrapOn(c, largura_texto-10, y); p_citacao.drawOn(c, margem_esq, y-h); y -= h + 15
    largura_quadro = largura_texto * 0.80; x_quadro = margem_esq + (largura_texto - largura_quadro)/2; y_quadro_topo = 4 * cm
    orientador = dados.get("orientador", ""); texto_orientador = f"orientadora {orientador}" if "Profa" in dados.get("orientador_tipo") else f"orientador {orientador}"
    coorientador = dados.get("coorientador", ""); texto_coorientador = f"coorientadora {coorientador}" if "Profa" in dados.get("coorientador_tipo") else f"coorientador {coorientador}"
    programa = f"Programa de Pós-Graduação em Tecnologia das Radiações em Ciências da Saúde ({dados.get('area','')})" if "Mestrado Profissional" in dados.get('nivel','') else f"Programa de Pós-Graduação em Tecnologia Nuclear ({dados.get('area','')})"
    titulo_completo_ficha = dados.get('titulo','').strip() + (f": {dados['subtitulo'].strip()}" if dados.get('subtitulo') else "")
    romanos = f"I. {orientador}, orient. II. {coorientador}, coorient. III. Título." if orientador and coorientador else f"I. {orientador}, orient. II. Título." if orientador else "I. Título."
    chaves_base = 'chave' if dados.get('idioma') == 'Português' else 'keyword'
    chaves_filtradas = [dados.get(f'{chaves_base}{i+1}', '') for i in range(5) if dados.get(f'{chaves_base}{i+1}', '')]
    chaves_formatadas = " ".join([f"{i+1}. {chave.strip()}." for i, chave in enumerate(chaves_filtradas)])
    partes_texto = [f"{dados.get('sobrenome','')}, {dados.get('nome_completo','')}<br/><br/>", f"{titulo_completo_ficha} / {dados.get('nome_completo','')} {dados.get('sobrenome','')}"]
    if orientador: partes_texto.append(f". {texto_orientador}")
    if coorientador: partes_texto.append(f". {texto_coorientador}")
    partes_texto.append(f". São Paulo, {dados.get('ano','')}.<br/><br/>")
    texto_ficha = f"""{"".join(partes_texto)}{dados.get('paginas','')} p.<br/><br/>{dados.get('nivel','')} - {programa} -- Instituto de Pesquisas Energéticas e Nucleares. Universidade de São Paulo.<br/><br/>&nbsp;&nbsp;&nbsp;{chaves_formatadas}{romanos}""".strip()
    p_ficha = Paragraph(texto_ficha.replace("\n", ""), ParagraphStyle(name='Ficha', fontName='Courier', fontSize=9, leading=11))
    w, h = p_ficha.wrapOn(c, largura_quadro-20, height)
    altura_quadro = max(6.5 * cm, h + 20)
    c.rect(x_quadro, y_quadro_topo, largura_quadro, altura_quadro)
    p_ficha.drawOn(c, x_quadro + 10, y_quadro_topo + altura_quadro - 10 - h)
    c.setFont("Helvetica", 10)
    c.drawCentredString(width/2, y_quadro_topo + altura_quadro + 30, "Ficha catalográfica elaborada pelo Sistema de geração automática da Biblioteca IPEN,")
    c.drawCentredString(width/2, y_quadro_topo + altura_quadro + 18, "com os dados fornecidos pelo(a) autor(a).")
    c.save()

def gerar_resumo(dados, idioma_principal, buffer):
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=2.5*cm, rightMargin=2.5*cm, topMargin=2.5*cm, bottomMargin=2.5*cm)
    styles = getSampleStyleSheet()
    story = [
        Paragraph("ABSTRACT" if idioma_principal == "Inglês" else "RESUMO", ParagraphStyle(name='Title', parent=styles['h1'], fontName='Helvetica-Bold', fontSize=12, alignment=TA_CENTER, spaceAfter=1*cm)),
        Paragraph(obter_texto_citacao(dados, incluir_disponivel_em=False, titulo_override=dados.get('titulo'), subtitulo_override=dados.get('subtitulo')), ParagraphStyle(name='Citacao', parent=styles['Normal'], fontName='Helvetica', fontSize=12, leading=14, alignment=TA_JUSTIFY, spaceAfter=1*cm)),
        Paragraph(dados.get('resumo', ''), ParagraphStyle(name='Body', parent=styles['Normal'], fontName='Helvetica', fontSize=12, leading=18, alignment=TA_JUSTIFY, spaceAfter=1*cm))
    ]
    chaves_base, rotulo = ('keyword', "<b>Keywords:</b> ") if idioma_principal == "Inglês" else ('chave', "<b>Palavras-chave:</b> ")
    chaves_filtradas = [dados.get(f'{chaves_base}{i+1}', '') for i in range(5) if dados.get(f'{chaves_base}{i+1}', '')]
    if chaves_filtradas: story.append(Paragraph(rotulo + ", ".join(chaves_filtradas), ParagraphStyle(name='Keywords', parent=styles['Normal'], fontName='Helvetica', fontSize=12, leading=15)))
    doc.build(story)

def gerar_abstract(dados, idioma_principal, buffer):
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=2.5*cm, rightMargin=2.5*cm, topMargin=2.5*cm, bottomMargin=2.5*cm)
    styles = getSampleStyleSheet()
    story = [
        Paragraph("RESUMO" if idioma_principal == "Inglês" else "ABSTRACT", ParagraphStyle(name='Title', fontName='Helvetica-Bold', fontSize=12, alignment=TA_CENTER, spaceAfter=1*cm)),
        Paragraph(obter_texto_citacao(dados, incluir_disponivel_em=False, titulo_override=dados.get('titulo_traduzido'), subtitulo_override=dados.get('subtitulo_traduzido')), ParagraphStyle(name='Citacao', fontName='Helvetica', fontSize=12, leading=13, alignment=TA_JUSTIFY, spaceAfter=1*cm)),
        Paragraph(dados.get('abstract', ''), ParagraphStyle(name='Body', fontName='Helvetica', fontSize=12, leading=18, alignment=TA_JUSTIFY, spaceAfter=1*cm))
    ]
    chaves_base, rotulo = ('chave', "<b>Palavras-chave:</b> ") if idioma_principal == "Inglês" else ('keyword', "<b>Keywords:</b> ")
    chaves_filtradas = [dados.get(f'{chaves_base}{i+1}', '') for i in range(5) if dados.get(f'{chaves_base}{i+1}', '')]
    if chaves_filtradas: story.append(Paragraph(rotulo + ", ".join(chaves_filtradas), ParagraphStyle(name='Keywords', parent=styles['Normal'], fontName='Helvetica', fontSize=12, leading=15)))
    doc.build(story)

def gerar_contracapa(dados, buffer):
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    nivel = dados.get("nivel", "")
    cores = {"Mestrado Profissional": (129/255, 0/255, 64/255), "Mestrado": (30/255, 143/255, 113/255), "Tese": (52/255, 14/255, 113/255)}
    cor_faixas = next((cor for key, cor in cores.items() if key in nivel), cores["Tese"])
    c.setFillColorRGB(*cor_faixas)
    f_fina, f_grossa, esp = 2.7*mm, 4.8*mm, 1.2*mm
    c.rect(0, height - 16*mm - f_fina, width, f_fina, fill=1, stroke=0)
    c.rect(0, height - 16*mm - f_fina - esp - f_grossa, width, f_grossa, fill=1, stroke=0)
    c.rect(0, height - 16*mm - f_fina - esp - f_grossa - esp - f_fina, width, f_fina, fill=1, stroke=0)
    b_margin = 9*mm
    c.rect(0, b_margin, width, f_fina, fill=1, stroke=0)
    c.rect(0, b_margin + f_fina + esp, width, f_grossa, fill=1, stroke=0)
    c.rect(0, b_margin + f_fina + esp + f_grossa + esp, width, f_fina, fill=1, stroke=0)
    c.setFillColorRGB(0,0,0)
    texto = """INSTITUTO DE PESQUISAS ENERGÉTICAS E NUCLEARES<br/>Av. Prof. Lineu Prestes, 2242 - Cidade Universitária - CEP: 05508-000<br/>Fone: (11) 2810-5000<br/>São Paulo - SP - Brasil<br/>https://www.gov.br/ipen<br/><br/>O IPEN é uma Autarquia vinculada à Secretaria de Desenvolvimento, associada<br/>à Universidade de São Paulo e gerida técnica e administrativamente pela<br/>Comissão Nacional de Energia Nuclear, órgão do<br/>Ministério da Ciência, Tecnologia e Inovação."""
    p = Paragraph(texto, ParagraphStyle(name='ContraCapa', fontName='Helvetica-Bold', fontSize=10, leading=12, alignment=TA_CENTER))
    w, h = p.wrapOn(c, width - 4*cm, height)
    p.drawOn(c, 2*cm, b_margin + 4*cm)
    c.save()


@app.route('/', methods=['GET', 'POST'])
def formulario():
    if request.method == 'POST':
        dados = request.form.to_dict()
        documentos_selecionados = request.form.getlist('documentos')

        if not documentos_selecionados:
            flash('Você deve selecionar pelo menos um documento para gerar.', 'error')
            return render_template('formulario.html', dados=dados)

        # AQUI PODEMOS ADICIONAR A VALIDAÇÃO COMPLETA
        # Por simplicidade, essa parte foi omitida, mas a lógica do seu script Tkinter seria adaptada aqui usando flash()

        try:
            generated_files = {}
            idioma_principal = dados.get('idioma', 'Português')

            # Mapeia o nome do documento para a função que o gera
            funcoes_geradoras = {
                'capa': gerar_capa,
                'pagina_rosto': gerar_pagina_rosto,
                'ficha': gerar_ficha_catalografica,
                'contracapa': gerar_contracapa
            }

            for doc_name, func in funcoes_geradoras.items():
                if doc_name in documentos_selecionados:
                    buffer = io.BytesIO()
                    func(dados, buffer)
                    buffer.seek(0)
                    generated_files[f'{doc_name}.pdf'] = buffer
            
            # Lógica especial para resumo e abstract
            if 'resumo' in documentos_selecionados:
                buffer = io.BytesIO()
                func = gerar_resumo if idioma_principal == 'Português' else gerar_abstract
                func(dados, idioma_principal, buffer)
                buffer.seek(0)
                generated_files['resumo.pdf'] = buffer
            
            if 'abstract' in documentos_selecionados:
                buffer = io.BytesIO()
                func = gerar_abstract if idioma_principal == 'Português' else gerar_resumo
                func(dados, idioma_principal, buffer)
                buffer.seek(0)
                generated_files['abstract.pdf'] = buffer

            if len(generated_files) == 1:
                filename, buffer = list(generated_files.items())[0]
                return send_file(buffer, as_attachment=True, download_name=filename, mimetype='application/pdf')
            else:
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for filename, buffer in generated_files.items():
                        zipf.writestr(filename, buffer.read())
                zip_buffer.seek(0)
                return send_file(zip_buffer, as_attachment=True, download_name='documentos_ipen.zip', mimetype='application/zip')

        except Exception as e:
            flash(f'Ocorreu um erro ao gerar o PDF: {e}', 'error')
            return render_template('formulario.html', dados=dados)

    return render_template('formulario.html', dados={})

if __name__ == '__main__':
    app.run(debug=True)