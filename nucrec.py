import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import subprocess
import os
import time
import sys

def get_resource_path(relative_path):
    """ Obtiene la ruta del recurso, funciona para dev y para PyInstaller """
    if getattr(sys, 'frozen', False):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

def get_ffmpeg_path():
    """ Busca FFmpeg dentro del paquete o en el sistema """
    ext = ".exe" if os.name == 'nt' else ""
    local_ffmpeg = get_resource_path(f"ffmpeg{ext}")
    if os.path.exists(local_ffmpeg):
        return local_ffmpeg
    return f"ffmpeg{ext}"

class HyperCamFinal:
    def __init__(self, root):
        self.root = root
        self.root.title("Nuclear Recorder")
        self.root.geometry("500x600")
        
        # --- CONFIGURACIÓN DE ICONO (BARRA DE TAREAS) ---
        path_icono = get_resource_path("icono.png")
        if os.path.exists(path_icono):
            try:
                self.img_icon = tk.PhotoImage(file=path_icono)
                self.root.iconphoto(True, self.img_icon)
            except Exception as e:
                print(f"Error cargando icono: {e}")

        self.recording = False
        self.paused = False
        self.segments = []
        self.current_process = None
        self.save_dir = os.path.expanduser("~/Escritorio")
        
        # --- INTERFAZ ---
        tk.Label(root, text="Unregistered Nuclear Recorder", font=("Impact", 24), fg="red").pack(pady=10)
        
        frame_path = tk.LabelFrame(root, text=" 📂 Carpeta de destino ")
        frame_path.pack(fill="x", padx=15, pady=5)
        self.lbl_path = tk.Label(frame_path, text=self.save_dir, fg="blue", wraplength=400)
        self.lbl_path.pack(pady=5)
        tk.Button(frame_path, text="Cambiar Carpeta", command=self.select_path).pack(pady=5)

        frame_audio = tk.LabelFrame(root, text=" 🔊 Entradas de Audio ")
        frame_audio.pack(fill="x", padx=15, pady=5)
        self.var_mic = tk.BooleanVar(value=True)
        tk.Checkbutton(frame_audio, text="🎤 Micrófono", variable=self.var_mic).pack(side=tk.LEFT, padx=20)
        self.var_sys = tk.BooleanVar(value=True)
        tk.Checkbutton(frame_audio, text="💻 Altavoces", variable=self.var_sys).pack(side=tk.LEFT, padx=20)

        self.var_water = tk.BooleanVar(value=True)
        tk.Checkbutton(root, text="Incluir marca de agua clásica", variable=self.var_water).pack(pady=5)

        self.btn_rec = tk.Button(root, text="● INICIAR GRABACIÓN", bg="#2ecc71", fg="white", font=("Arial", 12, "bold"), height=2, command=self.start_new_segment)
        self.btn_rec.pack(pady=15, fill="x", padx=50)
        
        btn_control = tk.Frame(root)
        btn_control.pack()
        self.btn_pause = tk.Button(btn_control, text="II PAUSAR", state=tk.DISABLED, width=15, height=2, command=self.pause_recording)
        self.btn_pause.pack(side=tk.LEFT, padx=5)
        self.btn_stop = tk.Button(btn_control, text="■ DETENER", bg="#e74c3c", fg="white", state=tk.DISABLED, width=15, height=2, command=self.stop_and_merge)
        self.btn_stop.pack(side=tk.LEFT, padx=5)

        self.status = tk.Label(root, text="Listo.", bd=1, relief=tk.SUNKEN, anchor="w")
        self.status.pack(side=tk.BOTTOM, fill="x")

    def select_path(self):
        d = filedialog.askdirectory()
        if d: 
            self.save_dir = d
            self.lbl_path.config(text=d)

    def get_sources(self):
        try:
            out = subprocess.check_output(["pactl", "list", "short", "sources"], text=True)
            mic, system = "default", None
            for line in out.splitlines():
                name = line.split()[1]
                if "monitor" in name: system = name
                elif "input" in name and name != "default": mic = name
            return mic, system
        except: return "default", None

    def start_new_segment(self):
        self.btn_rec.config(state=tk.DISABLED)
        self.btn_pause.config(state=tk.NORMAL, text="II PAUSAR", bg="#f0f0f0", command=self.pause_recording)
        self.btn_stop.config(state=tk.NORMAL)
        
        seg_name = os.path.join(self.save_dir, f"part_{len(self.segments)}.ts")
        self.segments.append(seg_name)
        
        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        mic, system = self.get_sources()
        
        # Usamos el path dinámico de FFmpeg
        ffmpeg_bin = get_ffmpeg_path()
        
        cmd = [ffmpeg_bin, '-y', '-f', 'x11grab', '-video_size', f'{sw}x{sh}', '-i', ':0.0']
        
        audio_in = 0
        if self.var_mic.get():
            cmd += ['-f', 'pulse', '-i', mic]
            audio_in += 1
        if self.var_sys.get() and system:
            cmd += ['-f', 'pulse', '-i', system]
            audio_in += 1

        if audio_in == 2:
            cmd += ['-filter_complex', 'amix=inputs=2:duration=first[aout]', '-map', '0:v', '-map', '[aout]']
        elif audio_in == 1:
            cmd += ['-map', '0:v', '-map', '1:a']
        else:
            cmd += ['-map', '0:v']

        if self.var_water.get():
            cmd += ['-vf', "drawtext=text='Unregistered NucRec':x=10:y=10:fontsize=24:fontcolor=white:shadowcolor=black:shadowx=2:shadowy=2"]

        cmd += ['-c:v', 'libx264', '-preset', 'ultrafast', '-c:a', 'aac', '-b:a', '192k', seg_name]
        
        self.current_process = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.recording = True
        self.status.config(text="GRABANDO...")

    def pause_recording(self):
        if self.current_process:
            try:
                self.current_process.stdin.write(b'q')
                self.current_process.stdin.flush()
                self.current_process.wait()
            except: pass
            self.current_process = None
        
        self.btn_pause.config(text="▶ REANUDAR", bg="yellow", command=self.resume_recording)
        self.status.config(text="PAUSADO")

    def resume_recording(self):
        self.btn_pause.config(text="II PAUSAR", bg="#f0f0f0", command=self.pause_recording)
        self.start_new_segment()

    def stop_and_merge(self):
        self.status.config(text="Procesando archivo final...")
        if self.current_process:
            try:
                self.current_process.stdin.write(b'q')
                self.current_process.stdin.flush()
                self.current_process.wait()
            except: pass

        concat_file = os.path.join(self.save_dir, "list.txt")
        with open(concat_file, "w") as f:
            for seg in self.segments:
                f.write(f"file '{os.path.basename(seg)}'\n")

        final_name = os.path.join(self.save_dir, f"NucBOMB_{int(time.time())}.mp4")
        merge_cmd = [get_ffmpeg_path(), '-y', '-f', 'concat', '-safe', '0', '-i', concat_file, '-c', 'copy', final_name]
        
        subprocess.run(merge_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        os.remove(concat_file)
        for seg in self.segments:
            if os.path.exists(seg): os.remove(seg)
        
        self.segments = []
        self.btn_rec.config(state=tk.NORMAL)
        self.btn_pause.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.DISABLED)
        self.status.config(text="¡Listo!")
        messagebox.showinfo("ÉXITO", f"Guardado en:\n{final_name}")

if __name__ == "__main__":
    main_root = tk.Tk()
    # Evita que el programa se cierre si hay procesos activos
    app = HyperCamFinal(main_root)
    main_root.mainloop()
