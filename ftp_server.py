import socket
import threading
import os
import time


SERVER_HOST = '127.0.0.1'
SERVER_PORT = 50000 
BUFFER_SIZE = 4096 
CONN_TIMEOUT = 120 

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SERVER_DIR = os.path.join(BASE_DIR, 'server_files') 

if not os.path.exists(SERVER_DIR):
    try:
        os.makedirs(SERVER_DIR)
        print(f"[BAŞLATMA] '{SERVER_DIR}' klasörü oluşturuldu.")
    except Exception as e:
        print(f"[KRİTİK HATA] {SERVER_DIR} klasörü oluşturulamadı: {e}")

# Test dosyası oluşturma (RETR komutunun çalışması için)
test_filepath = os.path.join(SERVER_DIR, "testfile.txt")
if not os.path.exists(test_filepath):
    with open(test_filepath, 'w') as f:
        f.write("Bu, istemcinin indireceği bir test dosyasıdır.\n")
        for i in range(100):
             f.write(f"Satır numarası: {i+1}\n")
    print(f"[BAŞLATMA] '{test_filepath}' dosyası oluşturuldu.")


def send_response(conn, response):
    try:
        conn.sendall(f"{response}\r\n".encode('utf-8'))
    except Exception as e:
        pass

# STOR İşlemi 
def handle_stor(conn, filename):
    """İstemciden dosyayı alır (Upload)."""
    filepath = os.path.join(SERVER_DIR, filename)

    print(f"[TRANSFER] STOR başlatıldı: {filename}")
    
    send_response(conn, f"150 Dosya transferi başlatılıyor: {filename}")
    
    total_bytes = 0
    
    try:
        conn.settimeout(30) 
        with open(filepath, 'wb') as f:
            while True:
                bytes_read = conn.recv(BUFFER_SIZE) 
                if not bytes_read:
                    break
                f.write(bytes_read)
                total_bytes += len(bytes_read)

        conn.settimeout(None)
        
        print(f"[BAŞARILI] {filename} ({total_bytes} bytes) alındı.")
        
        if not os.path.exists(filepath) or os.path.getsize(filepath) != total_bytes:
             print(f"[UYARI] Dosya yazma kontrolü başarısız oldu: {filepath}. Beklenen boyut: {total_bytes}, Gerçek boyut: {os.path.getsize(filepath) if os.path.exists(filepath) else 0}")
             send_response(conn, "550 Dosya yazılırken sunucu hatası oluştu.")
             return 
        
        time.sleep(0.1) 

        send_response(conn, "226 Dosya başarıyla yüklendi.")
        
    except socket.timeout:
         print(f"[UYARI] STOR sırasında zaman aşımı. Dosya alımı kesildi.")
         if os.path.exists(filepath):
             os.remove(filepath)
    except PermissionError: 
         print(f"[KRİTİK HATA] Yazma izni hatası: {filepath}")
         send_response(conn, "550 Sunucuda dosya yazma izni yok. (PermissionError)")
         if os.path.exists(filepath):
             os.remove(filepath)
    except ConnectionResetError:
        print(f"[UYARI] STOR sırasında istemci bağlantıyı aniden kapattı.")
    except Exception as e:
        print(f"[HATA] STOR hatası: {e}")
        send_response(conn, f"550 Dosya yüklemede hata: {e}")


def handle_retr(conn, filename):
    """Dosyayı istemciye gönderir (Download)."""
    filepath = os.path.join(SERVER_DIR, filename)
    
    if not os.path.exists(filepath) or os.path.isdir(filepath):
        send_response(conn, "550 Dosya sunucuda bulunamadı veya bir dizin.")
        return

    print(f"[TRANSFER] RETR başlatıldı: {filename}")
    send_response(conn, f"150 Dosya transferi başlatılıyor: {filename}")
    
    try:
        with open(filepath, 'rb') as f:
            while True:
                bytes_read = f.read(BUFFER_SIZE)
                if not bytes_read:
                    break
                conn.sendall(bytes_read)
        
        conn.shutdown(socket.SHUT_WR)
        
        time.sleep(0.1) 
        
        send_response(conn, "226 Dosya başarıyla transfer edildi.")
        
    except ConnectionResetError:
        print(f"[UYARI] RETR sırasında istemci bağlantıyı aniden kapattı.")
    except Exception as e:
        print(f"[HATA] RETR hatası: {e}")


def handle_list(conn):
    """Sunucu dizinindeki dosyaları listeler ve istemciye gönderir."""
    print("[TRANSFER] LIST başlatıldı.")
    send_response(conn, "150 Dizin listesi gönderimi için bağlantı açılıyor.")
    
    try:
        files = os.listdir(SERVER_DIR)
        list_output = "\n".join([f"{os.path.basename(f)}" for f in files]) + "\r\n"
        
        conn.sendall(list_output.encode('utf-8'))
        
        conn.shutdown(socket.SHUT_WR)
        time.sleep(0.01) 
        send_response(conn, "226 Dizin listesi başarıyla transfer edildi.")
        
    except ConnectionResetError:
        print(f"[UYARI] LIST sırasında istemci bağlantıyı aniden kapattı.")
    except Exception as e:
        print(f"[HATA] LIST hatası: {e}")


def handle_client(conn, addr):
    """İstemci kontrol bağlantısından gelen komutları işler."""
    print(f"[BAĞLANTI] {addr} bağlandı.")
    is_authenticated = False
    
    try:
        send_response(conn, "220 Python FTP Sunucusu Hazır.")
        
        while True:
            conn.settimeout(CONN_TIMEOUT) 
            data = conn.recv(BUFFER_SIZE).decode('utf-8').strip()
            conn.settimeout(None)

            if not data:
                break
            
            print(f"[KOMUT] {addr}: {data}")
            
            parts = data.split(' ', 1)
            command = parts[0].upper()
            args = parts[1] if len(parts) > 1 else ''

            if command == 'QUIT':
                send_response(conn, "221 Güle güle.")
                break
            elif command == 'USER':
                send_response(conn, "331 Şifre gerekli.")
            elif command == 'PASS':
                is_authenticated = True
                send_response(conn, "230 Giriş başarılı.")
            elif command == 'LIST':
                if is_authenticated:
                    handle_list(conn)
                else:
                    send_response(conn, "530 Giriş yapmanız gerekiyor.")
            elif command == 'RETR':
                if is_authenticated:
                    handle_retr(conn, args)
                else:
                    send_response(conn, "530 Giriş yapmanız gerekiyor.")
            elif command == 'STOR':
                if is_authenticated:
                    handle_stor(conn, args)
                else:
                    send_response(conn, "530 Giriş yapmanız gerekiyor.")
            else:
                send_response(conn, f"502 Komut uygulanmadı: {command}")
                
    except socket.timeout:
        print(f"[{addr}] Zaman aşımı nedeniyle bağlantı kesildi ({CONN_TIMEOUT} saniye).")
    except ConnectionResetError:
        print(f"[KOPMA] {addr} bağlantıyı aniden kapattı.")
    except Exception as e:
        print(f"[HATA] Beklenmeyen hata: {e}")
    finally:
        print(f"[KAPATMA] {addr} bağlantısı kapatıldı.")
        try:
            conn.close()
        except:
            pass


def start_server():
    """Sunucu soketini oluşturur ve dinlemeye başlar."""
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) 
    
    try:
        server_socket.bind((SERVER_HOST, SERVER_PORT))
        server_socket.listen(5)
        print(f"[*] Sunucu dinleniyor: {SERVER_HOST}:{SERVER_PORT}")
        
        while True:
            conn, addr = server_socket.accept()
            client_handler = threading.Thread(target=handle_client, args=(conn, addr))
            client_handler.start()
            
    except Exception as e:
        print(f"[KRİTİK HATA] Sunucu başlatılamadı: {e}")
    finally:
        try:
            server_socket.close()
        except:
            pass


if __name__ == "__main__":
    start_server()