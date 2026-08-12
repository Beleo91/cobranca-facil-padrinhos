"""
Serviço de Envio de E-mails via SMTP.

Variáveis de ambiente necessárias (configure no Render):
  SMTP_HOST      — ex: smtp.gmail.com
  SMTP_PORT      — ex: 587
  SMTP_USER      — seu e-mail remetente
  SMTP_PASSWORD  — senha de aplicativo (Gmail) ou senha normal
  APP_URL        — URL pública da aplicação (ex: https://cobranca-facil-padrinhos.onrender.com)
"""
import os
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
APP_URL = os.getenv("APP_URL", "https://cobranca-facil-padrinhos.onrender.com")


def _smtp_configurado() -> bool:
    return bool(SMTP_HOST and SMTP_USER and SMTP_PASSWORD)


def enviar_email_recuperacao(destinatario: str, nome: str, token: str) -> bool:
    """
    Envia o e-mail de recuperação de senha com link contendo o token.
    Retorna True em caso de sucesso, False em caso de falha.
    """
    link = f"{APP_URL}/login.html?reset_token={token}"

    assunto = "🔑 Recuperação de Senha — Cobrança Fácil Padrinhos"

    corpo_html = f"""
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head><meta charset="UTF-8"></head>
    <body style="margin:0;padding:0;background:#0b0f19;font-family:'Inter',Arial,sans-serif;">
      <div style="max-width:520px;margin:40px auto;background:rgba(15,23,42,0.95);border:1px solid rgba(255,255,255,0.1);border-radius:16px;padding:40px 32px;box-shadow:0 20px 40px rgba(0,0,0,0.5);">
        <div style="text-align:center;margin-bottom:28px;">
          <span style="font-size:2.5rem;">💰</span>
          <h2 style="color:#f8fafc;margin:8px 0 4px;font-size:1.4rem;">Cobrança Fácil Padrinhos</h2>
          <p style="color:#64748b;margin:0;font-size:0.85rem;">Sistema de Gestão de Empréstimos</p>
        </div>

        <h3 style="color:#f8fafc;font-size:1.1rem;margin:0 0 12px;">Olá, {nome}!</h3>
        <p style="color:#94a3b8;line-height:1.6;margin:0 0 24px;">
          Recebemos uma solicitação para redefinir a senha da sua conta.
          Clique no botão abaixo para criar uma nova senha. Este link é válido por <strong style="color:#f8fafc;">30 minutos</strong>.
        </p>

        <div style="text-align:center;margin:28px 0;">
          <a href="{link}"
             style="display:inline-block;padding:14px 32px;background:linear-gradient(135deg,#10b981,#059669);color:#fff;font-weight:700;font-size:1rem;text-decoration:none;border-radius:10px;box-shadow:0 4px 14px rgba(16,185,129,0.4);">
            🔑 Redefinir Minha Senha
          </a>
        </div>

        <p style="color:#64748b;font-size:0.8rem;line-height:1.5;margin:24px 0 0;border-top:1px solid rgba(255,255,255,0.07);padding-top:20px;">
          Se você não solicitou a redefinição de senha, ignore este e-mail — sua senha permanece a mesma.<br><br>
          Por segurança, não compartilhe este link com ninguém.<br>
          Link direto: <a href="{link}" style="color:#10b981;">{link}</a>
        </p>
      </div>
    </body>
    </html>
    """

    corpo_texto = (
        f"Olá, {nome}!\n\n"
        f"Para redefinir sua senha, acesse o link abaixo (válido por 30 minutos):\n\n"
        f"{link}\n\n"
        f"Se não foi você quem solicitou, ignore este e-mail."
    )

    if not _smtp_configurado():
        # Sem SMTP configurado: imprime no log do servidor para debug
        print(f"[EMAIL] SMTP não configurado. Link de recuperação para {destinatario}:")
        print(f"[EMAIL] {link}")
        # Retorna True para não bloquear o fluxo — o admin pode ver nos logs do Render
        return True

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = assunto
        msg["From"] = f"Cobrança Fácil Padrinhos <{SMTP_USER}>"
        msg["To"] = destinatario

        msg.attach(MIMEText(corpo_texto, "plain", "utf-8"))
        msg.attach(MIMEText(corpo_html, "html", "utf-8"))

        context = ssl.create_default_context()
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.ehlo()
            server.starttls(context=context)
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_USER, destinatario, msg.as_string())

        print(f"[EMAIL] E-mail de recuperação enviado para {destinatario}")
        return True

    except Exception as e:
        print(f"[EMAIL ERROR] Falha ao enviar e-mail para {destinatario}: {e}")
        return False


def enviar_email_lembrete_cobranca(destinatario: str, nome_cliente: str, valor: float, data_vencimento: str, num_parcela: int = 1) -> bool:
    """Envia o e-mail de lembrete de cobrança (1 dia antes do vencimento)."""
    assunto = f"⏰ Lembrete de Vencimento de Parcela (R$ {valor:.2f}) — Cobrança Fácil"
    corpo_html = f"""
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head><meta charset="UTF-8"></head>
    <body style="margin:0;padding:0;background:#0b0f19;font-family:'Inter',Arial,sans-serif;">
      <div style="max-width:520px;margin:40px auto;background:rgba(15,23,42,0.95);border:1px solid rgba(255,255,255,0.1);border-radius:16px;padding:40px 32px;box-shadow:0 20px 40px rgba(0,0,0,0.5);">
        <div style="text-align:center;margin-bottom:28px;">
          <span style="font-size:2.5rem;">⏰</span>
          <h2 style="color:#f8fafc;margin:8px 0 4px;font-size:1.4rem;">Cobrança Fácil Padrinhos</h2>
          <p style="color:#64748b;margin:0;font-size:0.85rem;">Lembrete de Vencimento</p>
        </div>

        <h3 style="color:#f8fafc;font-size:1.1rem;margin:0 0 12px;">Olá, {nome_cliente}!</h3>
        <p style="color:#94a3b8;line-height:1.6;margin:0 0 24px;">
          Este é um lembrete amigável de que sua parcela nº <strong style="color:#f8fafc;">#{num_parcela}</strong> no valor de <strong style="color:#10b981;">R$ {valor:.2f}</strong> vence amanhã, dia <strong style="color:#f8fafc;">{data_vencimento}</strong>.
        </p>

        <p style="color:#64748b;font-size:0.8rem;line-height:1.5;margin:24px 0 0;border-top:1px solid rgba(255,255,255,0.07);padding-top:20px;">
          Caso já tenha efetuado o pagamento, por favor desconsidere este e-mail.
        </p>
      </div>
    </body>
    </html>
    """
    corpo_texto = f"Olá, {nome_cliente}!\n\nLembrete de vencimento da parcela nº #{num_parcela} no valor de R$ {valor:.2f} com vencimento em {data_vencimento}."

    if not _smtp_configurado():
        print(f"[EMAIL LEMBRETE] SMTP não configurado. Lembrete para {destinatario}: R$ {valor:.2f} em {data_vencimento}")
        return True

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = assunto
        msg["From"] = f"Cobrança Fácil Padrinhos <{SMTP_USER}>"
        msg["To"] = destinatario

        msg.attach(MIMEText(corpo_texto, "plain", "utf-8"))
        msg.attach(MIMEText(corpo_html, "html", "utf-8"))

        context = ssl.create_default_context()
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.ehlo()
            server.starttls(context=context)
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_USER, destinatario, msg.as_string())

        print(f"[EMAIL LEMBRETE] E-mail de lembrete enviado para {destinatario}")
        return True
    except Exception as e:
        print(f"[EMAIL ERROR] Falha ao enviar lembrete para {destinatario}: {e}")
        return False
