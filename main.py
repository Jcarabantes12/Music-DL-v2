"""
Music-DL v2
"""

import sys
import sqlite3
import yt_dlp
import json
import os
import re
import requests
from app.core import config
from time import sleep
from datetime import datetime
from PyQt6.QtWidgets import (
    QMainWindow,
    QApplication,
    QWidget,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QComboBox,
    QPushButton,
    QSpacerItem,
    QSizePolicy,
    QDialog
)
from PyQt6.QtGui import (
    QIcon,
    QPixmap
)
from PyQt6.QtCore import (
    Qt,
    QTimer,
    QThread,
    pyqtSignal,
    QMutex
)

global app_config
with open(config.app_config(), "r") as config_file:
    app_config = json.load(config_file)

class DownloadAlbum_Thread(QThread):
    finished_thread = pyqtSignal()
    progress_updated = pyqtSignal(str, float)  # Para actualizar el progreso
    download_started = pyqtSignal(dict)  # Para informar inicio de descarga

    def __init__(self, url: str, _format: str, genre: str, save_as: str) -> None:
        super().__init__()
        self.url = url
        self._format = _format
        self.genre = genre
        self.save_as = save_as.replace("\\", "/")

    def progress_hook(self, d):
        if d['status'] == 'downloading':
            total = d.get('total_bytes', 0) or d.get('total_bytes_estimate', 0)
            if total > 0:
                percentage = (d['downloaded_bytes'] / total) * 100
                self.progress_updated.emit(d['filename'], percentage)

    def run(self) -> None:
        try:
            ydl_opts = { # opciones de yt_dlp
                "quiet" : True, # Muestra solo advertencias importantes
                'no_warnings': True,  # Suprime las advertencias
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ytd: # Descarga solo los metadatos de la URL
                metadata = ytd.extract_info(self.url, download=False)
            
            # Obtiene su titulo, artista principal, artistas, año y fecha de creacion/modificacion de cada pista
            playlist_entries = metadata.get("entries", [])
            songs = [
                {
                    "id": entry.get("id"), # ID
                    "title": entry.get("title", "Sin título"), # Titulo 
                    "artist_principal": entry.get("uploader", "Artista desconocido").replace(" - Topic", ""), # Artista principal
                    "artists": entry.get("artists", "Artistas desconocidos"), # Artistas
                    "year": entry.get("release_year", ""), # Año de creacion/modificacion
                    "date": entry.get("upload_date", "") # Fecha de creacion/modificacion
                }
                for entry in playlist_entries
            ]

            # Obtiene el nombre del canal
            common_artists = set(songs[0]["artists"])
            for song in songs[1:]:
                common_artists.intersection_update(song["artists"])

            if common_artists:
                channel = next(iter(common_artists))
            else:
                channel = metadata["entries"][0]["artists"][0]

            # Obtiene la URL de la miniatura
            thumbnail_url = metadata.get("thumbnails", [])[-2]["url"]

            # Obtiene el nombre del álbum
            album = metadata.get("title").replace("Album - ", "")
            _char_pattern = r'[\/\\*?"<>|:]' # caracteres que se reemplazaran
            album_title = re.sub(_char_pattern, " -", album)

            # Obtiene el numero de pistas en el album
            playlist_count = metadata.get("playlist_count")

            # Obtiene la fecha de creacion/modificacion del album
            date_album = metadata.get("modified_date")

            save_as = os.path.join(self.save_as, channel, album_title).replace("\\", "/")
            os.makedirs(save_as, exist_ok=True)

            # Crea la carpeta oculta temporal
            save_as_temp = os.path.join(save_as, ".temp")
            os.makedirs(save_as_temp, exist_ok=True)
            os.system(f"attrib +h {save_as_temp}") # Ocualta la carpeta
            
            # Crea la carpeta para los metadatos
            save_as_metadata = os.path.join(save_as_temp, "metadata")
            os.makedirs(save_as_metadata, exist_ok=True)

            # Crea la carpeta para los archivos descargados sin metadatos
            save_as_files = os.path.join(save_as_temp, "files")
            os.makedirs(save_as_files, exist_ok=True)


            album_metadata = {
                "id": metadata["id"], # ID
                "channel": channel, # Canal del creador
                "thumbnail_url": thumbnail_url, # URL de la miniatura
                "album_title": album_title, # Titulo del album
                "playlist_count": playlist_count, # Numero de pistas del album
                "date": date_album, # Fecha de creacion/modificacion
                "year": date_album[:4], # Año de creacion/modificacion
                "genre": self.genre, # Genero musical
                "songs_metadata": songs, # Entidades (canciones)
                "save_as": save_as # Guardar como
            }
            
            # Guarda los metadatos extraidos en un archivo JSON
            with open(f"{save_as_metadata}/metadata_url.json", "w", encoding="utf-8") as data:
                json.dump(metadata, data, indent=4)

            # Guarda los metadatos necesario para el album en un archivo JSON
            with open(f"{save_as_metadata}/metadata_album.json", "w", encoding="utf-8") as data:
                json.dump(album_metadata, data, indent=4)

            self.download_thumbnail(thumbnail_url, save_as_metadata, "thumbnail")

            # Formatos compatible la configuración
            supported_formats = ["flac", "mp3", "wav", "aac", "opus"]

            # Emitir señal con información del álbum
            album_info = {
                'thumbnail': thumbnail_url,
                'album': album_title,
                'artist': channel,
                'tracks': playlist_count,
                'save_as': save_as
            }
            self.download_started.emit(album_info)

            # Cuando el formato se encuentra en la lista de formatos permitidos
            if self._format in supported_formats:
                postprocessor = {
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': self._format,  # Usa el formato de salida elegido
                    'preferredquality': '0'  # Calidad máxima (sin pérdida)
                }

                ydl_opts = {
                    'ffmpeg_location': config["ffmpeg_path"],  # cambia esto a la ubicación correcta
                    'format' : "bestaudio/best",
                    'quiet': True,  # Suprime la salida
                    'no_warnings': True,  # Suprime las advertencias
                    'ignoreerrors': True,  # ignora los errores
                    'postprocessors': [postprocessor],
                    'progress_hooks': [self.progress_hook],  # Agregar hook de progreso
                    'outtmpl': fr"{save_as_files}/%(title)s.%(ext)s"  # ruta de destino por defecto
                }

                with yt_dlp.YoutubeDL(ydl_opts) as ytd:
                    ytd.download([self.url])

            self.quit()

            self.finished_thread.emit()

        except Exception as e:
            print(e)

    # Descarga la miniatura
    def download_thumbnail(self, thumbnail_url: str, save_as: str, file_name: str) -> str:
        _response = requests.get(thumbnail_url)
        if (_response.status_code == 200):
            save = os.path.join(save_as, f"{file_name}.jpg")
            with open(save, "wb") as save_thumbnail:
                save_thumbnail.write(_response.content)



class PopupAddGenre(QDialog):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Agregar Género")
        self.setWindowIcon(QIcon("resources/icons/AppIcon.png"))
        self.resize(300, 150)

        main_layout = QGridLayout()
        self.setLayout(main_layout)

        title = QLabel()
        title.setText("Ingresa el género nuevo")
        title.setAlignment(Qt.AlignmentFlag.AlignBottom)
        title.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        title.setMaximumSize(400, 30)
        main_layout.addWidget(title, 1, 1, 1, 2)

        self.entry = QLineEdit()
        self.entry.setPlaceholderText("Dubstep")
        self.entry.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.entry.setMaximumSize(400, 30)
        main_layout.addWidget(self.entry, 2, 1, 1, 2)

        button_add = QPushButton()
        button_add.setText("Agregar")
        button_add.clicked.connect(self.action_add_button)
        main_layout.addWidget(button_add, 3, 1)

        button_cancel = QPushButton()
        button_cancel.setText("Cancelar")
        button_cancel.clicked.connect(self.reject)
        main_layout.addWidget(button_cancel, 3, 2)

    def action_add_button(self):
        self.accept()

    def get_value(self):
        return self.entry.text().title().strip()

class MainWidget(QMainWindow):
    def __init__(self):
        super().__init__()

        self.max_threads = 3 # Hilos maximos creados
        self.active_threads = 0 # Contador de los hilos creados
        self.mutex = QMutex() # Controla los accesos a los hilos creados
        self.workers = []

        # self.setStyleSheet("border: 1px solid red")
        self.setWindowTitle(app_config["app_name"]) # titulo de la ventana
        self.setWindowIcon(QIcon(app_config["app_icon"])) # icono de la ventana

        load_ui = self.load_UI() # carga la GUI
        self.setCentralWidget(load_ui) # se coloca el widget principal

        self.showMaximized() # maximiza la ventana

    def load_UI(self):
        # Widget principal
        main_widget = QWidget() # widget principal que muestra el contenido de la ventana

        # Layout principal
        main_hbox = QHBoxLayout() # layout principal que contiene todo los widget de la ventana
        main_widget.setLayout(main_hbox) # agrega el layout principal al widget principal

        form = self.load_form()
        main_hbox.addLayout(form)

        content = self.load_content()
        main_hbox.addLayout(content, 1)

        return main_widget # se retorna le widget principal para colocarlo en el centralwidge
    
    # Formulario
    def load_form(self):
        # CREACION DE LAYOUT
        form_grid = QGridLayout() # layout de formulario

        # CREACION DE WIDGETS
        form_icon = QLabel() # imagen de titulo
        form_title_url = QLabel() # titulo de la url
        self.form_entry_url = QLineEdit() # entrada de la url
        form_title_format = QLabel() # titulo del formato
        self.form_entry_format = QComboBox() # entrada del formato
        form_title_genre = QLabel() # titulo del género
        self.form_entry_genre = QComboBox() # entrada del género
        form_title_save = QLabel() # titulo del guardado
        self.form_entry_save_as = QLineEdit() # entrada del guardado
        self.info_text = QLabel() # texto de informacion
        add_music_btn = QPushButton() # boton de agregar musica

        # CONFIGURACION DE WIDGETS
        # imagen de titulo
        image = QPixmap(app_config["app_icon"]) # ruta de la imagen
        scaled_title_icon = image.scaled(100, 100, transformMode=Qt.TransformationMode.SmoothTransformation) # redimencion de la imagen
        form_icon.setPixmap(scaled_title_icon) # se añade la imagen escalada al titulo
        form_grid.addWidget(form_icon, 1, 1, 1, 2, Qt.AlignmentFlag.AlignCenter) # imagen centrada el layout

        # Espaciado entre la imagen y el titulo de la url
        space = QSpacerItem(0, 20, vPolicy=QSizePolicy.Policy.Maximum)
        form_grid.addItem(space, 2, 1, 1, 2)

        # URL -> Title
        form_title_url.setText("URL") # titulo
        form_title_url.setAlignment(Qt.AlignmentFlag.AlignBottom)
        form_title_url.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        form_title_url.setMaximumSize(400, 35)
        form_title_url.setMinimumSize(400, 35)
        form_grid.addWidget(form_title_url, 3, 1, 1, 2)

        # entrada de la url
        self.form_entry_url.setPlaceholderText("https://music.youtube.com/playlist?list=0000000000")
        self.form_entry_url.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.form_entry_url.setMaximumSize(400, 35)
        self.form_entry_url.setMinimumSize(400, 35)
        form_grid.addWidget(self.form_entry_url, 4, 1, 1, 2)

        # titulo del formato
        form_title_format.setText("Tipo de formato")
        form_title_format.setAlignment(Qt.AlignmentFlag.AlignBottom)
        form_title_format.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        form_title_format.setMaximumSize(150, 35)
        form_title_format.setMinimumSize(150, 35)
        form_grid.addWidget(form_title_format, 5, 1, Qt.AlignmentFlag.AlignCenter)

        # entrada del formato
        format_list = config.get_formats_list(app_config["db_formats"])
        self.form_entry_format.addItems(format_list)
        for _format in range(self.form_entry_format.count()):
            if self.form_entry_format.itemText(_format).lower() != "flac":
                self.form_entry_format.setCurrentText("flac")
                self.form_entry_format.setItemData(_format, False, Qt.ItemDataRole.UserRole - 1)
        self.form_entry_format.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.form_entry_format.setMaximumSize(150, 35)
        self.form_entry_format.setMinimumSize(150, 35)
        self.form_entry_format.setStyleSheet("padding-left: 10px")
        form_grid.addWidget(self.form_entry_format, 6, 1, Qt.AlignmentFlag.AlignCenter)

        # titulo del género
        form_title_genre.setText("Género")
        form_title_genre.setAlignment(Qt.AlignmentFlag.AlignBottom)
        form_title_genre.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        form_title_genre.setMaximumSize(150, 35)
        form_title_genre.setMinimumSize(150, 35)
        form_grid.addWidget(form_title_genre, 5, 2, Qt.AlignmentFlag.AlignCenter)

        # entrada del género
        genre_list = config.get_genres_list(app_config["db_genres"])
        self.form_entry_genre.addItem("--Agregar Genero--")
        self.form_entry_genre.addItems(genre_list)
        self.form_entry_genre.setCurrentIndex(1)
        self.form_entry_genre.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.form_entry_genre.setMaximumSize(150, 35)
        self.form_entry_genre.setMinimumSize(150, 35)
        self.form_entry_genre.setStyleSheet("padding-left: 10px")
        form_grid.addWidget(self.form_entry_genre, 6, 2, Qt.AlignmentFlag.AlignCenter)

        # titulo de la url
        form_title_save.setText("Guardar En")
        form_title_save.setAlignment(Qt.AlignmentFlag.AlignBottom)
        form_title_save.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        form_title_save.setMaximumSize(400, 35)
        form_title_save.setMinimumSize(400, 35)
        form_grid.addWidget(form_title_save, 7, 1, 1, 2)

        # entrada de la url
        self.form_entry_save_as.setPlaceholderText(app_config["app_output_path"])
        self.form_entry_save_as.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.form_entry_save_as.setMaximumSize(400, 35)
        self.form_entry_save_as.setMinimumSize(400, 35)
        form_grid.addWidget(self.form_entry_save_as, 8, 1, 1, 2)

        # texto informativo
        self.info_text.setText("")
        self.info_text.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.info_text.setMaximumWidth(400)
        self.info_text.setMinimumWidth(400)
        self.info_text.setWordWrap(True)
        self.info_text.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
        form_grid.addWidget(self.info_text, 9, 1, 1, 2)

        # Boton de agregar musica
        add_music_btn.setText("Agregar")
        add_music_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        add_music_btn.setMaximumSize(400, 40)
        add_music_btn.setMinimumSize(400, 40)
        add_music_btn.clicked.connect(self.action_button)
        form_grid.addWidget(add_music_btn, 100, 1, 1, 2)

        return form_grid
    
    def load_content(self):
        # CREACION DE LAYOUT
        content_grid = QGridLayout()

        # CREACION DE WIDGETS
        content_title = QLabel()

        # CONFIGURACION DE LOS WIDGETS
        content_title.setText("Lista de Descarga")
        content_title.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom)
        content_title.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        content_grid.addWidget(content_title, 1, 1)

        return content_grid

    def action_button(self):
        if self.form_entry_url.text() and self.form_entry_save_as.text(): # Cuando la URL y Guardar Como tienen valor
            
            if self.form_entry_genre.currentIndex() == 0: # Cuando el genero se selecciono como crear uno nuevo
                popup_genre = PopupAddGenre() # Abre la ventana emergente para agregar el nuevo genero

                if popup_genre.exec() == QDialog.DialogCode.Accepted: # Cuando se preciona "agregar genero"
                    genre = popup_genre.get_value() # Obtiene el genero nuevo
                    genre_list = self.extract_genre()

                    if not genre in genre_list: # Cuando el genero no se encuentra en la base de datos, crea el nuevo genero
                        self.insert_genre(genre) # Crea el genero
                        genre_list = self.extract_genre() # Obtiene la lista actualizada
                        self.form_entry_genre.clear() # Elimina los generos
                        self.form_entry_genre.addItem("--Agregar Genero--") # Agrega el item en primera posicion 
                        self.form_entry_genre.addItems(genre_list) # Extrae los generos de la base de datos y los ordena alfabeticamente (con el genero nuevo)
                        self.form_entry_genre.setCurrentText(genre) # Selecciona el genero nuevo como predeterminado

                    else: # Cuando el genero se encuentra en la base de datos, selecciona el genero como predeterminado
                        self.form_entry_genre.setCurrentText(genre)
                else:
                    self.form_entry_genre.setCurrentIndex(1)

            else: # Ejecuta un hilo nuevo
                self.start_thread(
                    self.form_entry_url.text(), # URL
                    self.form_entry_format.currentText().lower(), # Formato
                    self.form_entry_genre.currentText(), # Genero
                    self.form_entry_save_as.text().replace("\\", "/") # Guardar Como y reemplaza "\" por "/"
                )

        else: # Cuando la entrada no contiene ningun dato
            self.info_text.setText("Rellena todo los campos")
            self.info_text.setStyleSheet("color: #e42222") # Letra roja
            if not self.form_entry_url.text(): # Cuando no contiene ninguna URL
                self.form_entry_url.setStyleSheet("background-color: #5f1111") # Fondo rojo oscuro
            if not self.form_entry_save_as.text(): # Cuando no contiene ninguna ruta "Guardar Como"
                self.form_entry_save_as.setStyleSheet("background-color: #5f1111") # Fondo rojo oscuro
            QTimer.singleShot(5000, self.none) # Espera 5s y ejecuta none()

    # Elimina el texto y estilo de la advertencia en la entrada de datos
    def none(self):
        self.info_text.setText("")
        self.info_text.setStyleSheet("")
        self.form_entry_url.setStyleSheet("")
        self.form_entry_save_as.setStyleSheet("")

    def extract_genre(self):
        genre_list = config.get_genres_list(app_config["db_genres"])

        return genre_list

    def insert_genre(self, genre):
        if genre:
            conn = sqlite3.connect(app_config["db_genres"])
            cur = conn.cursor()
            cur.execute("INSERT OR IGNORE INTO genres (genre) VALUES (?)", (genre.title(),))
            conn.commit()
            conn.close()
    
    def extract_format(self):
        format_list = config.get_formats_list(app_config["db_formats"])

        return format_list
    
    # def add_music_list(self, url, save, genre, _format):
    #     conn = sqlite3.connect("resources/data/music_list.db3")
    #     cur = conn.cursor()
    #     cur.execute("INSERT INTO music_list(url, cover, save, title, count_music, artists, genre, format, status, date_music) VALUES (?,?,?,?,?,?,?,?,?,?)", (
    #         url,
    #         None,
    #         save.replace("\\", "/"),
    #         None,
    #         None,
    #         None,
    #         genre,
    #         _format,
    #         "Pendiente",
    #         datetime.now().strftime("%d-%m-%Y, %H:%M:%S")
    #     ))
    #     conn.commit()
    #     conn.close()

    #     sleep(1)

    def start_thread(self, url, _format, genre, save_as):
        self.mutex.lock()
        if self.active_threads < self.max_threads:
            worker_thread = DownloadAlbum_Thread(url, _format, genre, save_as)
            worker_thread.finished_thread.connect(self.thread_finished)
            worker_thread.start()
            self.workers.append(worker_thread)
            self.active_threads += 1
            print(f"Número de hilos activos: {self.active_threads}")
        else:
            print("Has alcanzado el número maximo de hilos, espera que terminen los demas")
        self.mutex.unlock()

    def thread_finished(self):
        self.mutex.lock()
        self.active_threads -= 1
        print("Descarga finalizada")
        self.mutex.unlock()

    def music_card(self, thumbnail = None, album_name = None,
                   artist = None, tracks = None, save_as = None):
        if not self.findChild(QWidget, album_name):
            target = QWidget()
            


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWidget()
    window.show()
    sys.exit(app.exec())