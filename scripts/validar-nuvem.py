"""CRUD real nas duas tabelas + SELECT no container apos cada operacao.
Execute na VM: python3 scripts/validar-nuvem.py --base-url http://IP:8080
Usa apenas dados sinteticos criados pela propria execucao. Nao limpa outras linhas.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import time
import urllib.error
import urllib.request
import uuid

ROOT = Path(__file__).resolve().parent.parent
DB = 'zelacidade-orbital-db-rm558710'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--base-url', required=True)
    parser.add_argument('--testar-volume', action='store_true', help='Recria os dois containers e verifica os mesmos registros no volume nomeado.')
    args = parser.parse_args()
    base = args.base_url.rstrip('/')
    evidence = {'inicioUtc': datetime.now(timezone.utc).isoformat(), 'baseUrl': base, 'operacoes': [], 'testes': [], 'aprovado': False}
    area_id = alerta_id = None
    token = uuid.uuid4().hex[:10]

    def http(method, path, body=None, expected=200):
        data = json.dumps(body).encode() if body is not None else None
        request = urllib.request.Request(base+path, data=data, method=method, headers={'Content-Type': 'application/json'})
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                status, raw = response.status, response.read()
        except urllib.error.HTTPError as error:
            status, raw = error.code, error.read()
        result = json.loads(raw) if raw else None
        assert status == expected, f'{method} {path}: esperado {expected}, recebido {status}: {result}'
        return result

    def select(table, row_id):
        query = f'SELECT * FROM "{table}" WHERE "Id" = {int(row_id)};'
        print(f'\nSQL DIRETO NO CONTAINER: {query}', flush=True)
        command = ['docker', 'container', 'exec', DB, 'psql', '-X', '-U', 'orbital', '-d', 'orbital', '-v', 'ON_ERROR_STOP=1', '-c', query]
        result = subprocess.run(command, check=True, capture_output=True, text=True).stdout
        print(result, flush=True)
        rows_query = f'SELECT COALESCE(json_agg(t),\'[]\'::json) FROM ({query[:-1]}) t;'
        rows = subprocess.run(command[:-1] + [rows_query, '-t', '-A'], check=True, capture_output=True, text=True).stdout
        return query, result, json.loads(rows)

    def record(operation, table, row_id, method, path, body=None, expected=200):
        result = http(method, path, body, expected)
        query, output, rows = select(table, row_id)
        assert len(rows) == (0 if operation == 'DELETE' else 1)
        if operation != 'DELETE':
            assert rows[0]['Id'] == row_id
            for key, value in (body or {}).items():
                sql_key = key[0].upper() + key[1:]
                assert rows[0][sql_key] == value, f'Divergencia SQL em {sql_key}'
        evidence['operacoes'].append({'operacao': operation, 'tabela': table, 'id': row_id, 'http': expected, 'resposta': result, 'sql': query, 'saidaSelect': output, 'linhas': rows, 'utc': datetime.now(timezone.utc).isoformat()})
        print(f'APROVADO: {operation} {table} #{row_id}', flush=True)
        return result

    try:
        http('GET', '/health/ready')
        area_body = {'nome': f'Area sintetica {token}', 'municipio': 'Sao Paulo', 'latitude': -23.55052, 'longitude': -46.633308}
        area = http('POST', '/api/areas/', area_body, 201)
        area_id = area['id']
        query, output, rows = select('AreasMonitoradas', area_id)
        assert len(rows) == 1 and rows[0]['Nome'] == area_body['nome']
        evidence['operacoes'].append({'operacao': 'CREATE', 'tabela': 'AreasMonitoradas', 'id': area_id, 'http': 201, 'resposta': area, 'sql': query, 'saidaSelect': output, 'linhas': rows})
        record('READ', 'AreasMonitoradas', area_id, 'GET', f'/api/areas/{area_id}')
        area_body['nome'] += ' atualizada'
        record('UPDATE', 'AreasMonitoradas', area_id, 'PUT', f'/api/areas/{area_id}', area_body)
        alerta_body = {'areaMonitoradaId': area_id, 'titulo': f'Risco ambiental demonstrativo {token}', 'fonteOrbital': 'Sentinel-2 (exemplo sintetico)', 'referenciaObservacao': 'DEMO: observacao manual, sem download de imagem orbital', 'status': 'aberto'}
        alerta = http('POST', '/api/alertas/', alerta_body, 201)
        alerta_id = alerta['id']
        query, output, rows = select('Alertas', alerta_id)
        assert len(rows) == 1 and rows[0]['AreaMonitoradaId'] == area_id
        evidence['operacoes'].append({'operacao': 'CREATE', 'tabela': 'Alertas', 'id': alerta_id, 'http': 201, 'resposta': alerta, 'sql': query, 'saidaSelect': output, 'linhas': rows})
        record('READ', 'Alertas', alerta_id, 'GET', f'/api/alertas/{alerta_id}')
        alerta_body['status'] = 'resolvido'
        record('UPDATE', 'Alertas', alerta_id, 'PUT', f'/api/alertas/{alerta_id}', alerta_body)
        http('DELETE', f'/api/areas/{area_id}', expected=409)
        evidence['testes'].append({'teste': 'Excluir pai com alerta', 'http': 409, 'aprovado': True})
        http('POST', '/api/areas/', {**area_body, 'latitude': 91}, 400)
        evidence['testes'].append({'teste': 'Latitude invalida', 'http': 400, 'aprovado': True})
        http('POST', '/api/alertas/', {**alerta_body, 'areaMonitoradaId': 2147483647}, 400)
        evidence['testes'].append({'teste': 'Area inexistente', 'http': 400, 'aprovado': True})
        if args.testar_volume:
            subprocess.run(['docker', 'compose', 'up', '-d', '--force-recreate'], cwd=ROOT, check=True)
            for attempt in range(45):
                try:
                    http('GET', '/health/ready')
                    break
                except (AssertionError, OSError):
                    time.sleep(2)
            else:
                raise AssertionError('API nao retornou apos recriar containers.')
            for table, row_id in [('AreasMonitoradas', area_id), ('Alertas', alerta_id)]:
                assert len(select(table, row_id)[2]) == 1
            evidence['testes'].append({'teste': 'Persistencia apos recriacao dos dois containers', 'volume': 'zelacidade-orbital-data-rm558710', 'aprovado': True})
        record('DELETE', 'Alertas', alerta_id, 'DELETE', f'/api/alertas/{alerta_id}', expected=204)
        alerta_id = None
        record('DELETE', 'AreasMonitoradas', area_id, 'DELETE', f'/api/areas/{area_id}', expected=204)
        area_id = None
        assert len(evidence['operacoes']) == 8
        evidence['aprovado'] = True
    finally:
        # Nao remove volume, banco ou dados de terceiros.
        for entity, row_id in [('alertas', alerta_id), ('areas', area_id)]:
            if row_id:
                try:
                    http('DELETE', f'/api/{entity}/{row_id}', expected=204)
                except Exception:
                    print(f'Limpeza pendente: {entity} #{row_id}')
        evidence['fimUtc'] = datetime.now(timezone.utc).isoformat()
        out = ROOT / 'evidencias'
        out.mkdir(exist_ok=True)
        (out/'crud-container.json').write_text(json.dumps(evidence, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print('CRUD das duas tabelas e SELECTs: APROVADOS.', flush=True)


if __name__ == '__main__':
    main()
