# 🛠️ CodeArts Daily

Automatiza os benefícios diários do CodeArts e o presente único de cadastro. O script faz claim, confirm e depois relê a lista de benefícios, evitando tratar uma solicitação aceita como recompensa concluída.

[简体中文](../README.md) · [English](README.en.md) · [繁體中文](README.zh-Hant.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Português (BR)](README.pt-BR.md)

**Versão atual:** v1.0.6

A documentação completa em chinês está em [../README.md](../README.md).

## Recursos

- Usa o fluxo desktop `delivery → claim → confirm → nova leitura de delivery`.
- Assina com Huawei Cloud `SDK-HMAC-SHA256`, incluindo o cabeçalho `Host` do cliente desktop.
- Suporta login PKCE + DPoP com callback local automático.
- Renova credenciais antes do vencimento e as grava de forma atômica.
- Trata refresh token consumido, falha de gravação ou `STS5.1806` como estado terminal.
- Salva a chave de idempotência antes da escrita e limita a 6 tentativas por dia, com 10 minutos de intervalo.

## Início rápido no Qinglong

```bash
python3 -m pip install -r requirements.txt
```

Envie `codearts_daily.py`, configure `CODEARTS_CREDENTIALS` e crie a tarefa:

```text
40 8 * * * task codearts_daily.py
```

Gere as credenciais localmente:

```bash
python codearts_login.py
python codearts_login.py --paste --no-browser
python codearts_login.py --note principal
```

O callback escuta em `127.0.0.1`; execute o login na sua máquina mesmo quando o Qinglong estiver em um servidor remoto.

## GitHub Actions

Crie os Secrets em **Settings → Secrets and variables → Actions**:

```text
CODEARTS_CREDENTIALS
PUSHPLUS_TOKEN          # opcional
BARK_URL                # opcional
WECOM_WEBHOOK           # opcional
DINGTALK_WEBHOOK        # opcional
DINGTALK_SECRET         # opcional
```

Depois use **Actions → CodeArts Daily → Run workflow**. O workflow é manual por padrão; habilite o agendamento comentado em `.github/workflows/daily.yml` se necessário. O cron usa UTC.

## Variáveis principais

| Variável | Formato e uso |
| :--- | :--- |
| `CODEARTS_CREDENTIALS` | JSON em uma linha. Com refresh token, PKCE e chave privada DPoP, permite renovação automática. |
| `CODEARTS_CREDENTIALS` | `AK\|SK\|STS` também permite receber, mas expira em cerca de uma hora e não renova. |
| `PUSHPLUS_TOKEN`, `BARK_URL`, `WECOM_WEBHOOK`, `DINGTALK_WEBHOOK`, `DINGTALK_SECRET` | Canais de notificação opcionais |
| `QL_URL`, `QL_TOKEN` | Endpoint opcional de notificação e token legado do painel Qinglong |

Separe contas por linha ou `&`. Cada JSON deve ficar em sua própria linha.

## Sucesso e privacidade

O benefício só é confirmado quando a nova leitura retorna `CONFIRMED` ou `CONSUMED`. Se um item estiver `CLAIMED` sem `userBenefitId`, o script para em vez de repetir o claim ou inventar um ID.

`codearts_credentials.json` contém AK/SK/STS, refresh token, material PKCE e chave privada DPoP. `codearts_welfare_ledger.json` contém idempotência e estado de limite local. Ambos são ignorados pelo Git. Não publique esses arquivos nem segredos em uma issue.

## Limites de uso e redistribuição

As versões oficiais deste projeto são gratuitas, incluindo o repositório, os scripts, as instruções de implantação e os Releases.

Sem autorização escrita explícita do autor, não empacote o projeto como recurso pago, edição interna ou exclusiva, benefício de assinatura, curso pago, implantação paga ou serviço de atualização; não o republique em contas, grupos ou canais sem relação para gerar tráfego ou captar usuários; não remova avisos de autoria e direitos autorais nem reivindique o trabalho como seu; não use o nome, avatar, QR codes ou nome do projeto para sugerir endosso oficial.

Em caso de violação, o autor pode solicitar a remoção do conteúdo e pode pausar atualizações, arquivar ou excluir o repositório. Consulte [NOTICE.md](../NOTICE.md) para as regras completas.

## Links

- [Releases](https://github.com/L0NE-6/CodeArts-Daily/releases)
- [Issues](https://github.com/L0NE-6/CodeArts-Daily/issues)
- [Código e guia completo em chinês](../README.md)
