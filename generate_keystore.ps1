# Script para generar Keystore de Android
# Requiere tener Java (keytool) en el PATH

$ErrorActionPreference = "Stop"

Write-Host "Generando Keystore para ScrapBCV..." -ForegroundColor Cyan

# Verificar si keytool existe
try {
    $null = Get-Command keytool
} catch {
    Write-Error "No se encontró 'keytool'. Asegúrate de tener Java instalado y en el PATH."
    exit 1
}

$keystoreName = "upload-keystore.jks"
$aliasName = "upload"

if (Test-Path $keystoreName) {
    Write-Warning "El archivo $keystoreName ya existe. Si lo sobrescribes, no podrás actualizar apps firmadas con el anterior."
    $confirm = Read-Host "¿Deseas sobrescribirlo? (S/N)"
    if ($confirm -ne "S") {
        Write-Host "Operación cancelada."
        exit 0
    }
    Remove-Item $keystoreName
}

Write-Host "Por favor, introduce los datos para el certificado:"
$password = Read-Host "Contraseña para el Keystore (Mínimo 6 caracteres)"
$fullName = Read-Host "Nombre y Apellido (Ej. Juan Perez)"
$orgUnit = Read-Host "Unidad Organizacional (Ej. Desarrollo)"
$orgName = Read-Host "Nombre de Organización (Ej. MiEmpresa)"
$city = Read-Host "Ciudad o Localidad"
$state = Read-Host "Estado o Provincia"
$country = Read-Host "Código de País (Ej. VE)"

$dname = "CN=$fullName, OU=$orgUnit, O=$orgName, L=$city, ST=$state, C=$country"

# Generar Keystore
# keytool -genkey -v -keystore <keystore-file> -alias <alias> -keyalg RSA -keysize 2048 -validity 10000
# Nota: keytool pedirá confirmación de contraseña, aquí intentamos pasarla por argumentos para automatizar, 
# pero por seguridad keytool a veces prefiere interactividad. 
# Usaremos -storepass y -keypass para simplificar este script de ayuda.

keytool -genkey -v -keystore $keystoreName -alias $aliasName -keyalg RSA -keysize 2048 -validity 10000 -storepass $password -keypass $password -dname $dname

if (Test-Path $keystoreName) {
    Write-Host "`n¡ÉXITO! Keystore generado: $keystoreName" -ForegroundColor Green
    Write-Host "Alias: $aliasName"
    Write-Host "Contraseña: $password"
    Write-Host "`nAHORA SIGUE ESTOS PASOS PARA GITHUB:" -ForegroundColor Yellow
    
    # Convertir a Base64 para GitHub Secret
    $base64 = [Convert]::ToBase64String([IO.File]::ReadAllBytes("$PWD/$keystoreName"))
    $outputFile = "keystore_base64.txt"
    $base64 | Out-File $outputFile -Encoding utf8
    
    Write-Host "1. He guardado la versión Base64 de tu llave en: $outputFile"
    Write-Host "2. Ve a tu repositorio en GitHub -> Settings -> Secrets and variables -> Actions"
    Write-Host "3. Crea los siguientes 'New repository secret':"
    Write-Host "   - ANDROID_KEYSTORE_BASE64: (Copia el contenido de $outputFile)"
    Write-Host "   - ANDROID_KEYSTORE_PASSWORD: $password"
    Write-Host "   - ANDROID_KEY_ALIAS: $aliasName"
    Write-Host "   - ANDROID_KEY_PASSWORD: $password"
    Write-Host "`n¡IMPORTANTE! Borra $outputFile después de subirlo. Guarda $keystoreName en un lugar SEGURO y NO lo subas a Git." -ForegroundColor Red
} else {
    Write-Error "Falló la generación del Keystore."
}
