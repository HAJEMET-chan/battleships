# src/network_manager.py
import socket
import threading
import json
import time
from typing import Callable, Optional, Dict, Any, List
import platform # Для определения ОС

class NetworkManager:
    """
    Базовый класс для управления сетевым соединением (хост или клиент).
    """
    def __init__(self, port: int = 12345):
        self.port = port
        self.socket: Optional[socket.socket] = None
        self.conn: Optional[socket.socket] = None # Соединение с другим пиром
        self.addr: Optional[tuple[str, int]] = None
        self.is_connected = False
        self.running = False
        self.receive_thread: Optional[threading.Thread] = None
        self.message_callback: Optional[Callable[[Dict[str, Any]], None]] = None # Callback for received messages
        self.connection_status_callback: Optional[Callable[[bool, str], None]] = None # Callback for connection status

    def set_callbacks(self, message_cb: Callable[[Dict[str, Any]], None], status_cb: Callable[[bool, str], None]):
        """Устанавливает функции обратного вызова для обработки сообщений и статуса соединения."""
        self.message_callback = message_cb
        self.connection_status_callback = status_cb

    def _send_data(self, data: Dict[str, Any]):
        """Отправляет данные через установленное соединение."""
        if self.conn and self.is_connected:
            try:
                message = json.dumps(data).encode('utf-8')
                # Префикс длины сообщения
                self.conn.sendall(len(message).to_bytes(4, 'big') + message)
            except (BrokenPipeError, ConnectionResetError, OSError) as e:
                print(f"Ошибка отправки данных: {e}")
                self.disconnect("Ошибка отправки данных.")
            except Exception as e:
                print(f"Неизвестная ошибка при отправке: {e}")
                self.disconnect("Неизвестная ошибка при отправке.")
        else:
            print("Нет активного соединения для отправки данных.")

    def _receive_data(self) -> Optional[Dict[str, Any]]:
        """Получает данные из установленного соединения."""
        if self.conn and self.is_connected:
            try:
                # Сначала получаем длину сообщения (4 байта)
                length_bytes = self.conn.recv(4)
                if not length_bytes:
                    self.disconnect("Соединение закрыто удаленной стороной.")
                    return None
                message_length = int.from_bytes(length_bytes, 'big')

                # Затем получаем само сообщение
                chunks = []
                bytes_recd = 0
                while bytes_recd < message_length:
                    chunk = self.conn.recv(min(message_length - bytes_recd, 4096))
                    if not chunk:
                        self.disconnect("Соединение закрыто удаленной стороной во время приема.")
                        return None
                    chunks.append(chunk)
                    bytes_recd += len(chunk)
                full_message = b"".join(chunks)

                data = json.loads(full_message.decode('utf-8'))
                return data
            except (ConnectionResetError, BrokenPipeError, json.JSONDecodeError, OSError) as e:
                print(f"Ошибка получения данных: {e}")
                self.disconnect(f"Ошибка получения данных: {e}")
                return None
            except Exception as e:
                print(f"Неизвестная ошибка при приеме: {e}")
                self.disconnect(f"Неизвестная ошибка при приеме: {e}")
                return None
        return None

    def _listen_for_messages(self):
        """Поток, постоянно слушающий входящие сообщения."""
        while self.running and self.is_connected:
            data = self._receive_data()
            if data and self.message_callback:
                self.message_callback(data)
            elif data is None and self.running: # Disconnected
                break
            time.sleep(0.01) # Небольшая задержка, чтобы не нагружать CPU

    def start_listening(self):
        """Запускает поток для прослушивания входящих сообщений."""
        if self.is_connected and not self.receive_thread:
            self.running = True
            self.receive_thread = threading.Thread(target=self._listen_for_messages, daemon=True)
            self.receive_thread.start()

    def send_game_data(self, data_type: str, payload: Dict[str, Any]):
        """Отправляет игровые данные другому пиру."""
        full_data = {"type": data_type, "payload": payload}
        self._send_data(full_data)

    def disconnect(self, reason: str = "Отключено."):
        """Отключает сетевое соединение."""
        if self.is_connected:
            print(f"Отключение: {reason}")
            self.is_connected = False
            self.running = False
            if self.conn:
                try:
                    self.conn.shutdown(socket.SHUT_RDWR)
                    self.conn.close()
                except OSError as e:
                    print(f"Ошибка при закрытии соединения: {e}")
                self.conn = None
            if self.socket:
                try:
                    self.socket.close()
                except OSError as e:
                    print(f"Ошибка при закрытии сокета: {e}")
                self.socket = None
            if self.connection_status_callback:
                self.connection_status_callback(False, reason)
            print("Соединение разорвано.")

    def shutdown(self):
        """Полностью останавливает сетевой менеджер."""
        self.disconnect("Завершение работы.")
        if self.receive_thread and self.receive_thread.is_alive():
            # Даем потоку время на завершение, но не блокируем навсегда
            self.receive_thread.join(timeout=1)
            if self.receive_thread.is_alive():
                print("Поток приема не завершился вовремя.")


class NetworkHost(NetworkManager):
    """
    Управляет сетевым соединением в режиме хоста.
    """
    def __init__(self, port: int = 12345):
        super().__init__(port)
        self.host_ips = self._get_all_local_ips() # Получаем все локальные IP

    def _get_all_local_ips(self) -> List[str]:
        """
        Получает все не-loopback локальные IP-адреса хоста.
        """
        ips = []
        try:
            # Создаем UDP-сокет, чтобы получить IP-адрес, который будет использоваться
            # для исходящих соединений (и, следовательно, для входящих на этом интерфейсе)
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80)) # Подключаемся к внешнему серверу (Google DNS)
            main_ip = s.getsockname()[0]
            s.close()
            ips.append(main_ip)
        except Exception:
            pass # Если нет интернет-соединения, этот метод может не сработать

        # Дополнительно пытаемся получить все IP-адреса, связанные с хостнеймом
        try:
            hostname = socket.gethostname()
            all_host_ips = socket.gethostbyname_ex(hostname)[2]
            for ip in all_host_ips:
                if ip not in ips and not ip.startswith('127.'):
                    ips.append(ip)
        except Exception:
            pass

        if not ips:
            ips.append('127.0.0.1') # Fallback to localhost if no other IPs found
        return ips

    def start_host(self):
        """Запускает хост и ожидает подключения клиента."""
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Устанавливаем опцию SO_REUSEADDR для повторного использования адреса
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.settimeout(1) # Небольшой таймаут для accept

        try:
            # Привязываемся к 0.0.0.0, чтобы слушать на всех доступных интерфейсах
            self.socket.bind(('0.0.0.0', self.port))
            self.socket.listen(1)
            ip_message = ", ".join(self.host_ips)
            print(f"Хост запущен на 0.0.0.0:{self.port}. Ваши IP-адреса: {ip_message}. Ожидание подключения...")
            if self.connection_status_callback:
                self.connection_status_callback(False, f"Хост запущен. Ваши IP: {ip_message}. Ожидание подключения...")

            self.running = True
            while self.running and not self.is_connected:
                try:
                    self.conn, self.addr = self.socket.accept()
                    self.conn.settimeout(None) # Снимаем таймаут после подключения
                    self.is_connected = True
                    print(f"Подключен клиент: {self.addr}")
                    if self.connection_status_callback:
                        self.connection_status_callback(True, f"Подключен клиент: {self.addr[0]}")
                    self.start_listening()
                except socket.timeout:
                    if not self.running: # Хост был остановлен во время ожидания
                        break
                    continue
                except OSError as e:
                    print(f"Ошибка сокета при ожидании подключения: {e}")
                    self.disconnect(f"Ошибка сокета при ожидании подключения: {e}")
                    break
                except Exception as e:
                    print(f"Неизвестная ошибка в хосте: {e}")
                    self.disconnect(f"Неизвестная ошибка в хосте: {e}")
                    break
        except OSError as e:
            print(f"Не удалось запустить хост на 0.0.0.0:{self.port}: {e}")
            if self.connection_status_callback:
                self.connection_status_callback(False, f"Не удалось запустить хост: {e}")
            self.disconnect(f"Не удалось запустить хост: {e}")
        except Exception as e:
            print(f"Неизвестная ошибка при запуске хоста: {e}")
            self.disconnect(f"Неизвестная ошибка при запуске хоста: {e}")


class NetworkClient(NetworkManager):
    """
    Управляет сетевым соединением в режиме клиента.
    """
    def __init__(self, host_ip: str, port: int = 12345):
        super().__init__(port)
        self.host_ip = host_ip

    def connect_to_host(self):
        """Подключается к указанному хосту."""
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.conn = self.socket # Для клиента conn и socket - это одно и то же соединение
        try:
            print(f"Попытка подключения к {self.host_ip}:{self.port}...")
            if self.connection_status_callback:
                self.connection_status_callback(False, f"Попытка подключения к {self.host_ip}:{self.port}...")
            self.conn.connect((self.host_ip, self.port))
            self.is_connected = True
            self.addr = (self.host_ip, self.port)
            print(f"Подключено к хосту: {self.host_ip}:{self.port}")
            if self.connection_status_callback:
                self.connection_status_callback(True, f"Подключено к хосту: {self.host_ip}:{self.port}")
            self.start_listening()
        except (ConnectionRefusedError, socket.timeout, OSError) as e:
            print(f"Не удалось подключиться к хосту: {e}")
            if self.connection_status_callback:
                self.connection_status_callback(False, f"Не удалось подключиться: {e}")
            self.disconnect(f"Не удалось подключиться: {e}")
        except Exception as e:
            print(f"Неизвестная ошибка при подключении: {e}")
            self.disconnect(f"Неизвестная ошибка при подключении: {e}")

