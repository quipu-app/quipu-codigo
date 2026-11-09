# Quipu

**Quipu, tu asistente de escritorio.** Un compañero animado para Windows con reloj, notas, agenda, tiempo, sonidos de ambiente y modo foco, con personajes inspirados en figuras y paisajes de Argentina y América Latina.

- Página y descarga: https://quipu-app.github.io
- Requiere Windows 10 u 11 (64 bits)
- Licencia: [MIT](LICENSE)

## Cómo compilarlo

Quipu está hecho en Python 3.12 con PySide6. Se empaqueta con PyInstaller y el instalador se arma con Inno Setup 6.

```
python -m pip install -r requirements.txt
pyinstaller Quipu.spec --clean --noconfirm
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" quipu.iss
```

El instalador queda en la carpeta `instalador`. Las versiones oficiales se compilan automáticamente con GitHub Actions (`.github/workflows/compilar.yml`).

## Política de firma de código / Code signing policy

Free code signing provided by [SignPath.io](https://signpath.io), certificate by [SignPath Foundation](https://signpath.org).

Firma de código gratuita provista por SignPath.io, con certificado de SignPath Foundation.

**Roles del equipo / Team roles**

- Autores y revisores / Committers and reviewers: [Eric Seal (@ericocho)](https://github.com/ericocho)
- Aprobadores / Approvers: [Eric Seal (@ericocho)](https://github.com/ericocho)

Solo se firman los instaladores compilados por GitHub Actions a partir del código de este repositorio. / Only installers built by GitHub Actions from the source code in this repository are signed.

## Privacidad / Privacy

Quipu no usa estadísticas de uso, publicidad ni rastreo. Tus notas, tu agenda y tus ajustes se guardan en tu propia compu. Quipu se conecta a internet solo para lo siguiente:

- **Tiempo** ([Open-Meteo](https://open-meteo.com)): envía el nombre o las coordenadas de la ciudad que elegiste, para buscarla y traer el pronóstico.
- **Novedades** (Google Firebase): al abrirse, consulta si hay mensajes o una versión nueva de Quipu. No envía datos tuyos.
- **Notas compartidas** (Google Firebase): solo cuando decidís compartir o abrir una nota con un código. Para eso, Quipu crea una cuenta anónima, sin mail ni nombre, y guarda en Firebase el contenido de la nota que compartiste.
- **Actualizaciones** (GitHub): solo cuando tocás "Actualizar", descarga el instalador nuevo.

Quipu does not use analytics, advertising or tracking. Notes, calendar and settings are stored locally. Quipu connects to the internet only to: fetch the weather forecast for the city you choose (Open-Meteo, sends the city name or coordinates); check for news and new versions on startup (Google Firebase, sends no personal data); share or open a note when you ask it to (Google Firebase, using an anonymous account, stores the shared note's content); and