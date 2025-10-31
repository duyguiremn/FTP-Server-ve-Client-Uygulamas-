import socket
import threading
import tkinter as tk
from tkinter import scrolledtext, filedialog
import os
import time


SERVER_HOST = '127.0.0.1'
SERVER_PORT = 50000 
BUFFER_SIZE = 4096
CLIENT_DIR = 'client_downloads'
TRANSFER_TIMEOUT = 10 


if not os.path.exists(CLIENT_DIR):
    os.makedirs(CLIENT_DIR)

class FtpClientApp:
    def __init__(self, master):
        self.master = master
        master.title("Python FTP Client (Tek Soket Simülasyonu)")
        master.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.client_socket = None
        self.is_connected = False
        self.auth_success = False

        #ARAYÜZÜ OLUŞTURUYORUZ 
        tk.Label(master, text="Server IP:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.host_entry = tk.Entry(master, width=20)
        self.host_entry.insert(0, SERVER_HOST)
        self.host_entry.grid(row=0, column=1, padx=5, pady=5)

        tk.Label(master, text="Port:").grid(row=0, column=2, padx=5, pady=5, sticky="w")
        self.port_entry = tk.Entry(master, width=10)
        self.port_entry.insert(0, SERVER_PORT)
        self.port_entry.grid(row=0, column=3, padx=5, pady=5)
        
        self.connect_button = tk.Button(master, text="Bağlan", command=self.start_connect_thread, width=15)
        self.connect_button.grid(row=0, column=4, padx=5, pady=5)
        
        tk.Label(master, text="Komut (Örnek: STOR dosya.txt):").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.command_entry = tk.Entry(master, width=40)
        self.command_entry.bind('<Return>', lambda event: self.send_command_thread())
        self.command_entry.grid(row=1, column=1, columnspan=3, padx=5, pady=5)
        
        self.send_button = tk.Button(master, text="Gönder", command=self.send_command_thread, width=15)
        self.send_button.grid(row=1, column=4, padx=5, pady=5)
        
        self.log_area = scrolledtext.ScrolledText(master, wrap=tk.WORD, width=70, height=25)
        self.log_area.grid(row=2, column=0, columnspan=5, padx=10, pady=10)
        
        self.log_area.tag_config('green', foreground='green')
        self.log_area.tag_config('red', foreground='red')
        self.log_area.tag_config('blue', foreground='blue') 
        self.log_area.tag_config('black', foreground='black')
        
        self.status_bar = tk.Label(master, text="Bağlı Değil", bd=1, relief=tk.SUNKEN, anchor="w")
        self.status_bar.grid(row=3, column=0, columnspan=5, sticky="ew")

        self.update_status(False)

    def on_closing(self):
        if self.is_connected:
            self.send_quit(silent=True)
        self.master.destroy()
        
    def update_status(self, connected):
        self.is_connected = connected
        if connected:
            self.status_bar.config(text="Bağlandı", fg="green")
            self.connect_button.config(text="Bağlantıyı Kes", command=self.send_quit_thread)
            self.command_entry.config(state=tk.NORMAL)
            self.send_button.config(state=tk.NORMAL)
        else:
            self.status_bar.config(text="Bağlı Değil", fg="red")
            self.connect_button.config(text="Bağlan", command=self.start_connect_thread)
            self.command_entry.config(state=tk.DISABLED)
            self.send_button.config(state=tk.DISABLED)
            
    def log(self, message, color='black'):
        self.log_area.insert(tk.END, message + '\n', color)
        self.log_area.see(tk.END)
        
    def start_connect_thread(self):
        if self.is_connected:
            self.send_quit_thread() 
        else:
            threading.Thread(target=self.connect_to_server).start()

    def connect_to_server(self):
        if self.client_socket:
            try:
                self.client_socket.close()
            except:
                pass
        
        host = self.host_entry.get()
        port = int(self.port_entry.get())
        
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect((host, port))
            
            self.client_socket.settimeout(5)
            response = self.client_socket.recv(BUFFER_SIZE).decode('utf-8').strip()
            self.client_socket.settimeout(None)
            self.log(f"[SUNUCU PROTOKOLÜ] {response}", "blue") 
            
            if response.startswith('220'):
                self.master.after(0, lambda: self.update_status(True))
                self.log(f"[BAĞLANTI] {host}:{port} sunucusuna başarılı.", "green")
               
                self.send_command("USER testuser", silent=True)
                self.send_command("PASS testpass", silent=True)
            else:
                self.log(f"[HATA] Bağlantı reddedildi: {response}", "red")
                self.master.after(0, lambda: self.update_status(False))
                
        except Exception as e:
            self.log(f"[KRİTİK HATA] Sunucuya bağlanılamadı: {e}", "red")
            self.master.after(0, lambda: self.update_status(False))
            
    #bağlantıyı kapatmadan önce sistemi temizledik
    def send_quit(self, silent=False):
        if not silent:
            self.log("[KOMUT] QUIT", "black")
        
        if self.client_socket:
            try:
                self.client_socket.sendall(b'QUIT\r\n')
                self.client_socket.settimeout(2)
                
                response_data = b''
                while True:
                    try:
                        chunk = self.client_socket.recv(BUFFER_SIZE)
                        if not chunk:
                            break
                        response_data += chunk
                        if b'221' in chunk: 
                            break
                    except socket.timeout:
                        break
                
                response = response_data.decode('utf-8', errors='ignore').strip()
                if not silent and response:
                    
                    logged_response = response.split('\n')[-1].strip()
                    if logged_response and logged_response[0].isdigit():
                        self.log(f"[SUNUCU PROTOKOLÜ] {logged_response}", "blue") 
            except:
                pass
            finally:
                try:
                    self.client_socket.close()
                except:
                    pass
                self.client_socket = None
        
        self.master.after(0, lambda: self.update_status(False))
        if not silent:
            self.log("[BAĞLANTI] Bağlantı kapatıldı.", "red")

    def send_quit_thread(self):
        threading.Thread(target=self.send_quit).start()

    def send_command_thread(self):
        command = self.command_entry.get().strip()
        if command:
            self.command_entry.delete(0, tk.END)
            threading.Thread(target=self.process_command, args=(command,)).start()

    def send_command(self, command, silent=False):
        if not self.is_connected:
            if not silent:
                self.log("[HATA] Sunucuya bağlı değilsiniz.", "red")
            return None
            
        if not silent:
            self.log(f"[KOMUT] {command}", "black")
        
        try:
            self.client_socket.sendall(command.encode('utf-8') + b'\r\n')
            
            self.client_socket.settimeout(10)
            response = self.client_socket.recv(BUFFER_SIZE).decode('utf-8').strip()
            self.client_socket.settimeout(None)
            
            if not silent:
                self.log(f"[SUNUCU PROTOKOLÜ] {response}", "blue") 
                
            if command.upper().startswith('PASS') and response.startswith('230'):
                 self.auth_success = True
            
            return response
            
        except Exception as e:
            self.log(f"[HATA] Komut gönderiminde hata: {e}", "red")
            self.master.after(0, lambda: self.send_quit(silent=True))
            return None

    # STOR İŞLEMİ
    def process_stor_data(self, target_filename):
        """Dosyayı seçer ve ana soket üzerinden sunucuya gönderir (Upload)."""
        local_filepath = filedialog.askopenfilename(
            initialdir=".",
            title="Yüklenecek Dosyayı Seçin",
            filetypes=(("Tüm dosyalar", "*.*"), ("Metin dosyaları", "*.txt"))
        )
        
        if not local_filepath:
            self.log("[HATA] Yükleme iptal edildi (Dosya seçilmedi).", "red")
            return
            
        self.log(f"[TRANSFER] '{local_filepath}' yüklenmeye başlanıyor... Hedef: {target_filename}", "black")
        
        data_socket = self.client_socket 
        total_bytes = 0
        
        try:
            with open(local_filepath, 'rb') as f:
                while True:
                    bytes_read = f.read(BUFFER_SIZE)
                    if not bytes_read:
                        break
                    data_socket.sendall(bytes_read)
                    total_bytes += len(bytes_read)

            data_socket.shutdown(socket.SHUT_WR) 

            
            time.sleep(0.1) 

            self.log(f"[BAŞARILI] '{target_filename}' ({total_bytes} bytes) sunucuya gönderildi.", "green")
            
        except Exception as e:
            self.log(f"[HATA] STOR verisi gönderiminde hata: {e}", "red")
    
    # RETR İŞLEMİ
    def process_retr_data(self, filename):
        filepath = os.path.join(CLIENT_DIR, filename)
        self.log(f"[TRANSFER] '{filename}' indirilmeye başlanıyor... Kaydediliyor: {filepath}", "black")
        
        data_socket = self.client_socket 
        total_bytes = 0
        file_transfer_successful = False
        
        try:
            data_socket.settimeout(TRANSFER_TIMEOUT) 
            with open(filepath, 'wb') as f:
                while True:
                    data = data_socket.recv(BUFFER_SIZE)
                    if not data:
                        break
                    f.write(data)
                    total_bytes += len(data)

            data_socket.settimeout(None) 
            file_transfer_successful = True
            self.log(f"[BAŞARILI] '{filename}' ({total_bytes} bytes) indirme tamamlandı.", "green")
            
        except socket.timeout:
            self.log(f"[HATA] RETR sırasında zaman aşımı ({TRANSFER_TIMEOUT}s).", "red")
        except Exception as e:
            self.log(f"[HATA] RETR verisi alımında hata: {e}", "red")
        
        finally:
            if not file_transfer_successful and os.path.exists(filepath):
                 os.remove(filepath)
                 self.log(f"[TEMİZLİK] Başarısız indirme silindi: {filepath}", "red")

    # LIST İŞLEMİ
    def process_list_data(self, filename=None): 
        self.log("[TRANSFER] Dizin listesi bekleniyor...", "black")
        
        data_socket = self.client_socket 
        data = b''
        
        try:
            data_socket.settimeout(TRANSFER_TIMEOUT)
            while True:
                chunk = data_socket.recv(BUFFER_SIZE)
                if not chunk:
                    break
                data += chunk
            data_socket.settimeout(None)

            list_output = data.decode('utf-8', errors='ignore').strip()
            
            self.log("--- SUNUCU DİZİNİ ---", "black")
            for item in list_output.split('\n'):
                self.log(f"  {item.strip()}", "black")
            self.log("---------------------", "black")
            self.log("[BAŞARILI] Dizin listesi transferi tamamlandı.", "green")
            
        except socket.timeout:
            self.log(f"[HATA] LIST sırasında zaman aşımı ({TRANSFER_TIMEOUT}s).", "red")
        except Exception as e:
            self.log(f"[HATA] LIST verisi alımında hata: {e}", "red")
                
    def transfer_data_command(self, command, process_func, filename=None):
        if not self.auth_success:
             self.log("[HATA] Komut için giriş yapmalısınız (USER/PASS).", "red")
             return

        self.log(f"[KOMUT] {command}", "black")
        should_reconnect = False
        
        try:
            
            self.client_socket.sendall(command.encode('utf-8') + b'\r\n')
            
            self.client_socket.settimeout(10) 
            response = self.client_socket.recv(BUFFER_SIZE).decode('utf-8').strip()
            self.client_socket.settimeout(None)
            
            self.log(f"[SUNUCU PROTOKOLÜ] {response}", "blue") 
            if not response.startswith('150'):
                if response.startswith('550'):
                    self.log("[HATA] Sunucu transferi başlatmayı reddetti. (550 hatası)", "red")
                    
                should_reconnect = True 
                return

            process_func(filename) 
            
            try:
                self.client_socket.settimeout(3) 
                final_response = ""
                
                while True:
                    chunk = self.client_socket.recv(BUFFER_SIZE).decode('utf-8', errors='ignore').strip()
                    if not chunk:
                         break
                    final_response += chunk
                    if '226' in chunk or '221' in chunk or '550' in chunk: 
                         break 

                self.client_socket.settimeout(None)
                
                if final_response:
                    for line in final_response.split('\n'):
                        line = line.strip()
                        if line.startswith('226') or line.startswith('221'):
                             self.log(f"[SUNUCU PROTOKOLÜ] {line}", "blue") 
                        elif line.startswith('550'):
                            self.log(f"[HATA] {line}", "red")
                
            except socket.timeout:
                self.log(f"[UYARI] Final 226/221 yanıtı zaman aşımı.", "red")
            except Exception as e:
                self.log(f"[HATA] Final yanıtı okuma hatası: {e}", "red")

            should_reconnect = True 
            
        except Exception as e:
            self.log(f"[HATA] Transfer akışında kritik hata: {e}", "red")
            should_reconnect = True
            
        finally:
            self.send_quit(silent=True) 
            if should_reconnect:
                self.master.after(1000, self.start_connect_thread) 


    def process_command(self, full_command):
        parts = full_command.split(' ', 1)
        command = parts[0].upper()
        args = parts[1] if len(parts) > 1 else ''

        if command == 'LIST':
            self.transfer_data_command(full_command, self.process_list_data)
        elif command == 'RETR':
            if not args:
                self.log("[HATA] RETR komutu için dosya adı gerekli.", "red")
                return
            self.transfer_data_command(full_command, self.process_retr_data, filename=args)
        elif command == 'STOR':
            if not args:
                self.log("[HATA] STOR komutu için hedef dosya adı gerekli.", "red")
                return
            self.transfer_data_command(full_command, self.process_stor_data, filename=args)
        elif command == 'QUIT':
            self.send_quit()
        elif command in ('USER', 'PASS'):
             self.send_command(full_command)
        else:
            self.send_command(full_command)


if __name__ == "__main__":
    root = tk.Tk()
    app = FtpClientApp(root)
    root.mainloop()
    