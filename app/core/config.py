# Importación de módulos necesarios para el funcionamiento
import json
import sqlite3
import os


# Esta función crea la base de datos de formatos de audio popular
# Si la base de datos ya existe, no hace nada
def create_database_formats(database_path: str) -> str:
    # Lista de formatos de audio populares
    popular_formats = ["mp3", "flac", "wav", "aac", "ogg", "m4a"]

    # Establece conexión con la base de datos
    conn = sqlite3.connect(database_path)
    cur = conn.cursor()
    # Crea la tabla de formatos si no existe
    cur.execute("CREATE TABLE IF NOT EXISTS formats (format TEXT UNIQUE)")
    # Inserta cada formato en la base de datos
    for _format in popular_formats:
        cur.execute("INSERT OR IGNORE INTO formats (format) VALUES (?)", (_format,))
    # Guarda los cambios y cierra la conexión
    conn.commit()
    conn.close()
    return database_path


# Crea la base de datos de géneros
def create_database_genres(database_path: str) -> str:
    # Lista de géneros populares
    popular_genres = ["Pop", "Rock", "Hip-Hop", "Electrónica",
                      "Reggaetón", "Jazz", "Blues", "R&B",
                      "Country", "Metal", "Clásica", "Funk",
                      "Soul", "Indie", "Latina", "Dubstep",]

    # Establece conexión con la base de datos
    conn = sqlite3.connect(database_path)
    cur = conn.cursor()
    # Crea la tabla de géneros si no existe
    cur.execute("CREATE TABLE IF NOT EXISTS genres (genre TEXT UNIQUE)") # Crea la tabla de géneros si no existe
    # Inserta cada género en la base de datos
    for _genre in popular_genres:
        cur.execute("INSERT OR IGNORE INTO genres (genre) VALUES (?)", (_genre,))
    # Guarda los cambios y cierra la conexión
    conn.commit()
    conn.close()
    return database_path


# Esta función extrae la lista de géneros de la base de datos
# Tal lista esta ordenada alfabéticamente (A-Z) con código SQL
# y los devuelve en una lista ordenada
def get_genres_list(database_path: str) -> list[str]:
    conn = sqlite3.connect(database_path)
    cur = conn.cursor()
    cur.execute("SELECT genre FROM genres ORDER BY genre ASC")
    genres = [row[0] for row in cur.fetchall()] # Extrae los géneros en una lista
    conn.close()
    return genres


# Esta función extrae la lista de formatos de la base de datos
# Tal lista esta ordenada alfabéticamente (A-Z) con código SQL
# y los devuelve en una lista ordenada
def get_formats_list(database_path: str) -> list[str]:
    conn = sqlite3.connect(database_path)
    cur = conn.cursor()
    cur.execute("SELECT format FROM formats ORDER BY format ASC")
    formats = [row[0] for row in cur.fetchall()]
    conn.close()
    return formats


# Esta función extrae el perfil del usuario
# Para crear la carpeta de la aplicación en el perfil del usuario
# Si no existe el perfil del usuario, devuelve la ruta por defecto de Windows
def get_user_profile() -> str:
    return os.path.expanduser("~")


# Esta función crea las carpetas de la aplicación
# Si la carpeta no existe, la crea
# De lo contrario, solo devuelve la ruta de la carpeta
def create_directory(app_directory: str) -> dict:
    os.makedirs(app_directory, exist_ok=True)
    return app_directory


def app_config():
    # Variables de configuración de la aplicación
    app_name = "Music-DL v2" # Nombra de la aplicación
    app_version = "0.3.0" # Versión de la aplicación
    app_icon = "app/resources/icons/app.png" # Icono de la aplicación
    ffmpeg_path = "app/resources/bin/ffmpeg.exe" # Ruta del ejecutable de FFmpeg
    
    # Obtiene y formatea la ruta del perfil del usuario
    _user_profile = get_user_profile() # Extrae la ruta del perfil del usuario
    _user_profile = _user_profile.replace("\\", "/") # Reemplaza las barras invertidas por barras normales
    
    # Crea las carpetas necesarias para la aplicación
    app_path = create_directory(f"{_user_profile}/Music-DL") # Crea la carpeta Music-DL en Documents del perfil del usuario
    app_databases_path = create_directory(f"{app_path}/Databases") # Crea la carpeta databases
    app_output_path = create_directory(f"{app_path}/Output") # Crea la carpeta output, donde se guardarán los archivos descargados
    app_config_path = create_directory(f"{app_path}/Config") # Crea la carpeta config, donde se guardarán los archivos de configuración
    
    # Crea las bases de datos necesarias
    db_formats = create_database_formats(f"{app_databases_path}/formats.db3") # Crea la base de datos de formatos
    db_genres = create_database_genres(f"{app_databases_path}/genres.db3") # Crea la base de datos de géneros músicales

    # Ruta del archivo de configuración JSON
    json_path = f"{app_config_path}/app_config.json"
    
    # Si no existe el archivo de configuración, lo crea con valores predeterminados
    if not os.path.exists(json_path):
        _config_values = {
            "app_name": app_name,
            "app_version": app_version,
            "app_icon": app_icon,
            "ffmpeg_path": ffmpeg_path,
            "app_path": app_path,
            "app_databases_path": app_databases_path,
            "app_output_path": app_output_path,
            "app_config": json_path,
            "db_formats": db_formats,
            "db_genres": db_genres
        }

        with open(json_path, "w") as config_file:
            json.dump(_config_values, config_file, indent=4)

    # Si existe el archivo, actualiza los valores si es necesario
    elif os.path.exists(json_path):
        # Lee la configuración actual que tiene guardada la aplicación
        with open(json_path, "r") as config_file:
            config = json.load(config_file)

            # Verifica y actualiza cada valor de configuración que sea necesario para la aplicación
            if "app_name" not in config or config["app_name"] != app_name:
                config["app_name"] = app_name

            if "app_version" not in config or config["app_version"] != app_version:
                config["app_version"] = app_version

            if "app_icon" not in config or config["app_icon"] != app_icon:
                config["app_icon"] = app_icon
            
            if "ffmpeg_path" not in config or config["ffmpeg_path"] != ffmpeg_path:
                config["ffmpeg_path"] = ffmpeg_path
            
            if "app_path" not in config or config["app_path"] != app_path:
                config["app_path"] = app_path

            if "app_databases_path" not in config or config["app_databases_path"] != app_databases_path:
                config["app_databases_path"] = app_databases_path

            if "app_output_path" not in config or config["app_output_path"] != app_output_path:
                config["app_output_path"] = app_output_path

            if "db_formats" not in config or config["db_formats"] != db_formats:
                config["db_formats"] = db_formats

            if "db_genres" not in config or config["db_genres"] != db_genres:
                config["db_genres"] = db_genres

        # Guarda la configuración actualizada
        with open(json_path, "w") as config_file:
            json.dump(config, config_file, indent=4)

    return json_path
