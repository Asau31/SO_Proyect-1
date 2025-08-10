from .gui_min import VentanaSimulador

def main():
    app = VentanaSimulador(capacidad_mb=1024)
    app.mainloop()

if __name__ == "__main__":
    main()
