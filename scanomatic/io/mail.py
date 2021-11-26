import smtplib
import socket
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from logging import Logger
from struct import unpack
from typing import Optional, Union
from collections.abc import Sequence

import requests

from scanomatic.io.app_config import Config as AppConfig

_logger = Logger("Mailer")

_IP: Optional[str] = None


def ip_is_local(ip: str) -> bool:
    """Determines if ip is local
    Code from http://stackoverflow.com/a/8339939/1099682
    """
    f = unpack('!I', socket.inet_pton(socket.AF_INET, ip))[0]
    private = (
        # 127.0.0.0,   255.0.0.0   http://tools.ietf.org/html/rfc3330
        [2130706432, 4278190080],
        # 192.168.0.0, 255.255.0.0 http://tools.ietf.org/html/rfc1918
        [3232235520, 4294901760],
        # 172.16.0.0,  255.240.0.0 http://tools.ietf.org/html/rfc1918
        [2886729728, 4293918720],
        # 10.0.0.0,    255.0.0.0   http://tools.ietf.org/html/rfc1918
        [167772160,  4278190080],
    )
    for net in private:
        if (f & net[1]) == net[0]:
            return True
    return False


def get_my_ip():
    def get_ip_from_socket(sock: socket.socket) -> str:
        sock.connect(('8.8.8.8', 80))
        ip = sock.getsockname()[0]
        sock.close()
        return ip

    global _IP
    if _IP:
        return _IP

    try:
        _IP = get_ip_from_socket(socket.socket(
            socket.AF_INET,
            socket.SOCK_DGRAM,
        ))
    except IndexError:
        _logger.info("Failed to get IP via socket")

    if _IP is None or ip_is_local(_IP):
        try:
            _IP = requests.request('GET', 'http://myip.dnsomatic.com').text
        except requests.ConnectionError:
            _logger.info("Failed to get IP via external service provider")
            _IP = None

    return _IP


def get_server(
    host=None,
    smtp_port=0,
    tls=False,
    login=None,
    password=None,
) -> Optional[smtplib.SMTP]:
    if host:
        if tls and smtp_port == 0:
            smtp_port = 587
        elif smtp_port == 0:
            smtp_port = 25
        try:
            server = smtplib.SMTP(host, port=smtp_port)
        except Exception:
            return None

    else:
        try:
            server = smtplib.SMTP()
        except Exception:
            return None

    if tls:
        server.ehlo()
        server.starttls()
        server.ehlo()

    if login:
        server.login(login, password)
    else:
        try:
            server.connect()
        except socket.error:
            return None

    return server


def can_get_server_with_current_settings() -> bool:
    if AppConfig().mail.server:
        server = get_server(
            AppConfig().mail.server,
            smtp_port=AppConfig().mail.port,
            login=AppConfig().mail.user,
            password=AppConfig().mail.password,
        )
    else:
        server = None

    return server is not None


def mail(
    sender: Optional[str],
    receiver: Union[str, Sequence[str]],
    subject: str,
    message: str,
    final_message: bool = True,
    server: Optional[smtplib.SMTP] = None,
) -> bool:
    """
    :param sender: Then mail address of the sender, if has value `None` a
        default address will be generated using `get_default_email()`
    :param receiver: The mail address(es) of the reciever(s)
    :param subject: Subject line
    :param message: Bulk of message
    :param final_message (optional): If this is the final message intended to
        be sent by the server. If so, server will be disconnected afterwards.
        Default `True`
    :param server (optional): The server to send the message, if not supplied
        will create a default server
     using `get_server()`
    """
    if server is None:
        server = get_server()

    if server is None:
        return False

    if not sender:
        sender = get_default_email()

    msg = MIMEMultipart()

    msg['From'] = sender
    msg['To'] = (
        receiver if isinstance(receiver, str) else ", ".join(receiver)
    )
    msg['Subject'] = subject
    msg.attach(MIMEText(message))

    if isinstance(receiver, str):
        receiver = [receiver]
    try:
        server.sendmail(sender, receiver, msg.as_string())
    except smtplib.SMTPException:
        _logger.error(
            "Could not mail, either no network connection or missing mailing functionality.",  # noqa: E501
        )

    if final_message:
        try:
            server.quit()
        except Exception:
            pass

    return True


def get_host_name() -> Optional[str]:
    try:
        return socket.gethostbyaddr(get_my_ip())[0]
    except (IndexError, socket.herror):
        return None


def get_default_email(username="no-reply---scan-o-matic") -> str:

    hostname = get_host_name()
    if not hostname:
        hostname = "scanomatic.somewhere"

    return "{0}@{1}".format(username, hostname)
