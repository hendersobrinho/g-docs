@echo off
setlocal EnableExtensions

cd /d "%~dp0\.."

set "BUILD_PYTHON="
set "ICON_PYTHON="
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -c "import importlib.util, sys; mods=['openpyxl','PyInstaller']; missing=[m for m in mods if importlib.util.find_spec(m) is None]; sys.exit(1 if missing else 0)" >nul 2>&1
    if not errorlevel 1 set "BUILD_PYTHON=.venv\Scripts\python.exe"
    ".venv\Scripts\python.exe" -c "import importlib.util, sys; sys.exit(0 if importlib.util.find_spec('PIL') else 1)" >nul 2>&1
    if not errorlevel 1 set "ICON_PYTHON=.venv\Scripts\python.exe"
)
if not defined BUILD_PYTHON (
    python -c "import importlib.util, sys; mods=['openpyxl','PyInstaller']; missing=[m for m in mods if importlib.util.find_spec(m) is None]; sys.exit(1 if missing else 0)" >nul 2>&1
    if not errorlevel 1 (
        set "BUILD_PYTHON=python"
    ) else (
        echo Dependencias ausentes para build. Instale com:
        echo   python -m pip install -r requirements.txt
        exit /b 1
    )
)
if not defined ICON_PYTHON (
    python -c "import importlib.util, sys; sys.exit(0 if importlib.util.find_spec('PIL') else 1)" >nul 2>&1
    if not errorlevel 1 (
        set "ICON_PYTHON=python"
    ) else (
        echo Dependencia ausente para gerar icones. Instale com:
        echo   python -m pip install -r requirements.txt
        exit /b 1
    )
)

set "RUN_TESTS=%RUN_TESTS%"
if not defined RUN_TESTS set "RUN_TESTS=1"

if not "%RUN_TESTS%"=="0" (
    echo Executando testes antes do build...
    "%BUILD_PYTHON%" -m unittest tests.test_services tests.test_storage tests.test_resources tests.test_display tests.test_release_files
    if errorlevel 1 exit /b %errorlevel%
)

"%ICON_PYTHON%" scripts\generate_icons.py
if errorlevel 1 exit /b %errorlevel%

"%BUILD_PYTHON%" -m PyInstaller --noconfirm --clean documentos_empresa_app.spec
if errorlevel 1 exit /b %errorlevel%

for /f %%i in ('"%BUILD_PYTHON%" -c "from documentos_empresa_app import __version__; print(__version__)"') do set "APP_VERSION=%%i"
if not defined APP_VERSION (
    echo Nao foi possivel identificar a versao da aplicacao.
    exit /b 1
)

if not exist "dist_release" mkdir "dist_release"
set "ZIP_PATH=dist_release\G-docs-win64-v%APP_VERSION%.zip"
if exist "%ZIP_PATH%" del /f /q "%ZIP_PATH%"

powershell -NoProfile -Command "Compress-Archive -Path 'dist\G-docs\*' -DestinationPath '%ZIP_PATH%' -Force"
if errorlevel 1 exit /b %errorlevel%

echo.
echo Build Windows concluido em: %cd%\dist\G-docs
echo Arquivo de distribuicao: %cd%\%ZIP_PATH%
echo Icone de empacotamento: assets\icons\icon.ico

where iscc >nul 2>&1
if not errorlevel 1 (
    echo.
    echo Inno Setup detectado. Gerando instalador...
    iscc installer\G-docs.iss
    if errorlevel 1 exit /b %errorlevel%
) else (
    echo.
    echo Inno Setup nao encontrado no PATH.
    echo Para gerar o instalador, abra installer\G-docs.iss no Inno Setup ou execute "iscc installer\G-docs.iss".
)
