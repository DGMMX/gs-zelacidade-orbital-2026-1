"""Capa de DevOps 2026/1. Sem video: somente previa marcada.
python scripts/gerar-pdf.py --video-url URL_REAL --video-reviewed
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from urllib.parse import urlparse, parse_qs
import pymupdf

ROOT = Path(__file__).resolve().parent.parent


def youtube_url(value):
    parsed = urlparse(value)
    if parsed.scheme != 'https':
        raise ValueError('Use URL HTTPS real do video YouTube.')
    if parsed.hostname == 'youtu.be':
        video = parsed.path.strip('/')
    elif parsed.hostname in ('youtube.com', 'www.youtube.com') and parsed.path == '/watch':
        video = parse_qs(parsed.query).get('v', [''])[0]
    else:
        raise ValueError('Informe um video, nao canal, playlist ou URL de exemplo.')
    if not re.fullmatch(r'[A-Za-z0-9_-]{11}', video):
        raise ValueError('Identificador YouTube invalido.')
    return 'https://www.youtube.com/watch?v=' + video


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--video-url')
    parser.add_argument('--video-reviewed', action='store_true')
    args = parser.parse_args()
    config = json.loads((ROOT/'entrega.json').read_text(encoding='utf-8'))
    video = youtube_url(args.video_url) if args.video_url else config.get('videoUrl', '')
    if video and video != config.get('videoUrl'):
        config['videoRevisado'] = False
    config['videoUrl'] = video
    if args.video_reviewed:
        config['videoRevisado'] = True
    final = bool(video)
    if final:
        if not config.get('videoRevisado'):
            raise SystemExit('Assista ao video inteiro e confirme com --video-reviewed.')
        path = ROOT/'evidencias/crud-container.json'
        proof = json.loads(path.read_text(encoding='utf-8-sig')) if path.exists() else {}
        expected = {(table, operation) for table in ['AreasMonitoradas', 'Alertas'] for operation in ['CREATE', 'READ', 'UPDATE', 'DELETE']}
        actual = {(op.get('tabela'), op.get('operacao')) for op in proof.get('operacoes', []) if op.get('sql') and op.get('saidaSelect')}
        if not proof.get('aprovado') or not expected.issubset(actual):
            raise SystemExit('Falta evidencia real de CRUD e SELECT nas duas tabelas. Execute validar-nuvem.py na VM e copie o JSON para evidencias/.')
        environment_path = ROOT/'evidencias/ambiente.json'
        inspection_path = ROOT/'evidencias/inspecao-nuvem.json'
        environment = json.loads(environment_path.read_text(encoding='utf-8-sig')) if environment_path.exists() else {}
        inspection = json.loads(inspection_path.read_text(encoding='utf-8-sig')) if inspection_path.exists() else {}
        containers = inspection.get('containers', [])
        if (environment.get('vmCriada') is not True or environment.get('crudNuvemAprovado') is not True
            or inspection.get('vm', {}).get('subscriptionId') != 'dda05624-99e8-4c3e-adad-af54a46e1811'
            or len(containers) != 2 or any(c.get('health') != 'healthy' for c in containers)
            or proof.get('baseUrl') != 'http://' + environment.get('dns', '') + ':8080'):
            raise SystemExit('Falta comprovacao de execucao na VM Azure. Teste local nao substitui a nuvem.')
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)
    page.draw_rect(pymupdf.Rect(0, 0, 595, 205), fill=(0.05, 0.13, 0.24), color=None)
    def text(y, value, size=12, bold=False, color=(0.1, 0.16, 0.23)):
        page.insert_text((42, y), value, fontsize=size, fontname='hebo' if bold else 'helv', color=color)
    def link(y, value, url):
        text(y, value, 10, color=(0.05, 0.3, 0.65))
        page.insert_link({'kind': pymupdf.LINK_URI, 'from': pymupdf.Rect(42, y-12, 550, y+4), 'uri': url})
    text(50, 'FIAP | GLOBAL SOLUTION 2026/1', 13, True, (0.8, 0.88, 1))
    text(110, 'ZelaCidade Orbital', 31, True, (1, 1, 1))
    text(155, 'DevOps Tools & Cloud Computing', 19, color=(1, 1, 1))
    text(245, 'GRUPO ZELACIDADE - ENTREGA INDIVIDUAL', 12, True)
    text(285, config['nome'], 16, True)
    text(314, 'RM558710 | Turma 2TDSPG', 13)
    text(360, 'Professor: Antonio Sergio Rodrigues Figueiredo', 11)
    text(384, 'profantonio.figueiredo@fiap.com.br', 11)
    text(445, 'REPOSITORIO GITHUB', 12, True)
    link(474, config['github'], config['github'])
    text(528, 'VIDEO NO YOUTUBE', 12, True)
    if final:
        link(557, video, video)
    else:
        text(557, 'PENDENTE - aluno ainda nao gravou o video.', 12, True, (0.7, 0.2, 0.05))
        page.draw_rect(pymupdf.Rect(32, 610, 562, 688), fill=(1, 0.93, 0.83), color=None)
        text(642, 'PREVIA - NAO ENVIAR COMO ENTREGA FINAL', 13, True, (0.6, 0.2, 0.04))
        text(669, 'Falta link real da demonstracao exigida pelo professor.', 11)
    text(790, 'GS 2026/1 | Conteinerizacao .NET + PostgreSQL na Azure', 10)
    page = doc.new_page(width=595, height=842)
    text(55, 'Conferencia da entrega', 24, True)
    for y, value in [
        (105, 'Escopo: somente DevOps, paginas 23-28 do PDF do professor.'),
        (135, 'Imagem propria da API; usuario orbital; WORKDIR /app; porta 8080.'),
        (165, 'PostgreSQL 16 em container; porta 5432; variavel e volume nomeado.'),
        (195, 'Nomes com RM558710; rede compartilhada; execucao em background.'),
        (225, 'Duas tabelas relacionadas: AreasMonitoradas e Alertas.'),
        (255, 'Evidenciar logs, terminal e SELECT apos cada operacao do CRUD.'),
        (300, 'README: proposta, limites, arquitetura e tutorial desde o clone.'),
        (330, 'MVP com cadastro manual; exemplos sinteticos de fonte orbital.'),
        (360, 'Sem ingestao automatica de imagens ou previsao de desastres.'),
        (410, 'O ZIP contem fonte, infraestrutura e evidencias datadas, se executadas.'),
        (440, 'O formato oficial solicitado e PDF; a gravacao e obrigatoria.'),
        (490, 'Prazo original: 09/06/2026, 23h55. Verificar reposicao com professor.'),
        (520, 'Nao foi realizado envio ao Portal nem confirmado prazo substituto.'),
        (575, 'IA: ChatGPT/Codex auxiliou na preparacao e validacao do material.'),
        (605, 'O aluno deve revisar e explicar a solucao e seus comandos.')
    ]:
        text(y, value, 11)
    text(660, 'A revisao integral do video e uma confirmacao manual do aluno.', 11)
    text(690, 'O gerador valida formato da URL, nao o conteudo do video.', 11)
    text(790, 'ZelaCidade | Diego Bassalo Canals Silva | RM558710 | 2TDSPG', 10)
    doc.set_metadata({'title': 'GS 2026/1 - ZelaCidade Orbital - DevOps', 'author': config['nome'], 'subject': 'PREVIA SEM VIDEO' if not final else 'Entrega DevOps'})
    out = ROOT/'entrega'
    out.mkdir(exist_ok=True)
    target = out/('ZelaCidade_rm558710' + ('' if final else '_PREVIA') + '.pdf')
    doc.save(target)
    if final:
        (ROOT/'entrega.json').write_text(json.dumps(config, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(target)


if __name__ == '__main__':
    main()
